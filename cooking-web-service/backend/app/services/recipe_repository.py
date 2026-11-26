"""菜谱与要素数据访问。

对菜谱池（``t_recipe`` / ``t_recipe_element`` / ``t_element``）的访问：

- 菜谱列表 / 摘要 / 卡片组装：``list_recipe_summaries`` / ``find_recipe_summaries``；
- 批量详情（编辑回显 + Agent 详情 API）：``find_recipe_details``；
- 编辑回显要素读取：``find_recipe_elements``；
- 模拟选取（保留）：``pick_recipe_ids``。

摘要与详情均以统一的 ``elements`` 数组承载菜谱全部关联要素，不再按类型
拼装 ``ingredients`` / ``time_estimate`` / ``difficulty`` 字段。
"""

from app.core.database import connection
from app.core.logging import get_logger
from app.services.recipe_md import read_recipe_detail

logger = get_logger(__name__)

# 列表接口每页条数上限（遵循 api-conventions 分页约定）。
MAX_PAGE_SIZE = 100


def _elements_map(conn, recipe_ids: list[int]) -> dict[int, list[dict]]:
    """批量读取菜谱关联的全部要素，返回 ``{recipe_id: [elements]}``。

    每项要素为 ``{id, type, name, sort_order}``；数组不排序（消费方按 ``type``
    识别、可依 ``sort_order`` 自行排序）。
    """
    if not recipe_ids:
        return {}

    placeholders = ",".join("?" for _ in recipe_ids)
    rows = conn.execute(
        "SELECT re.recipe_id AS recipe_id, e.id AS id, e.type AS type, "
        "e.name AS name, e.sort_order AS sort_order "
        "FROM t_recipe_element re JOIN t_element e ON e.id = re.element_id "
        f"WHERE re.recipe_id IN ({placeholders})",
        recipe_ids,
    ).fetchall()

    result: dict[int, list[dict]] = {}
    for row in rows:
        result.setdefault(row["recipe_id"], []).append(
            {
                "id": row["id"],
                "type": row["type"],
                "name": row["name"],
                "sort_order": row["sort_order"],
            }
        )
    return result


def _fetch_summaries(conn, recipe_ids: list[int]) -> list[dict]:
    """按菜谱 id 批量读取摘要（含 elements），保持输入顺序、忽略不存在。"""
    if not recipe_ids:
        return []

    placeholders = ",".join("?" for _ in recipe_ids)
    rows = conn.execute(
        f"SELECT id, name, file_path FROM t_recipe WHERE id IN ({placeholders})",
        recipe_ids,
    ).fetchall()
    by_id = {
        row["id"]: {
            "id": row["id"],
            "name": row["name"],
            "has_detail": bool(row["file_path"]),
        }
        for row in rows
    }
    elements_map = _elements_map(conn, recipe_ids)

    summaries = []
    for recipe_id in recipe_ids:
        summary = by_id.get(recipe_id)
        if summary is None:
            continue
        summary["elements"] = elements_map.get(recipe_id, [])
        summaries.append(summary)
    return summaries


def list_recipe_summaries(
    keyword: str | None,
    page: int,
    page_size: int,
    exclude_ids: list[int] | None = None,
) -> dict:
    """分页查询菜谱摘要，支持按菜名模糊过滤与按 id 排除。

    过滤顺序：先按 ``keyword`` 模糊匹配，再排除 ``exclude_ids``；分页与
    ``total`` / ``has_next`` 均基于排除后的结果集。

    Args:
        keyword: 菜名关键字，空 / None 表示不过滤。
        page: 页码，从 1 开始。
        page_size: 每页条数，上限 ``MAX_PAGE_SIZE``。
        exclude_ids: 需从结果中排除的菜谱 id（不存在的 id 无影响）。

    Returns:
        api-conventions 分页结构（list / has_next / total / page / page_size）。
    """
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    offset = (page - 1) * page_size
    like = f"%{keyword.strip()}%" if keyword and keyword.strip() else None

    conditions: list[str] = []
    filter_params: list = []
    if like is not None:
        conditions.append("name LIKE ?")
        filter_params.append(like)
    if exclude_ids:
        placeholders = ",".join("?" for _ in exclude_ids)
        conditions.append(f"id NOT IN ({placeholders})")
        filter_params.extend(exclude_ids)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

    with connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM t_recipe{where}", filter_params
        ).fetchone()["n"]
        id_rows = conn.execute(
            f"SELECT id FROM t_recipe{where} ORDER BY id LIMIT ? OFFSET ?",
            [*filter_params, page_size + 1, offset],
        ).fetchall()

        # 多取一条判断是否还有下一页，丢弃多余记录。
        has_next = len(id_rows) > page_size
        recipe_ids = [row["id"] for row in id_rows[:page_size]]
        summaries = _fetch_summaries(conn, recipe_ids)

    return {
        "list": summaries,
        "has_next": has_next,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def find_recipe_summaries(recipe_ids: list[int]) -> list[dict]:
    """按 id 批量读取菜谱摘要（含 elements），保持输入顺序、忽略不存在。"""
    with connection() as conn:
        return _fetch_summaries(conn, recipe_ids)


def find_recipe_summary(recipe_id: int) -> dict | None:
    """读取单个菜谱摘要，不存在返回 None。"""
    summaries = find_recipe_summaries([recipe_id])
    return summaries[0] if summaries else None


def find_recipe_details(recipe_ids: list[int]) -> list[dict]:
    """批量读取菜谱详情（要素 + 做法正文），保持输入顺序、忽略不存在。

    做法正文读自 MD 文件；无详情（``file_path`` 为空或文件缺失）时 ``detail``
    为 ``None``。不存在的 id 跳过。该函数同时服务决策去重翻译与详情接口。
    """
    if not recipe_ids:
        return []

    placeholders = ",".join("?" for _ in recipe_ids)
    with connection() as conn:
        rows = conn.execute(
            f"SELECT id, name, file_path FROM t_recipe WHERE id IN ({placeholders})",
            recipe_ids,
        ).fetchall()
        by_id = {row["id"]: row for row in rows}
        elements_map = _elements_map(conn, recipe_ids)

    details = []
    for recipe_id in recipe_ids:
        row = by_id.get(recipe_id)
        if row is None:
            continue
        details.append(
            {
                "id": row["id"],
                "name": row["name"],
                "elements": elements_map.get(recipe_id, []),
                "detail": read_recipe_detail(row["file_path"]),
            }
        )
    return details


def find_recipe_elements(conn, recipe_id: int) -> list[dict]:
    """读取菜谱关联的全部要素（id / type / name / sort_order），按要素 id 升序。

    Args:
        conn: 复用调用方事务的 SQLite 连接。
        recipe_id: 菜谱 id。
    """
    rows = conn.execute(
        "SELECT e.id AS id, e.type AS type, e.name AS name, "
        "e.sort_order AS sort_order "
        "FROM t_recipe_element re JOIN t_element e ON e.id = re.element_id "
        "WHERE re.recipe_id = ? ORDER BY e.id",
        (recipe_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "type": row["type"],
            "name": row["name"],
            "sort_order": row["sort_order"],
        }
        for row in rows
    ]


def pick_recipe_ids(exclude_ids: list[int], limit: int) -> list[int]:
    """选取至多 ``limit`` 个菜谱 id，排除 ``exclude_ids`` 中的 id。

    Args:
        exclude_ids: 需排除（已展示）的菜谱 id 列表。
        limit: 最多返回的数量；小于等于 0 时返回空列表。

    Returns:
        选中的菜谱 id 列表。
    """
    if limit <= 0:
        return []

    if exclude_ids:
        placeholders = ",".join("?" for _ in exclude_ids)
        query = f"""
            SELECT id FROM t_recipe
            WHERE id NOT IN ({placeholders})
            ORDER BY id
            LIMIT ?
        """
        params: list = [*exclude_ids, limit]
    else:
        query = "SELECT id FROM t_recipe ORDER BY id LIMIT ?"
        params = [limit]

    with connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [row["id"] for row in rows]
