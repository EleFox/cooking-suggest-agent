"""要素查询接口测试。

对应 S2 ``design/sprints/S2/api.md`` 的 ``GET /api/elements``。
"""

# 要素查询接口的 type 参数取值范围，与接口设计一致。
VALID_TYPES = {"technique", "time"}


async def test_list_technique_elements_returns_sorted(client):
    response = await client.get("/api/elements", params={"type": "technique"})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    items = body["data"]
    assert len(items) == 8
    for item in items:
        assert set(item.keys()) == {"id", "type", "name", "sort_order"}
        assert item["type"] == "technique"
    # 名称与 sort_order 均按种子顺序升序。
    assert [item["name"] for item in items] == [
        "煎",
        "炒",
        "凉拌",
        "油炸",
        "蒸",
        "炖",
        "煮",
        "烤",
    ]
    sort_orders = [item["sort_order"] for item in items]
    assert sort_orders == sorted(sort_orders)


async def test_list_time_elements_returns_tiers(client):
    response = await client.get("/api/elements", params={"type": "time"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert [item["name"] for item in items] == ["15", "30", "60"]
    assert all(item["type"] == "time" for item in items)


async def test_missing_type_rejected(client):
    response = await client.get("/api/elements")

    assert response.status_code == 422


async def test_invalid_type_rejected(client):
    response = await client.get("/api/elements", params={"type": "ingredient"})

    assert response.status_code == 422


async def test_list_difficulty_elements_returns_options(client):
    response = await client.get("/api/elements", params={"type": "difficulty"})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    items = body["data"]
    assert [item["name"] for item in items] == ["简单", "一般", "困难"]
    assert all(item["type"] == "difficulty" for item in items)
    sort_orders = [item["sort_order"] for item in items]
    assert sort_orders == sorted(sort_orders)
    assert all(order > 0 for order in sort_orders)


async def test_validation_error_returns_envelope(client):
    response = await client.get("/api/elements")

    assert response.status_code == 422
    body = response.json()
    assert set(body.keys()) == {"code", "data", "message"}
    assert body["code"] == 422
    assert body["data"] is None
    assert body["message"]
