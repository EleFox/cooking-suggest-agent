"""菜谱 CRUD 接口测试。

对应 S3 ``design/sprints/S3/api.md`` 的菜谱接口（列表 / 批量详情 / 创建 /
更新 / 删除），覆盖分页搜索、要素 resolve-or-create、单值约束与 MD 文件联动。
列表与详情统一以 ``elements`` 数组返回。
"""

from pathlib import Path

from app.core.config import get_settings
from app.core.database import connection


def _recipes_dir() -> Path:
    return Path(get_settings().recipes_dir)


def _element_id(element_type: str, name: str) -> int | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM t_element WHERE type = ? AND name = ?",
            (element_type, name),
        ).fetchone()
    return row["id"] if row else None


def _element_count() -> int:
    with connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM t_element").fetchone()["n"]


def _recipe_count() -> int:
    with connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM t_recipe").fetchone()["n"]


def _element_names(payload: dict, element_type: str) -> list[str]:
    """从摘要 / 详情对象的 elements 中取指定类型的名称列表。"""
    return [e["name"] for e in payload["elements"] if e["type"] == element_type]


async def _create(
    client,
    name: str,
    *,
    time_minutes: int = 30,
    difficulty: str = "一般",
    ingredients: tuple[str, ...] = ("鸡蛋",),
    techniques: tuple[str, ...] = ("炒",),
    detail: str | None = None,
) -> dict:
    """通过接口创建菜谱并返回摘要数据（用于构造测试数据）。"""
    response = await client.post(
        "/api/recipes",
        json={
            "name": name,
            "elements": [
                *({"name": n, "type": "ingredient"} for n in ingredients),
                *({"name": n, "type": "technique"} for n in techniques),
                {"name": str(time_minutes), "type": "time"},
                {"name": difficulty, "type": "difficulty"},
            ],
            "detail": detail,
        },
    )
    assert response.status_code == 200
    assert response.json()["code"] == 200
    return response.json()["data"]


async def _detail(client, recipe_id: int) -> dict:
    """调用批量详情接口并返回单条详情对象（取数组首项）。"""
    response = await client.get("/api/recipes/detail", params={"ids": recipe_id})
    assert response.status_code == 200
    assert response.json()["code"] == 200
    return response.json()["data"][0]


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------


async def test_list_recipes_returns_paginated_summary(client):
    detailed = await _create(
        client,
        "番茄牛腩煲",
        time_minutes=45,
        difficulty="一般",
        ingredients=("牛腩", "番茄"),
        techniques=("炖",),
        detail="做法步骤",
    )
    plain = await _create(client, "清蒸鲈鱼", time_minutes=20, difficulty="简单")

    response = await client.get("/api/recipes")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert set(data.keys()) == {"list", "has_next", "total", "page", "page_size"}
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["has_next"] is False
    assert len(data["list"]) == 2

    item = next(x for x in data["list"] if x["id"] == detailed["id"])
    assert set(item.keys()) == {"id", "name", "elements", "has_detail"}
    assert item["has_detail"] is True
    for element in item["elements"]:
        assert set(element.keys()) == {"id", "type", "name", "sort_order"}
    assert set(_element_names(item, "ingredient")) == {"牛腩", "番茄"}
    assert _element_names(item, "time") == ["45"]
    assert _element_names(item, "difficulty") == ["一般"]

    # 未填写做法的菜谱无 MD 详情。
    other = next(x for x in data["list"] if x["id"] == plain["id"])
    assert other["has_detail"] is False
    assert _element_names(other, "difficulty") == ["简单"]


async def test_list_recipes_search_filters_by_name(client):
    await _create(client, "番茄牛腩煲")
    await _create(client, "番茄炒蛋")
    await _create(client, "清蒸鲈鱼")

    response = await client.get("/api/recipes", params={"keyword": "番茄"})

    data = response.json()["data"]
    assert data["total"] == 2
    assert all("番茄" in item["name"] for item in data["list"])


async def test_list_recipes_search_no_match(client):
    await _create(client, "清蒸鲈鱼")

    response = await client.get("/api/recipes", params={"keyword": "不存在的菜"})

    data = response.json()["data"]
    assert data["list"] == []
    assert data["total"] == 0
    assert data["has_next"] is False


async def test_list_recipes_pagination(client):
    for i in range(5):
        await _create(client, f"菜{i}")

    page1 = await client.get("/api/recipes", params={"page": 1, "page_size": 2})
    page3 = await client.get("/api/recipes", params={"page": 3, "page_size": 2})

    d1 = page1.json()["data"]
    d3 = page3.json()["data"]
    assert d1["total"] == 5
    assert d1["has_next"] is True
    assert len(d1["list"]) == 2
    assert d3["has_next"] is False
    assert len(d3["list"]) == 1
    ids1 = {item["id"] for item in d1["list"]}
    ids3 = {item["id"] for item in d3["list"]}
    assert not (ids1 & ids3)


async def test_list_recipes_invalid_page_rejected(client):
    response = await client.get("/api/recipes", params={"page": 0})

    assert response.status_code == 422
    assert response.json()["code"] == 422


async def test_list_recipes_excludes_recipe_ids(client):
    first = await _create(client, "甲菜")
    second = await _create(client, "乙菜")
    third = await _create(client, "丙菜")

    response = await client.get(
        "/api/recipes", params={"exclude_recipe_ids": f"{second['id']}"}
    )

    data = response.json()["data"]
    assert data["total"] == 2
    ids = {item["id"] for item in data["list"]}
    assert ids == {first["id"], third["id"]}
    assert second["id"] not in ids


async def test_list_recipes_exclude_ignores_missing_ids(client):
    first = await _create(client, "甲菜")
    second = await _create(client, "乙菜")

    response = await client.get(
        "/api/recipes", params={"exclude_recipe_ids": "9998,9999"}
    )

    data = response.json()["data"]
    assert data["total"] == 2
    assert {item["id"] for item in data["list"]} == {first["id"], second["id"]}


async def test_list_recipes_exclude_empty_string_returns_all(client):
    first = await _create(client, "甲菜")
    second = await _create(client, "乙菜")

    response = await client.get("/api/recipes", params={"exclude_recipe_ids": ""})

    data = response.json()["data"]
    assert data["total"] == 2
    assert {item["id"] for item in data["list"]} == {first["id"], second["id"]}


async def test_list_recipes_exclude_applies_before_pagination(client):
    created = [await _create(client, f"菜{i}") for i in range(5)]

    response = await client.get(
        "/api/recipes",
        params={
            "exclude_recipe_ids": f"{created[0]['id']},{created[1]['id']}",
            "page": 1,
            "page_size": 2,
        },
    )

    data = response.json()["data"]
    # 排除 2 条后剩 3 条，total 与分页均基于排除后结果集。
    assert data["total"] == 3
    assert data["has_next"] is True
    ids = {item["id"] for item in data["list"]}
    assert created[0]["id"] not in ids
    assert created[1]["id"] not in ids


async def test_list_recipes_exclude_combined_with_keyword(client):
    await _create(client, "番茄牛腩煲")
    tomato_egg = await _create(client, "番茄炒蛋")
    await _create(client, "清蒸鲈鱼")

    response = await client.get(
        "/api/recipes",
        params={
            "keyword": "番茄",
            "exclude_recipe_ids": f"{tomato_egg['id']}",
        },
    )

    data = response.json()["data"]
    assert data["total"] == 1
    assert all("番茄" in item["name"] for item in data["list"])
    assert tomato_egg["id"] not in {item["id"] for item in data["list"]}


async def test_list_recipes_invalid_exclude_ids_rejected(client):
    response = await client.get("/api/recipes", params={"exclude_recipe_ids": "1,abc"})

    assert response.status_code == 200
    assert response.json()["code"] == 422


# ---------------------------------------------------------------------------
# 批量详情
# ---------------------------------------------------------------------------


async def test_get_recipe_details_returns_elements_and_null_detail(client):
    created = await _create(client, "清蒸鲈鱼")

    response = await client.get("/api/recipes/detail", params={"ids": created["id"]})

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 1
    item = data[0]
    assert set(item.keys()) == {"id", "name", "elements", "detail"}
    assert item["id"] == created["id"]
    assert item["detail"] is None
    types = {element["type"] for element in item["elements"]}
    assert {"ingredient", "technique", "time", "difficulty"} <= types
    for element in item["elements"]:
        assert set(element.keys()) == {"id", "type", "name", "sort_order"}


async def test_get_recipe_details_batch_ignores_missing(client):
    first = await _create(client, "甲菜")
    second = await _create(client, "乙菜")

    response = await client.get(
        "/api/recipes/detail",
        params={"ids": f"{first['id']},{second['id']},9999"},
    )

    data = response.json()["data"]
    assert [item["id"] for item in data] == [first["id"], second["id"]]


async def test_get_recipe_details_all_missing_returns_empty(client):
    response = await client.get("/api/recipes/detail", params={"ids": "9998,9999"})

    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert response.json()["data"] == []


async def test_get_recipe_details_empty_ids_rejected(client):
    response = await client.get("/api/recipes/detail", params={"ids": ""})

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_get_recipe_details_non_integer_ids_rejected(client):
    response = await client.get("/api/recipes/detail", params={"ids": "1,abc"})

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_get_recipe_details_missing_param_rejected(client):
    response = await client.get("/api/recipes/detail")

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 创建
# ---------------------------------------------------------------------------


async def test_create_recipe_with_detail_writes_md(client):
    response = await client.post(
        "/api/recipes",
        json={
            "name": "手工菜",
            "elements": [
                {"name": "自制酱", "type": "ingredient"},
                {"name": "炖", "type": "technique"},
                {"name": "45", "type": "time"},
                {"name": "简单", "type": "difficulty"},
            ],
            "detail": "第一步：准备食材。",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert set(data.keys()) == {"id", "name", "elements", "has_detail"}
    assert data["name"] == "手工菜"
    assert "自制酱" in _element_names(data, "ingredient")
    assert _element_names(data, "time") == ["45"]
    assert _element_names(data, "difficulty") == ["简单"]
    assert data["has_detail"] is True

    detail = await _detail(client, data["id"])
    assert detail["detail"] == "第一步：准备食材。"

    # 文件落盘且含 front-matter 与正文。
    file_path = _recipes_dir() / f"r-{data['id']}.md"
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "name: 手工菜" in content
    assert "time: 45" in content
    assert "第一步：准备食材。" in content


async def test_create_recipe_without_detail_has_no_detail(client):
    response = await client.post(
        "/api/recipes",
        json={"name": "无详情菜", "elements": [], "detail": None},
    )

    data = response.json()["data"]
    assert data["has_detail"] is False
    detail = await _detail(client, data["id"])
    assert detail["detail"] is None


async def test_create_recipe_reuses_existing_element(client):
    # 先创建一次，使「番茄」要素入库；再次引用不应新增要素行。
    await _create(client, "首个菜", ingredients=("番茄",))
    before = _element_count()

    response = await client.post(
        "/api/recipes",
        json={
            "name": "复用菜",
            "elements": [{"name": "番茄", "type": "ingredient"}],
            "detail": None,
        },
    )

    assert response.status_code == 200
    assert _element_count() == before


async def test_create_recipe_empty_name_rejected(client):
    response = await client.post(
        "/api/recipes", json={"name": "  ", "elements": [], "detail": None}
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_create_recipe_invalid_element_type_rejected(client):
    response = await client.post(
        "/api/recipes",
        json={
            "name": "坏类型",
            "elements": [{"name": "牛肉", "type": "unknown"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_create_recipe_non_positive_time_rejected(client):
    response = await client.post(
        "/api/recipes",
        json={
            "name": "坏时间",
            "elements": [{"name": "abc", "type": "time"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_create_recipe_duplicate_time_rejected(client):
    response = await client.post(
        "/api/recipes",
        json={
            "name": "两个时间",
            "elements": [
                {"name": "45", "type": "time"},
                {"name": "60", "type": "time"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_create_recipe_duplicate_difficulty_rejected(client):
    response = await client.post(
        "/api/recipes",
        json={
            "name": "两个难度",
            "elements": [
                {"name": "简单", "type": "difficulty"},
                {"name": "困难", "type": "difficulty"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


# ---------------------------------------------------------------------------
# 更新
# ---------------------------------------------------------------------------


async def test_update_recipe_name_and_add_element(client):
    created = (
        await client.post(
            "/api/recipes",
            json={
                "name": "旧菜",
                "elements": [{"name": "番茄", "type": "ingredient"}],
            },
        )
    ).json()["data"]

    response = await client.put(
        "/api/recipes",
        json={
            "id": created["id"],
            "name": "新菜",
            "elements": [{"name": "鸡蛋", "type": "ingredient", "operate": "add"}],
            "detail": None,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "新菜"
    assert {"番茄", "鸡蛋"} <= set(_element_names(data, "ingredient"))


async def test_update_recipe_removes_element(client):
    created = (
        await client.post(
            "/api/recipes",
            json={
                "name": "减料菜",
                "elements": [{"name": "番茄", "type": "ingredient"}],
            },
        )
    ).json()["data"]
    tomato_id = _element_id("ingredient", "番茄")
    assert tomato_id is not None

    response = await client.put(
        "/api/recipes",
        json={
            "id": created["id"],
            "name": "减料菜",
            "elements": [
                {
                    "id": tomato_id,
                    "name": "番茄",
                    "type": "ingredient",
                    "operate": "remove",
                }
            ],
            "detail": None,
        },
    )

    assert _element_names(response.json()["data"], "ingredient") == []


async def test_update_recipe_edit_time(client):
    created = (
        await client.post(
            "/api/recipes",
            json={
                "name": "改时间",
                "elements": [{"name": "45", "type": "time"}],
            },
        )
    ).json()["data"]
    time_id = _element_id("time", "45")
    assert time_id is not None

    response = await client.put(
        "/api/recipes",
        json={
            "id": created["id"],
            "name": "改时间",
            "elements": [
                {"id": time_id, "name": "60", "type": "time", "operate": "edit"}
            ],
            "detail": None,
        },
    )

    assert _element_names(response.json()["data"], "time") == ["60"]


async def test_update_recipe_adds_detail_writes_md(client):
    created = (
        await client.post(
            "/api/recipes",
            json={"name": "后补做法", "elements": [], "detail": None},
        )
    ).json()["data"]

    response = await client.put(
        "/api/recipes",
        json={
            "id": created["id"],
            "name": "后补做法",
            "elements": [],
            "detail": "后补的步骤",
        },
    )

    assert response.json()["data"]["has_detail"] is True
    detail = await _detail(client, created["id"])
    assert detail["detail"] == "后补的步骤"


async def test_update_recipe_clears_detail_deletes_md(client):
    created = (
        await client.post(
            "/api/recipes",
            json={"name": "清空做法", "elements": [], "detail": "原始步骤"},
        )
    ).json()["data"]
    file_path = _recipes_dir() / f"r-{created['id']}.md"
    assert file_path.exists()

    response = await client.put(
        "/api/recipes",
        json={
            "id": created["id"],
            "name": "清空做法",
            "elements": [],
            "detail": "",
        },
    )

    assert response.json()["data"]["has_detail"] is False
    assert not file_path.exists()
    detail = await _detail(client, created["id"])
    assert detail["detail"] is None


async def test_update_recipe_single_value_violation_rolls_back(client):
    created = (
        await client.post(
            "/api/recipes",
            json={
                "name": "唯一难度",
                "elements": [{"name": "简单", "type": "difficulty"}],
            },
        )
    ).json()["data"]

    response = await client.put(
        "/api/recipes",
        json={
            "id": created["id"],
            "name": "唯一难度",
            "elements": [{"name": "困难", "type": "difficulty", "operate": "add"}],
            "detail": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422

    # 事务回滚：原难度保持不变。
    detail = await _detail(client, created["id"])
    assert _element_names(detail, "difficulty") == ["简单"]


async def test_update_recipe_not_found(client):
    response = await client.put(
        "/api/recipes",
        json={"id": 9999, "name": "x", "elements": [], "detail": None},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


async def test_update_recipe_empty_name_rejected(client):
    created = (
        await client.post("/api/recipes", json={"name": "有名", "elements": []})
    ).json()["data"]

    response = await client.put(
        "/api/recipes",
        json={"id": created["id"], "name": "", "elements": [], "detail": None},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


# ---------------------------------------------------------------------------
# 删除
# ---------------------------------------------------------------------------


async def test_delete_recipe_removes_row_links_and_file(client):
    created = (
        await client.post(
            "/api/recipes",
            json={
                "name": "待删菜",
                "elements": [{"name": "番茄", "type": "ingredient"}],
                "detail": "待删步骤",
            },
        )
    ).json()["data"]
    file_path = _recipes_dir() / f"r-{created['id']}.md"
    assert file_path.exists()

    response = await client.request(
        "DELETE", "/api/recipes", json={"id": created["id"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] is None
    assert not file_path.exists()

    # 删除后详情接口忽略该 id（返回空数组）。
    detail = await client.get("/api/recipes/detail", params={"ids": created["id"]})
    assert detail.json()["data"] == []

    with connection() as conn:
        links = conn.execute(
            "SELECT id FROM t_recipe_element WHERE recipe_id = ?", (created["id"],)
        ).fetchall()
    assert links == []


async def test_delete_recipe_updates_list_total(client):
    created = await _create(client, "待删菜")
    assert _recipe_count() == 1

    response = await client.request(
        "DELETE", "/api/recipes", json={"id": created["id"]}
    )

    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert _recipe_count() == 0


async def test_delete_recipe_not_found(client):
    response = await client.request("DELETE", "/api/recipes", json={"id": 9999})

    assert response.status_code == 200
    assert response.json()["code"] == 404
