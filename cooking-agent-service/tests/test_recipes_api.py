"""获取菜谱接口测试。"""

from unittest.mock import patch


def _full_payload() -> dict:
    """构造带要素与去重菜谱的完整请求体。"""
    return {
        "count": 1,
        "elements": [
            {
                "id": 3,
                "type": "technique",
                "name": "炖",
                "sort_order": 1,
                "relation_type": "preference",
            }
        ],
        "dedup": [
            {
                "id": 7,
                "name": "去重菜",
                "elements": [
                    {"id": 3, "type": "technique", "name": "炖", "sort_order": 1}
                ],
                "detail": "先切再炒",
            }
        ],
    }


async def test_get_recipes_happy_path(client):
    """正向路径：返回 200 信封，data 为菜谱 id 数组。"""
    with patch("app.services.recipes.get_recipes", return_value=[2, 3, 5]):
        response = await client.post("/api/recipes", json={"count": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == [2, 3, 5]
    assert body["message"] == "ok"


async def test_get_recipes_empty_result_is_ok(client):
    """边界情况：Agent 无结果时为空数组，属正常业务结果（200）。"""
    with patch("app.services.recipes.get_recipes", return_value=[]):
        response = await client.post("/api/recipes", json={"count": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == []
    assert body["message"] == "ok"


async def test_get_recipes_single_count(client):
    """边界情况：数量为 1 时返回单元素数组。"""
    with patch("app.services.recipes.get_recipes", return_value=[7]):
        response = await client.post("/api/recipes", json={"count": 1})

    assert response.status_code == 200
    assert response.json()["data"] == [7]


async def test_get_recipes_missing_count_returns_422(client):
    """无效输入：缺少 count 时返回 422。"""
    response = await client.post("/api/recipes", json={})

    assert response.status_code == 422


async def test_get_recipes_zero_count_returns_422(client):
    """无效输入：count 为 0 时返回 422。"""
    response = await client.post("/api/recipes", json={"count": 0})

    assert response.status_code == 422


async def test_get_recipes_negative_count_returns_422(client):
    """无效输入：count 为负数时返回 422。"""
    response = await client.post("/api/recipes", json={"count": -1})

    assert response.status_code == 422


async def test_get_recipes_non_integer_count_returns_422(client):
    """无效输入：count 为非整数时返回 422。"""
    response = await client.post("/api/recipes", json={"count": "three"})

    assert response.status_code == 422


async def test_get_recipes_accepts_elements_and_dedup(client):
    """正向路径：携带要素与去重菜谱的请求被接受并返回 200。"""
    with patch("app.services.recipes.get_recipes", return_value=[1]):
        response = await client.post("/api/recipes", json=_full_payload())

    assert response.status_code == 200
    assert response.json()["data"] == [1]


async def test_get_recipes_invalid_relation_type_returns_422(client):
    """无效输入：relation_type 非 preference/taboo 时返回 422。"""
    payload = _full_payload()
    payload["elements"][0]["relation_type"] = "unknown"

    response = await client.post("/api/recipes", json=payload)

    assert response.status_code == 422


async def test_get_recipes_dedup_missing_id_returns_422(client):
    """无效输入：去重菜谱缺少 id 时返回 422。"""
    payload = _full_payload()
    del payload["dedup"][0]["id"]

    response = await client.post("/api/recipes", json=payload)

    assert response.status_code == 422
