"""料理偏好方案业务逻辑。

管理 ``t_preference_scheme`` / ``t_scheme_element`` 的增删改查。写操作
（创建 / 更新 / 删除 / 默认标记互斥）均在单事务内完成，避免半写状态。
"""

from app.core.database import connection
from app.core.logging import get_logger
from app.services.errors import (
    ElementValidationError,
    SchemeNotFoundError,
    SchemeValidationError,
)

logger = get_logger(__name__)

# 列表接口的每页条数上限（遵循 api-conventions 分页约定）。
MAX_PAGE_SIZE = 100


def _validate_element_ids(element_ids: list[int]) -> None:
    """校验要素 id 均存在，任一缺失抛出 422。"""
    if not element_ids:
        return

    placeholders = ",".join("?" for _ in element_ids)
    with connection() as conn:
        rows = conn.execute(
            f"SELECT id FROM t_element WHERE id IN ({placeholders})", element_ids
        ).fetchall()

    found = {row["id"] for row in rows}
    missing = sorted(set(element_ids) - found)
    if missing:
        raise ElementValidationError(f"要素不存在: {missing}")


def _validate_name(name: str) -> None:
    """校验方案名非空，空白名称抛出 422。"""
    if not name.strip():
        raise SchemeValidationError("方案名不能为空")


def _get_scheme(conn, scheme_id: int) -> dict:
    """读取单个方案对象（含 element_ids，按 id 升序）。"""
    row = conn.execute(
        "SELECT id, name, is_default, created_at, updated_at "
        "FROM t_preference_scheme WHERE id = ?",
        (scheme_id,),
    ).fetchone()
    element_ids = [
        r["element_id"]
        for r in conn.execute(
            "SELECT element_id FROM t_scheme_element "
            "WHERE scheme_id = ? ORDER BY element_id",
            (scheme_id,),
        ).fetchall()
    ]
    return {
        "id": row["id"],
        "name": row["name"],
        "is_default": row["is_default"],
        "element_ids": element_ids,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_scheme(name: str, element_ids: list[int]) -> dict:
    """创建方案（方案行 + 勾选关联，同一事务）。

    Args:
        name: 方案名，非空。
        element_ids: 偏好要素 id 数组，可为空。

    Returns:
        创建后的方案对象。

    Raises:
        SchemeValidationError: 方案名为空。
        ElementValidationError: 存在不存在的要素 id。
    """
    _validate_name(name)
    _validate_element_ids(element_ids)

    with connection() as conn:
        cur = conn.execute(
            "INSERT INTO t_preference_scheme (name) VALUES (?)", (name.strip(),)
        )
        scheme_id = cur.lastrowid
        for element_id in element_ids:
            conn.execute(
                "INSERT INTO t_scheme_element (scheme_id, element_id) VALUES (?, ?)",
                (scheme_id, element_id),
            )

    logger.info(
        "created scheme id=%s name=%s elements=%s", scheme_id, name, element_ids
    )
    with connection() as conn:
        return _get_scheme(conn, scheme_id)


def list_schemes(page: int, page_size: int) -> dict:
    """分页查询方案列表（每项含完整 element_ids）。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页条数，上限 ``MAX_PAGE_SIZE``。

    Returns:
        api-conventions 分页结构（list / has_next / total / page / page_size）。
    """
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    offset = (page - 1) * page_size

    with connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM t_preference_scheme"
        ).fetchone()["n"]
        rows = conn.execute(
            "SELECT id FROM t_preference_scheme ORDER BY id LIMIT ? OFFSET ?",
            (page_size + 1, offset),
        ).fetchall()
        # 多取一条判断是否还有下一页，丢弃多余记录。
        has_next = len(rows) > page_size
        scheme_ids = [row["id"] for row in rows[:page_size]]
        schemes = [_get_scheme(conn, scheme_id) for scheme_id in scheme_ids]

    return {
        "list": schemes,
        "has_next": has_next,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_default_scheme() -> dict | None:
    """返回默认方案对象；无默认方案时返回 None。

    Returns:
        默认方案对象（含完整 element_ids），或 None。
    """
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM t_preference_scheme WHERE is_default = 1 "
            "ORDER BY id LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return _get_scheme(conn, row["id"])


def update_scheme(
    scheme_id: int, name: str, element_ids: list[int], is_default: int
) -> dict:
    """更新方案名称 / 勾选项 / 默认标记（同一事务）。

    默认标记互斥：``is_default=1`` 时先将其余方案置 0 再标记本方案；
    ``is_default=0`` 仅取消本方案默认。

    Args:
        scheme_id: 目标方案 id。
        name: 更新后的方案名，非空。
        element_ids: 更新后的勾选要素 id 数组。
        is_default: 1 设为默认 / 0 取消默认。

    Returns:
        更新后的方案对象。

    Raises:
        SchemeNotFoundError: 方案不存在。
        SchemeValidationError: 方案名为空。
        ElementValidationError: 存在不存在的要素 id。
    """
    _validate_name(name)
    _validate_element_ids(element_ids)

    with connection() as conn:
        exists = conn.execute(
            "SELECT id FROM t_preference_scheme WHERE id = ?", (scheme_id,)
        ).fetchone()
        if exists is None:
            raise SchemeNotFoundError(f"方案不存在: {scheme_id}")

        conn.execute(
            "UPDATE t_preference_scheme SET name = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (name.strip(), scheme_id),
        )
        if is_default == 1:
            # 先清除所有方案的默认标记，再标记目标方案，保证全局唯一。
            conn.execute("UPDATE t_preference_scheme SET is_default = 0")
            conn.execute(
                "UPDATE t_preference_scheme SET is_default = 1, "
                "updated_at = datetime('now') WHERE id = ?",
                (scheme_id,),
            )
        else:
            conn.execute(
                "UPDATE t_preference_scheme SET is_default = 0, "
                "updated_at = datetime('now') WHERE id = ?",
                (scheme_id,),
            )

        # 勾选项先删后插，与方案行更新同事务保证一致。
        conn.execute("DELETE FROM t_scheme_element WHERE scheme_id = ?", (scheme_id,))
        for element_id in element_ids:
            conn.execute(
                "INSERT INTO t_scheme_element (scheme_id, element_id) VALUES (?, ?)",
                (scheme_id, element_id),
            )

    logger.info(
        "updated scheme id=%s name=%s elements=%s is_default=%s",
        scheme_id,
        name,
        element_ids,
        is_default,
    )
    with connection() as conn:
        return _get_scheme(conn, scheme_id)


def delete_scheme(scheme_id: int) -> None:
    """删除方案及其勾选关联（同一事务）。

    删除默认方案后系统不再有默认方案，不转移给其他方案。

    Args:
        scheme_id: 目标方案 id。

    Raises:
        SchemeNotFoundError: 方案不存在。
    """
    with connection() as conn:
        exists = conn.execute(
            "SELECT id FROM t_preference_scheme WHERE id = ?", (scheme_id,)
        ).fetchone()
        if exists is None:
            raise SchemeNotFoundError(f"方案不存在: {scheme_id}")

        conn.execute("DELETE FROM t_scheme_element WHERE scheme_id = ?", (scheme_id,))
        conn.execute("DELETE FROM t_preference_scheme WHERE id = ?", (scheme_id,))

    logger.info("deleted scheme id=%s", scheme_id)
