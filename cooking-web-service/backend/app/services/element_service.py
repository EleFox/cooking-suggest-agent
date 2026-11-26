"""要素查询与解析业务逻辑。

职责：
- 按要素类型从 ``t_element`` 读取展示选项（供设置页 / 菜谱表单渲染）；
- 提供 ``resolve-or-create`` 能力：成员 / 菜谱表单提交的自由文本要素按
  ``UNIQUE(type, name)`` 完全匹配，存在复用、不存在新建。

要素表 + 关联表的设计用于支撑要素类型自由扩展：新增要素类型时只需扩展
``VALID_ELEMENT_TYPES`` 与相应查询入口，接口字段结构不变。
"""

from app.core.database import connection
from app.core.logging import get_logger
from app.schemas.element import ElementOperate
from app.services.errors import ElementValidationError

logger = get_logger(__name__)

# 合法要素类型集合（新增类型在此扩展）。
VALID_ELEMENT_TYPES = frozenset(
    {"ingredient", "technique", "time", "allergen", "taste", "difficulty"}
)

# 增量更新支持的要素操作。
VALID_OPERATES = frozenset({"add", "remove", "edit"})


def list_elements(element_type: str) -> list[dict]:
    """按类型列出要素展示选项，按 ``sort_order`` 升序。

    仅返回 ``sort_order > 0`` 的要素：菜谱属性要素（如菜谱具体时间）以
    ``sort_order=0`` 存储，不作为用户勾选选项。

    Args:
        element_type: 要素类型（如 technique / time / difficulty）。

    Returns:
        要素字典列表（id / type / name / sort_order）。
    """
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, type, name, sort_order FROM t_element "
            "WHERE type = ? AND sort_order > 0 ORDER BY sort_order ASC",
            (element_type,),
        ).fetchall()

    logger.debug("listed %d elements of type %s", len(rows), element_type)
    return [dict(row) for row in rows]


def validate_element_type(element_type: str) -> None:
    """校验要素类型合法，非法时抛出 422。

    Args:
        element_type: 待校验的要素类型。

    Raises:
        ElementValidationError: 类型不在 ``VALID_ELEMENT_TYPES`` 内。
    """
    if element_type not in VALID_ELEMENT_TYPES:
        raise ElementValidationError(f"非法要素类型: {element_type}")


def validate_element_name(element_type: str, name: str) -> None:
    """校验要素名合法（``time`` 类型要求正整数分钟数）。

    Args:
        element_type: 要素类型。
        name: 要素名。

    Raises:
        ElementValidationError: 名称为空，或 ``time`` 类型的名称不是正整数。
    """
    if not name.strip():
        raise ElementValidationError("要素名不能为空")
    if element_type == "time" and not _is_positive_int(name):
        raise ElementValidationError("时间要素必须为正整数分钟数")


def resolve_or_create(conn, element_type: str, name: str) -> int:
    """按 ``(type, name)`` 完全匹配解析要素 id，不存在则新建。

    新要素以 ``sort_order=0`` 写入（不作为选项展示），符合「要素只增不删」
    的生命周期约定。

    Args:
        conn: 复用调用方事务的 SQLite 连接。
        element_type: 要素类型。
        name: 要素名（已做去空白处理）。

    Returns:
        对应 ``t_element.id``。
    """
    normalized = name.strip()
    row = conn.execute(
        "SELECT id FROM t_element WHERE type = ? AND name = ?",
        (element_type, normalized),
    ).fetchone()
    if row is not None:
        return row["id"]

    cur = conn.execute(
        "INSERT INTO t_element (type, name, sort_order) VALUES (?, ?, 0)",
        (element_type, normalized),
    )
    logger.info("created element type=%s name=%s", element_type, normalized)
    return cur.lastrowid


def _is_positive_int(value: str) -> bool:
    """判断字符串是否为表示正整数的十进制数字（无符号、无前导空白）。"""
    candidate = value.strip()
    return candidate.isdigit() and int(candidate) >= 1


def validate_operation(operand: ElementOperate) -> None:
    """校验单个增量要素操作项，非法时抛出 422。

    Args:
        operand: 增量操作项（含 operate / id / name / type）。

    Raises:
        ElementValidationError: 操作标识非法、``remove`` / ``edit`` 缺 id、
            要素类型非法，或 ``add`` / ``edit`` 的要素名非法。
    """
    if operand.operate not in VALID_OPERATES:
        raise ElementValidationError(f"非法操作: {operand.operate}")
    if operand.operate in {"remove", "edit"} and operand.id is None:
        raise ElementValidationError(f"{operand.operate} 操作缺少 id")
    validate_element_type(operand.type)
    # remove 仅凭 id 定位关联，无需校验名称。
    if operand.operate in {"add", "edit"}:
        validate_element_name(operand.type, operand.name)


def apply_element_operations(
    conn,
    *,
    table: str,
    owner_column: str,
    owner_id: int,
    fixed_columns: dict | None,
    operands: list[ElementOperate],
) -> None:
    """在给定关联表上增量应用要素操作（add / remove / edit）。

    所有操作复用调用方事务；``add`` 已存在关联幂等忽略，``remove`` 不存在
    关联幂等忽略，``edit`` 解析结果相同则 no-op（等价 remove + add）。

    Args:
        conn: 复用调用方事务的 SQLite 连接。
        table: 关联表名（内部常量，非用户输入）。
        owner_column: 关联表中指向资源主键的列名。
        owner_id: 资源主键值。
        fixed_columns: 追加的固定列（如成员的 ``relation_type``），可为 None。
        operands: 增量操作项列表。
    """
    extras = fixed_columns or {}
    for operand in operands:
        if operand.operate == "add":
            element_id = resolve_or_create(conn, operand.type, operand.name)
            _insert_relation(conn, table, owner_column, owner_id, element_id, extras)
        elif operand.operate == "remove":
            _delete_relation(conn, table, owner_column, owner_id, operand.id, extras)
        else:  # edit
            new_element_id = resolve_or_create(conn, operand.type, operand.name)
            if new_element_id != operand.id:
                _delete_relation(
                    conn, table, owner_column, owner_id, operand.id, extras
                )
                _insert_relation(
                    conn, table, owner_column, owner_id, new_element_id, extras
                )


def _insert_relation(
    conn,
    table: str,
    owner_column: str,
    owner_id: int,
    element_id: int,
    extras: dict,
) -> None:
    """插入关联行，已存在则忽略（幂等）。"""
    columns = [owner_column, "element_id", *extras.keys()]
    values = [owner_id, element_id, *extras.values()]
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        values,
    )


def _delete_relation(
    conn,
    table: str,
    owner_column: str,
    owner_id: int,
    element_id: int,
    extras: dict,
) -> None:
    """删除关联行，不存在则忽略（幂等）。"""
    clauses = [f"{owner_column} = ?", "element_id = ?"]
    values = [owner_id, element_id]
    for column, value in extras.items():
        clauses.append(f"{column} = ?")
        values.append(value)
    conn.execute(f"DELETE FROM {table} WHERE {' AND '.join(clauses)}", values)
