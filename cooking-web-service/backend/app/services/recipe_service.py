"""菜谱业务逻辑。

管理 ``t_recipe`` / ``t_recipe_element`` 及可选的 MD 详情文件：

- 列表：分页 + 菜名模糊搜索，摘要按卡片字段聚合；
- 详情：结构化要素数组 + 读取 MD 正文作为做法；
- 创建 / 更新：要素 resolve-or-create / 增量 operate，单值约束校验，
  做法非空时生成或更新 MD 文件（写文件失败回滚表数据）；
- 删除：物理删除表行 + 关联行 + MD 文件。
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
from app.services.errors import RecipeNotFoundError, RecipeValidationError
from app.services.recipe_md import (
    delete_recipe_file,
    write_recipe_file,
)
from app.services.recipe_repository import (
    find_recipe_details,
    find_recipe_elements,
    find_recipe_summary,
    list_recipe_summaries,
)

logger = get_logger(__name__)

# 每菜谱至多 1 个的单值要素类型。
SINGLE_VALUE_TYPES = ("time", "difficulty")


def list_recipes(
    keyword: str | None,
    page: int,
    page_size: int,
    exclude_ids: list[int] | None = None,
) -> dict:
    """分页查询菜谱摘要（支持菜名模糊搜索与按 id 排除）。

    Args:
        keyword: 菜名关键字，空表示不过滤。
        page: 页码，从 1 开始。
        page_size: 每页条数，上限 100。
        exclude_ids: 需从结果中排除的菜谱 id（去重；不存在的 id 无影响）。

    Returns:
        api-conventions 分页结构。
    """
    return list_recipe_summaries(keyword, page, page_size, exclude_ids)


def get_recipe_details(recipe_ids: list[int]) -> list[dict]:
    """批量读取菜谱详情（结构化要素 + 做法正文）。

    作为编辑回显与 Agent 详情 API 的共用服务逻辑；不存在的 id 忽略，保持输入
    顺序。决策模块在转发 Agent 前复用本函数翻译 ``dedup_ids``。

    Args:
        recipe_ids: 菜谱 id 列表。

    Returns:
        含 ``id`` / ``name`` / ``elements`` / ``detail`` 的字典列表。
    """
    return find_recipe_details(recipe_ids)


def create_recipe(name: str, elements: list[ElementRef], detail: str | None) -> dict:
    """创建菜谱及其要素关联，做法非空时生成 MD 文件（单事务）。

    Args:
        name: 菜名，非空。
        elements: 要素引用数组（{name, type}）。
        detail: 做法文本，可空。

    Returns:
        创建后的菜谱摘要。

    Raises:
        RecipeValidationError: 菜名为空或单值约束违反。
        ElementValidationError: 要素类型 / 名称非法。
    """
    _validate_name(name)
    _validate_refs(elements)
    _validate_single_values(elements)

    with connection() as conn:
        cur = conn.execute("INSERT INTO t_recipe (name) VALUES (?)", (name.strip(),))
        recipe_id = cur.lastrowid
        for ref in elements:
            element_id = resolve_or_create(conn, ref.type, ref.name)
            conn.execute(
                "INSERT OR IGNORE INTO t_recipe_element (recipe_id, element_id) "
                "VALUES (?, ?)",
                (recipe_id, element_id),
            )

        if detail and detail.strip():
            file_path = write_recipe_file(
                recipe_id,
                name.strip(),
                [ref.model_dump() for ref in elements],
                detail,
            )
            conn.execute(
                "UPDATE t_recipe SET file_path = ? WHERE id = ?",
                (file_path, recipe_id),
            )

    logger.info("created recipe id=%s name=%s", recipe_id, name)
    summary = find_recipe_summary(recipe_id)
    if summary is None:  # pragma: no cover - 事务内刚写入，理论不可达
        raise RecipeNotFoundError(f"菜谱不存在: {recipe_id}")
    return summary


def update_recipe(recipe_id: int, name: str, elements, detail: str | None) -> dict:
    """更新菜谱：姓名 / 做法全量 + 要素增量，做法联动 MD 文件（单事务）。

    Args:
        recipe_id: 目标菜谱 id。
        name: 更新后的菜名，非空。
        elements: 要素增量操作数组。
        detail: 做法文本；为空则删除原 MD 文件并置 ``file_path=null``。

    Returns:
        更新后的菜谱摘要。

    Raises:
        RecipeValidationError: 菜名为空或单值约束违反。
        RecipeNotFoundError: 菜谱不存在。
        ElementValidationError: 操作项非法。
    """
    _validate_name(name)
    for operand in elements:
        validate_operation(operand)

    with connection() as conn:
        row = conn.execute(
            "SELECT id, file_path FROM t_recipe WHERE id = ?", (recipe_id,)
        ).fetchone()
        if row is None:
            raise RecipeNotFoundError(f"菜谱不存在: {recipe_id}")

        conn.execute(
            "UPDATE t_recipe SET name = ?, updated_at = datetime('now') WHERE id = ?",
            (name.strip(), recipe_id),
        )
        apply_element_operations(
            conn,
            table="t_recipe_element",
            owner_column="recipe_id",
            owner_id=recipe_id,
            fixed_columns=None,
            operands=elements,
        )
        _validate_single_values_applied(conn, recipe_id)

        if detail and detail.strip():
            current_elements = find_recipe_elements(conn, recipe_id)
            file_path = write_recipe_file(
                recipe_id, name.strip(), current_elements, detail
            )
            conn.execute(
                "UPDATE t_recipe SET file_path = ? WHERE id = ?",
                (file_path, recipe_id),
            )
        else:
            if row["file_path"]:
                delete_recipe_file(row["file_path"])
            conn.execute(
                "UPDATE t_recipe SET file_path = NULL WHERE id = ?", (recipe_id,)
            )

    logger.info("updated recipe id=%s", recipe_id)
    summary = find_recipe_summary(recipe_id)
    if summary is None:  # pragma: no cover - 事务内刚更新，理论不可达
        raise RecipeNotFoundError(f"菜谱不存在: {recipe_id}")
    return summary


def delete_recipe(recipe_id: int) -> None:
    """物理删除菜谱：表行 + 关联行 + MD 文件（容忍文件缺失）。

    Args:
        recipe_id: 目标菜谱 id。

    Raises:
        RecipeNotFoundError: 菜谱不存在。
    """
    with connection() as conn:
        row = conn.execute(
            "SELECT id, file_path FROM t_recipe WHERE id = ?", (recipe_id,)
        ).fetchone()
        if row is None:
            raise RecipeNotFoundError(f"菜谱不存在: {recipe_id}")

        conn.execute("DELETE FROM t_recipe_element WHERE recipe_id = ?", (recipe_id,))
        conn.execute("DELETE FROM t_recipe WHERE id = ?", (recipe_id,))
        file_path = row["file_path"]

    delete_recipe_file(file_path)
    logger.info("deleted recipe id=%s", recipe_id)


def _validate_name(name: str) -> None:
    """校验菜名非空，空白名称抛出 422。"""
    if not name.strip():
        raise RecipeValidationError("菜名不能为空")


def _validate_refs(elements: list[ElementRef]) -> None:
    """校验创建请求中的要素引用（类型合法、名称合法）。"""
    for ref in elements:
        validate_element_type(ref.type)
        validate_element_name(ref.type, ref.name)


def _validate_single_values(elements: list[ElementRef]) -> None:
    """创建前校验单值约束：``time`` / ``difficulty`` 至多各 1 个。"""
    for type_name in SINGLE_VALUE_TYPES:
        count = sum(1 for ref in elements if ref.type == type_name)
        if count > 1:
            raise RecipeValidationError(f"{type_name} 类型要素至多 1 个")


def _validate_single_values_applied(conn, recipe_id: int) -> None:
    """更新应用 operate 后校验单值约束，违反抛出 422（事务回滚）。"""
    for type_name in SINGLE_VALUE_TYPES:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM t_recipe_element re "
            "JOIN t_element e ON e.id = re.element_id "
            "WHERE re.recipe_id = ? AND e.type = ?",
            (recipe_id, type_name),
        ).fetchone()["n"]
        if count > 1:
            raise RecipeValidationError(f"{type_name} 类型要素至多 1 个")
