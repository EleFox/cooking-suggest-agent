"""web-service 菜谱接口客户端测试。

使用 ``httpx.MockTransport`` 拦截 HTTP，验证请求构造、信封解析与异常处理，
避免真实网络调用。
"""

import httpx
import pytest
from pydantic import ValidationError

from app.services.recipe_client import (
    RecipeServiceError,
    fetch_recipe_details,
    fetch_recipe_summaries,
)


def _client_factory(handler):
    """把 handler 注入到 recipe_client 使用的 httpx.Client 中。"""
    original = httpx.Client

    def _factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    return _factory


def _summary_body() -> dict:
    return {
        "code": 200,
        "data": {
            "list": [
                {
                    "id": 1,
                    "name": "番茄牛腩煲",
                    "elements": [
                        {
                            "id": 21,
                            "type": "ingredient",
                            "name": "番茄",
                            "sort_order": 1,
                        }
                    ],
                    "has_detail": True,
                }
            ],
            "has_next": False,
            "total": 1,
            "page": 1,
            "page_size": 20,
        },
        "message": "ok",
    }


def test_fetch_recipe_summaries_parses_page(monkeypatch):
    """正向路径：按分页参数请求并解析列表结构。"""

    def handler(request):
        assert request.url.path == "/api/recipes"
        assert dict(request.url.params) == {"page": "2", "page_size": "5"}
        return httpx.Response(200, json=_summary_body())

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = fetch_recipe_summaries(page=2, page_size=5)

    assert result.total == 1
    assert result.has_next is False
    assert [item.id for item in result.list] == [1]
    assert result.list[0].elements[0].name == "番茄"


def test_fetch_recipe_summaries_empty_list(monkeypatch):
    """边界情况：空列表正常解析为空数组、总数 0。"""
    body = _summary_body()
    body["data"]["list"] = []
    body["data"]["total"] = 0

    def handler(request):
        return httpx.Response(200, json=body)

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = fetch_recipe_summaries()

    assert result.list == []
    assert result.total == 0


def test_fetch_recipe_summaries_forwards_exclude_ids(monkeypatch):
    """正向路径：排除 id 数组拼接为逗号串传给 web-service。"""

    def handler(request):
        assert dict(request.url.params) == {
            "page": "1",
            "page_size": "20",
            "exclude_recipe_ids": "3,7,9",
        }
        return httpx.Response(200, json=_summary_body())

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = fetch_recipe_summaries(page=1, page_size=20, exclude_recipe_ids=[3, 7, 9])

    assert result.total == 1


def test_fetch_recipe_summaries_omits_empty_exclude_ids(monkeypatch):
    """边界情况：排除数组为空时不传 exclude_recipe_ids。"""

    def handler(request):
        assert "exclude_recipe_ids" not in request.url.params
        return httpx.Response(200, json=_summary_body())

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    fetch_recipe_summaries(page=1, page_size=20, exclude_recipe_ids=[])


def test_fetch_recipe_summaries_invalid_page_raises(monkeypatch):
    """无效输入：页码小于 1 时参数校验失败，且不发起请求。"""

    def handler(request):  # pragma: no cover - 不应被调用
        raise AssertionError("不应发起请求")

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    with pytest.raises(ValidationError):
        fetch_recipe_summaries(page=0)


def test_fetch_recipe_summaries_raises_on_non_200_envelope(monkeypatch):
    """异常路径：信封 code 非 200 时抛出服务异常。"""

    def handler(request):
        return httpx.Response(
            200, json={"code": 500, "data": None, "message": "服务器内部错误"}
        )

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    with pytest.raises(RecipeServiceError):
        fetch_recipe_summaries()


def test_fetch_recipe_summaries_uses_fallback_message(monkeypatch):
    """异常路径：web-service 未给 message 时回退到文档定义的文案。"""

    def handler(request):
        return httpx.Response(200, json={"code": 502, "data": None})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    with pytest.raises(RecipeServiceError, match="上游服务不可用"):
        fetch_recipe_summaries()


def test_fetch_recipe_summaries_raises_on_http_error(monkeypatch):
    """异常路径：网络错误时抛出服务异常。"""

    def handler(request):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    with pytest.raises(RecipeServiceError):
        fetch_recipe_summaries()


def test_fetch_recipe_details_joins_ids(monkeypatch):
    """正向路径：id 数组自动拼接为逗号串并按详情解析。"""

    def handler(request):
        assert request.url.path == "/api/recipes/detail"
        assert dict(request.url.params) == {"ids": "1,2,3"}
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": [{"id": 1, "name": "菜", "elements": [], "detail": "做法"}],
                "message": "ok",
            },
        )

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    result = fetch_recipe_details([1, 2, 3])

    assert [item.id for item in result] == [1]
    assert result[0].detail == "做法"


def test_fetch_recipe_details_empty_ids_skips_request(monkeypatch):
    """边界情况：id 数组为空时直接返回空数组，不发起请求。"""
    called = {"hit": False}

    def handler(request):  # pragma: no cover - 不应被调用
        called["hit"] = True
        return httpx.Response(200, json={"code": 200, "data": [], "message": "ok"})

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    assert fetch_recipe_details([]) == []
    assert called["hit"] is False


def test_fetch_recipe_details_raises_on_non_200_envelope(monkeypatch):
    """异常路径：信封 code 非 200 时抛出服务异常。"""

    def handler(request):
        return httpx.Response(
            200, json={"code": 422, "data": None, "message": "ids 参数非法"}
        )

    monkeypatch.setattr(httpx, "Client", _client_factory(handler))

    with pytest.raises(RecipeServiceError):
        fetch_recipe_details([1, 2])
