"""成员业务逻辑。

管理 ``t_member`` / ``t_member_element`` 的增删改查：

- 创建：按 ``(type, name)`` resolve-or-create 要素后批量写关联，单事务；
- 更新：姓名全量更新 + 要素增量 operate 应用，单事务；
- 删除：成员行 + 级联关联行，单事务；不触碰 ``t_element``（要素只增不删）。
"""

from app.core.database import connection
from app.core.logging import get_logger
from app.schemas.element import ElementRef
from app.services.element_service import (
    apply_element_operations,
    resolve_or_create,
    validate_element_name,
    validate_element_type,
    validate_operation,
)
from app.services.errors import MemberNotFoundError, MemberValidationError

logger = get_logger(__name__)

# 成员-要素关联的两类关系。
RELATION_PREFERENCE = "preference"
RELATION_TABOO = "taboo"


def _validate_name(name: str) -> None:
    """校验成员名非空，空白名称抛出 422。"""
    if not name.strip():
        raise MemberValidationError("成员名不能为空")


def _validate_refs(refs: list[ElementRef]) -> None:
    """校验创建请求中的要素引用（类型合法、名称合法）。"""
    for ref in refs:
        validate_element_type(ref.type)
        validate_element_name(ref.type, ref.name)


def _related_elements(conn, member_id: int, relation_type: str) -> list[dict]:
    """读取成员某类关系下的要素明细（按要素 id 升序）。"""
    rows = conn.execute(
        "SELECT e.id AS id, e.name AS name, e.type AS type "
        "FROM t_member_element me JOIN t_element e ON e.id = me.element_id "
        "WHERE me.member_id = ? AND me.relation_type = ? ORDER BY e.id",
        (member_id, relation_type),
    ).fetchall()
    return [{"id": row["id"], "name": row["name"], "type": row["type"]} for row in rows]


def _get_member(conn, member_id: int) -> dict:
    """读取单个成员对象（含偏好 / 禁忌要素明细）。"""
    row = conn.execute(
        "SELECT id, name, created_at, updated_at FROM t_member WHERE id = ?",
        (member_id,),
    ).fetchone()
    return {
        "id": row["id"],
        "name": row["name"],
        "preferences": _related_elements(conn, member_id, RELATION_PREFERENCE),
        "taboos": _related_elements(conn, member_id, RELATION_TABOO),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_members() -> list[dict]:
    """列出全部成员（成员量少，不分页），含完整偏好 / 禁忌要素。"""
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at, updated_at FROM t_member ORDER BY id"
        ).fetchall()
        return [_get_member(conn, row["id"]) for row in rows]


def create_member(
    name: str, preferences: list[ElementRef], taboos: list[ElementRef]
) -> dict:
    """创建成员及其偏好 / 禁忌关联（单事务）。

    Args:
        name: 成员名，非空。
        preferences: 偏好要素引用数组，可为空。
        taboos: 禁忌要素引用数组，可为空。

    Returns:
        创建后的成员对象。

    Raises:
        MemberValidationError: 成员名为空。
        ElementValidationError: 要素类型或名称非法。
    """
    _validate_name(name)
    _validate_refs([*preferences, *taboos])

    with connection() as conn:
        cur = conn.execute("INSERT INTO t_member (name) VALUES (?)", (name.strip(),))
        member_id = cur.lastrowid
        _insert_refs(conn, member_id, RELATION_PREFERENCE, preferences)
        _insert_refs(conn, member_id, RELATION_TABOO, taboos)
        result = _get_member(conn, member_id)

    logger.info(
        "created member id=%s name=%s preferences=%d taboos=%d",
        member_id,
        name,
        len(preferences),
        len(taboos),
    )
    return result


def _insert_refs(
    conn, member_id: int, relation_type: str, refs: list[ElementRef]
) -> None:
    """把创建请求的要素引用 resolve-or-create 后写入关联（幂等）。"""
    for ref in refs:
        element_id = resolve_or_create(conn, ref.type, ref.name)
        conn.execute(
            "INSERT OR IGNORE INTO t_member_element "
            "(member_id, element_id, relation_type) VALUES (?, ?, ?)",
            (member_id, element_id, relation_type),
        )


def update_member(member_id: int, name: str, preferences, taboos) -> dict:
    """更新成员姓名并增量应用要素操作（单事务）。

    Args:
        member_id: 目标成员 id。
        name: 更新后的成员名，非空。
        preferences: 偏好要素增量操作数组。
        taboos: 禁忌要素增量操作数组。

    Returns:
        更新后的成员对象。

    Raises:
        MemberValidationError: 成员名为空。
        MemberNotFoundError: 成员不存在。
        ElementValidationError: 操作项非法。
    """
    _validate_name(name)
    for operand in [*preferences, *taboos]:
        validate_operation(operand)

    with connection() as conn:
        exists = conn.execute(
            "SELECT id FROM t_member WHERE id = ?", (member_id,)
        ).fetchone()
        if exists is None:
            raise MemberNotFoundError(f"成员不存在: {member_id}")

        conn.execute(
            "UPDATE t_member SET name = ?, updated_at = datetime('now') WHERE id = ?",
            (name.strip(), member_id),
        )
        apply_element_operations(
            conn,
            table="t_member_element",
            owner_column="member_id",
            owner_id=member_id,
            fixed_columns={"relation_type": RELATION_PREFERENCE},
            operands=preferences,
        )
        apply_element_operations(
            conn,
            table="t_member_element",
            owner_column="member_id",
            owner_id=member_id,
            fixed_columns={"relation_type": RELATION_TABOO},
            operands=taboos,
        )
        result = _get_member(conn, member_id)

    logger.info("updated member id=%s", member_id)
    return result


def delete_member(member_id: int) -> None:
    """删除成员及其关联行（单事务）；不删除 ``t_element``。

    Args:
        member_id: 目标成员 id。

    Raises:
        MemberNotFoundError: 成员不存在。
    """
    with connection() as conn:
        exists = conn.execute(
            "SELECT id FROM t_member WHERE id = ?", (member_id,)
        ).fetchone()
        if exists is None:
            raise MemberNotFoundError(f"成员不存在: {member_id}")

        conn.execute("DELETE FROM t_member_element WHERE member_id = ?", (member_id,))
        conn.execute("DELETE FROM t_member WHERE id = ?", (member_id,))

    logger.info("deleted member id=%s", member_id)
