"""Agent 客户端单元测试。

使用 ``httpx.MockTransport`` 拦截 HTTP，验证请求构造、信封解析与异常处理，
避免真实网络调用。
"""

import httpx
import pytest

from app.services import agent_client
from app.services.agent_client import RECIPES_PATH, AgentServiceError, get_recipe_ids


def _client_factory(handler):
    """把 handler 注入到 agent_client 使用的 httpx.Client 中。"""
    original = httpx.Client

    def _factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    return _factory


def test_get_recipe_ids_returns_data_ids(monkeypatch):
    import json

    def handler(request):
        assert request.url.path == RECIPES_PATH
        assert json.loads(request.content) == {
            "count": 3,
            "elements": [],
            "dedup": [],
        }
        return httpx.Response(
            200, json={"code": 200, "data": [2, 3, 5], "message": "ok"}
        )

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    assert get_recipe_ids(3) == [2, 3, 5]


def test_get_recipe_ids_forwards_elements(monkeypatch):
    import json

    elements = [
        {
            "id": 3,
            "type": "technique",
            "name": "炖",
            "sort_order": 1,
            "relation_type": "preference",
        },
        {
            "id": 5,
            "type": "time",
            "name": "30",
            "sort_order": 2,
            "relation_type": "preference",
        },
    ]

    def handler(request):
        assert json.loads(request.content) == {
            "count": 2,
            "elements": elements,
            "dedup": [],
        }
        return httpx.Response(200, json={"code": 200, "data": [1], "message": "ok"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    assert get_recipe_ids(2, elements) == [1]


def test_get_recipe_ids_forwards_dedup_recipes(monkeypatch):
    import json

    elements = [
        {
            "id": 3,
            "type": "technique",
            "name": "炖",
            "sort_order": 1,
            "relation_type": "taboo",
        }
    ]
    dedup = [
        {
            "id": 7,
            "name": "去重菜",
            "elements": [{"id": 3, "type": "technique", "name": "炖", "sort_order": 1}],
            "detail": "先切再炒",
        }
    ]

    def handler(request):
        assert json.loads(request.content) == {
            "count": 1,
            "elements": elements,
            "dedup": dedup,
        }
        return httpx.Response(200, json={"code": 200, "data": [2], "message": "ok"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    assert get_recipe_ids(1, elements, dedup) == [2]


def test_get_recipe_ids_includes_empty_arrays_when_no_context(monkeypatch):
    import json

    def handler(request):
        assert json.loads(request.content) == {
            "count": 1,
            "elements": [],
            "dedup": [],
        }
        return httpx.Response(200, json={"code": 200, "data": [], "message": "ok"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    assert get_recipe_ids(1, [], []) == []


def test_get_recipe_ids_empty_data_returns_empty(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"code": 200, "data": [], "message": "ok"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    assert get_recipe_ids(1) == []


def test_get_recipe_ids_uses_config_url(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"code": 200, "data": [1], "message": "ok"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))
    monkeypatch.setenv("AGENT_SERVICE_URL", "http://agent-host:9000")
    agent_client.get_settings.cache_clear()

    get_recipe_ids(1)
    assert seen["url"] == f"http://agent-host:9000{RECIPES_PATH}"


def test_get_recipe_ids_raises_on_non_200_envelope(monkeypatch):
    def handler(request):
        return httpx.Response(
            200, json={"code": 422, "data": None, "message": "count 非法"}
        )

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    with pytest.raises(AgentServiceError):
        get_recipe_ids(1)


def test_get_recipe_ids_raises_on_http_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    with pytest.raises(AgentServiceError):
        get_recipe_ids(1)


def test_summarize_payload_omits_detail_without_mutating():
    payload = {
        "count": 1,
        "elements": [
            {
                "id": 1,
                "type": "technique",
                "name": "炒",
                "sort_order": 1,
                "relation_type": "preference",
            }
        ],
        "dedup": [
            {"id": 7, "name": "旧菜", "elements": [], "detail": "很长的做法正文"}
        ],
    }

    summary = agent_client._summarize_payload(payload)

    assert summary["count"] == 1
    assert summary["elements"] == payload["elements"]
    assert summary["dedup"][0]["detail"] != "很长的做法正文"
    assert "omitted" in summary["dedup"][0]["detail"]
    # 不修改原始 payload。
    assert payload["dedup"][0]["detail"] == "很长的做法正文"


def test_get_recipe_ids_logs_element_count_and_omits_detail(monkeypatch, caplog):
    import logging

    def handler(request):
        return httpx.Response(200, json={"code": 200, "data": [1], "message": "ok"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    elements = [
        {
            "id": 3,
            "type": "technique",
            "name": "炖",
            "sort_order": 1,
            "relation_type": "preference",
        }
    ]
    dedup = [
        {"id": 7, "name": "去重菜", "elements": [], "detail": "很长的做法正文内容"}
    ]

    with caplog.at_level(logging.INFO):
        get_recipe_ids(1, elements, dedup)

    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "elements=1" in messages
    assert "dedup=1" in messages
    assert "chars omitted" in messages
    assert "很长的做法正文内容" not in messages
