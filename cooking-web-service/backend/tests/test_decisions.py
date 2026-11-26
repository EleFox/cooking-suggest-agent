"""决策接口测试。

对应 S3 ``design/sprints/S3/api.md``：请求要素使用 ``relation_type``；服务端
enrich 要素并把 ``dedup_ids`` 翻译为完整菜谱后透传给 Agent；响应 ``data`` 直接
为卡片数组（``elements`` + ``has_detail``）。
"""

import pytest

from app.core.database import connection
from app.services import decision_service
from app.services.agent_client import AgentServiceError


def _technique_id() -> int:
    """返回第一个料理手段要素 id。"""
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM t_element WHERE type = 'technique' "
            "ORDER BY sort_order LIMIT 1"
        ).fetchone()
    return row["id"]


def _time_id() -> int:
    """返回第一个时间档位要素 id。"""
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM t_element WHERE type = 'time' ORDER BY sort_order LIMIT 1"
        ).fetchone()
    return row["id"]


@pytest.fixture
def mock_get_recipe_ids(monkeypatch):
    """替身：把决策服务中的 Agent 调用替换为可控的假实现。"""

    def _factory(ids):
        def _impl(count, elements=None, dedup=None):
            return ids

        monkeypatch.setattr(decision_service, "get_recipe_ids", _impl)

    return _factory


async def _create_recipe(client, name: str, time_minutes: int = 30) -> int:
    """通过接口创建一条菜谱，返回其 id（用于决策卡片组装测试）。"""
    response = await client.post(
        "/api/recipes",
        json={
            "name": name,
            "elements": [
                {"name": "炒", "type": "technique"},
                {"name": str(time_minutes), "type": "time"},
                {"name": "简单", "type": "difficulty"},
                {"name": "鸡蛋", "type": "ingredient"},
            ],
        },
    )
    return response.json()["data"]["id"]


async def test_decision_returns_one_card_on_first_request(client, mock_get_recipe_ids):
    recipe_id = await _create_recipe(client, "测试菜")
    mock_get_recipe_ids([recipe_id])

    response = await client.post(
        "/api/decisions",
        json={"count": 1, "dedup_ids": [], "elements": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "ok"
    cards = body["data"]
    assert len(cards) == 1
    card = cards[0]
    assert set(card.keys()) == {"id", "name", "elements", "has_detail"}
    assert card["id"] == recipe_id
    assert isinstance(card["elements"], list)
    assert isinstance(card["has_detail"], bool)


async def test_decision_assembles_cards_from_agent_ids(client, mock_get_recipe_ids):
    # 创建两条菜谱，验证卡片按 Agent 返回的 id 组装。
    first = await _create_recipe(client, "甲菜")
    second = await _create_recipe(client, "乙菜")
    mock_get_recipe_ids([first, second])

    response = await client.post(
        "/api/decisions",
        json={"count": 2, "dedup_ids": [], "elements": []},
    )

    assert response.status_code == 200
    cards = response.json()["data"]
    assert len(cards) == 2
    assert {card["id"] for card in cards} == {first, second}


async def test_decision_returns_no_result_when_agent_returns_empty(
    client, mock_get_recipe_ids
):
    mock_get_recipe_ids([])

    response = await client.post(
        "/api/decisions",
        json={"count": 1, "dedup_ids": [], "elements": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == []
    assert body["message"] == "没有合适的菜了"


async def test_decision_returns_error_envelope_when_agent_fails(
    client, mock_get_recipe_ids, monkeypatch
):
    def _fail(count, elements=None, dedup=None):
        raise AgentServiceError("boom")

    monkeypatch.setattr(decision_service, "get_recipe_ids", _fail)

    response = await client.post(
        "/api/decisions",
        json={"count": 1, "dedup_ids": [], "elements": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 500
    assert body["data"] is None
    assert body["message"] == "服务暂时不可用，请稍后重试"


async def test_decision_count_zero_rejected(client):
    response = await client.post(
        "/api/decisions",
        json={"count": 0, "dedup_ids": [], "elements": []},
    )

    assert response.status_code == 422


async def test_decision_invalid_relation_type_rejected(client):
    response = await client.post(
        "/api/decisions",
        json={
            "count": 1,
            "dedup_ids": [],
            "elements": [
                {"type": "technique", "element_id": 1, "relation_type": "love"}
            ],
        },
    )

    assert response.status_code == 422


async def test_decision_missing_element_id_rejected(client):
    response = await client.post(
        "/api/decisions",
        json={
            "count": 1,
            "dedup_ids": [],
            "elements": [{"type": "technique", "relation_type": "preference"}],
        },
    )

    assert response.status_code == 422


async def test_decision_forwards_enriched_elements_to_agent(client, monkeypatch):
    seen = {}

    def _capture(count, elements=None, dedup=None):
        seen["elements"] = elements
        return [1]

    monkeypatch.setattr(decision_service, "get_recipe_ids", _capture)

    technique_id = _technique_id()
    time_id = _time_id()
    with connection() as conn:
        technique = conn.execute(
            "SELECT name, sort_order FROM t_element WHERE id = ?", (technique_id,)
        ).fetchone()
        time_row = conn.execute(
            "SELECT name, sort_order FROM t_element WHERE id = ?", (time_id,)
        ).fetchone()
    await client.post(
        "/api/decisions",
        json={
            "count": 1,
            "dedup_ids": [],
            "elements": [
                {
                    "type": "technique",
                    "element_id": technique_id,
                    "relation_type": "preference",
                },
                {
                    "type": "time",
                    "element_id": time_id,
                    "relation_type": "preference",
                },
            ],
        },
    )

    assert seen["elements"] == [
        {
            "id": technique_id,
            "type": "technique",
            "name": technique["name"],
            "sort_order": technique["sort_order"],
            "relation_type": "preference",
        },
        {
            "id": time_id,
            "type": "time",
            "name": time_row["name"],
            "sort_order": time_row["sort_order"],
            "relation_type": "preference",
        },
    ]


async def test_decision_forwards_taboo_relation_type(client, monkeypatch):
    # 成员禁忌：relation_type=taboo 必须原样透传给 Agent。
    seen = {}

    def _capture(count, elements=None, dedup=None):
        seen["elements"] = elements
        return [1]

    monkeypatch.setattr(decision_service, "get_recipe_ids", _capture)

    technique_id = _technique_id()
    await client.post(
        "/api/decisions",
        json={
            "count": 1,
            "dedup_ids": [],
            "elements": [
                {
                    "type": "technique",
                    "element_id": technique_id,
                    "relation_type": "taboo",
                }
            ],
        },
    )

    assert seen["elements"][0]["relation_type"] == "taboo"
    assert seen["elements"][0]["id"] == technique_id


async def test_decision_forwards_count_beyond_one(client, monkeypatch):
    # 生成数量：count>1 必须原样透传。
    seen = {}

    def _capture(count, elements=None, dedup=None):
        seen["count"] = count
        return [1]

    monkeypatch.setattr(decision_service, "get_recipe_ids", _capture)

    response = await client.post(
        "/api/decisions",
        json={"count": 3, "dedup_ids": [], "elements": []},
    )

    assert response.status_code == 200
    assert seen["count"] == 3


async def test_decision_translates_dedup_ids_to_full_recipes(client, monkeypatch):
    seen = {}

    def _capture(count, elements=None, dedup=None):
        seen["dedup"] = dedup
        return [1]

    monkeypatch.setattr(decision_service, "get_recipe_ids", _capture)

    response = await client.post(
        "/api/recipes",
        json={
            "name": "去重菜",
            "elements": [{"name": "番茄", "type": "ingredient"}],
            "detail": "先切再炒",
        },
    )
    recipe_id = response.json()["data"]["id"]

    await client.post(
        "/api/decisions",
        json={"count": 1, "dedup_ids": [recipe_id], "elements": []},
    )

    assert len(seen["dedup"]) == 1
    recipe = seen["dedup"][0]
    assert set(recipe.keys()) == {"id", "name", "elements", "detail"}
    assert recipe["id"] == recipe_id
    assert recipe["detail"] == "先切再炒"
    assert recipe["elements"][0]["type"] == "ingredient"


async def test_decision_dedup_missing_id_ignored(client, monkeypatch):
    seen = {}

    def _capture(count, elements=None, dedup=None):
        seen["dedup"] = dedup
        return [1]

    monkeypatch.setattr(decision_service, "get_recipe_ids", _capture)

    await client.post(
        "/api/decisions",
        json={"count": 1, "dedup_ids": [9999], "elements": []},
    )

    assert seen["dedup"] == []


async def test_decision_nonexistent_element_id_rejected(client):
    with connection() as conn:
        max_id = conn.execute("SELECT MAX(id) AS m FROM t_element").fetchone()["m"]

    response = await client.post(
        "/api/decisions",
        json={
            "count": 1,
            "dedup_ids": [],
            "elements": [
                {
                    "type": "technique",
                    "element_id": max_id + 100,
                    "relation_type": "preference",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_decision_element_type_mismatch_rejected(client):
    # time 类型要素的 id 却声明为 technique，类型与实际不符。
    time_id = _time_id()

    response = await client.post(
        "/api/decisions",
        json={
            "count": 1,
            "dedup_ids": [],
            "elements": [
                {
                    "type": "technique",
                    "element_id": time_id,
                    "relation_type": "preference",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_decision_card_time_from_time_element(client, mock_get_recipe_ids):
    # 菜谱预估时间来自其 time 要素（45 分钟）。
    recipe_id = await _create_recipe(client, "计时菜", time_minutes=45)
    mock_get_recipe_ids([recipe_id])

    response = await client.post(
        "/api/decisions",
        json={"count": 1, "dedup_ids": [], "elements": []},
    )

    assert response.status_code == 200
    card = response.json()["data"][0]
    assert card["id"] == recipe_id
    times = [e["name"] for e in card["elements"] if e["type"] == "time"]
    assert times == ["45"]
