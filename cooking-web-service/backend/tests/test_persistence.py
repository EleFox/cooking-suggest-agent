from app.core.database import connection
from app.services.recipe_repository import (
    find_recipe_details,
    find_recipe_summaries,
    pick_recipe_ids,
)


def _count(table: str) -> int:
    with connection() as conn:
        return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]


def _element_id(conn, element_type: str, name: str, sort_order: int = 0) -> int:
    row = conn.execute(
        "SELECT id FROM t_element WHERE type = ? AND name = ?",
        (element_type, name),
    ).fetchone()
    if row is not None:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO t_element (type, name, sort_order) VALUES (?, ?, ?)",
        (element_type, name, sort_order),
    )
    return cur.lastrowid


def _create_recipe(
    name: str,
    time_minutes: int,
    difficulty: str,
    techniques: list[str],
    ingredients: list[str],
) -> int:
    """直接写库创建一条菜谱，供仓库层测试构造数据。"""
    with connection() as conn:
        cur = conn.execute("INSERT INTO t_recipe (name) VALUES (?)", (name,))
        recipe_id = cur.lastrowid
        for technique in techniques:
            conn.execute(
                "INSERT OR IGNORE INTO t_recipe_element (recipe_id, element_id) "
                "VALUES (?, ?)",
                (recipe_id, _element_id(conn, "technique", technique)),
            )
        for ingredient in ingredients:
            conn.execute(
                "INSERT OR IGNORE INTO t_recipe_element (recipe_id, element_id) "
                "VALUES (?, ?)",
                (recipe_id, _element_id(conn, "ingredient", ingredient)),
            )
        conn.execute(
            "INSERT OR IGNORE INTO t_recipe_element (recipe_id, element_id) "
            "VALUES (?, ?)",
            (recipe_id, _element_id(conn, "time", str(time_minutes))),
        )
        conn.execute(
            "INSERT OR IGNORE INTO t_recipe_element (recipe_id, element_id) "
            "VALUES (?, ?)",
            (recipe_id, _element_id(conn, "difficulty", difficulty)),
        )
    return recipe_id


def test_seed_leaves_business_data_empty():
    # 新库中成员 / 菜谱 / 方案等业务数据均为空。
    assert _count("t_recipe") == 0
    assert _count("t_member") == 0
    assert _count("t_preference_scheme") == 0


def test_seed_is_idempotent():
    from app.core.seed import seed

    seed()
    assert _count("t_recipe") == 0
    assert _count("t_element") > 0


def test_seed_populates_technique_and_time_elements():
    with connection() as conn:
        technique_count = conn.execute(
            "SELECT COUNT(*) AS n FROM t_element WHERE type = 'technique'"
        ).fetchone()["n"]
        time_tiers = conn.execute(
            "SELECT name FROM t_element WHERE type = 'time' AND sort_order > 0 "
            "ORDER BY sort_order"
        ).fetchall()

    assert technique_count == 8
    assert [row["name"] for row in time_tiers] == ["15", "30", "60"]


def test_seed_backfills_difficulty_sort_order():
    # 模拟早期版本：难度要素存在但 sort_order 为 0（选项缺失）。
    with connection() as conn:
        conn.execute("UPDATE t_element SET sort_order = 0 WHERE type = 'difficulty'")

    from app.core.seed import seed

    seed()

    with connection() as conn:
        rows = conn.execute(
            "SELECT sort_order FROM t_element WHERE type = 'difficulty'"
        ).fetchall()

    assert len(rows) == 3
    assert all(row["sort_order"] > 0 for row in rows)


def test_pick_recipe_ids_respects_limit_and_exclusions():
    created = [
        _create_recipe(f"菜{i}", 10 + i, "简单", ["炒"], ["鸡蛋"]) for i in range(3)
    ]

    ids = pick_recipe_ids(exclude_ids=[], limit=2)
    assert len(ids) == 2
    assert set(ids) <= set(created)

    remaining = pick_recipe_ids(exclude_ids=ids, limit=5)
    assert remaining
    assert not (set(ids) & set(remaining))


def test_pick_recipe_ids_negative_limit_returns_empty():
    assert pick_recipe_ids(exclude_ids=[], limit=0) == []
    assert pick_recipe_ids(exclude_ids=[], limit=-1) == []


def test_find_recipe_summaries_assembles_elements_shape():
    recipe_id = _create_recipe("测试菜", 45, "一般", ["炖"], ["牛腩", "番茄"])

    summaries = find_recipe_summaries([recipe_id])

    assert len(summaries) == 1
    summary = summaries[0]
    assert set(summary.keys()) == {"id", "name", "elements", "has_detail"}
    assert summary["id"] == recipe_id
    assert summary["name"] == "测试菜"
    assert summary["has_detail"] is False

    by_type: dict[str, list[str]] = {}
    for element in summary["elements"]:
        assert set(element.keys()) == {"id", "type", "name", "sort_order"}
        by_type.setdefault(element["type"], []).append(element["name"])
    assert set(by_type["ingredient"]) == {"牛腩", "番茄"}
    assert by_type["time"] == ["45"]
    assert by_type["difficulty"] == ["一般"]
    assert by_type["technique"] == ["炖"]


def test_find_recipe_summaries_ignores_missing():
    assert find_recipe_summaries([]) == []
    assert find_recipe_summaries([9999]) == []


def test_find_recipe_details_without_file_has_null_detail():
    recipe_id = _create_recipe("无详情", 30, "简单", ["炒"], ["鸡蛋"])

    details = find_recipe_details([recipe_id])

    assert len(details) == 1
    assert set(details[0].keys()) == {"id", "name", "elements", "detail"}
    assert details[0]["id"] == recipe_id
    assert details[0]["detail"] is None


def test_find_recipe_details_ignores_missing():
    assert find_recipe_details([]) == []
    assert find_recipe_details([9998, 9999]) == []
