"""Agent 服务 HTTP 客户端。

封装对独立 Agent 服务的调用（``POST /api/recipes``），使前端永不直接访问
Agent 服务。所有对外调用均通过本模块，并记录请求/响应/耗时/错误日志。

调用方向：

    Frontend -> FastAPI -> AgentClient -> HTTP -> Agent Service
"""

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Agent 服务业务接口路径（对应 agent 服务 ``docs/api.md`` 的 ``POST /api/recipes``）。
RECIPES_PATH = "/api/recipes"


class AgentServiceError(Exception):
    """Agent 服务调用失败（网络错误、超时或返回非成功状态）。"""


def _summarize_payload(payload: dict) -> dict:
    """构造用于日志的请求摘要：省略 dedup 中最长的做法正文 ``detail``。

    Args:
        payload: 实际发给 Agent 的请求体。

    Returns:
        浅拷贝后的摘要；``dedup[].detail`` 替换为长度标记，避免日志过长。
    """
    summary = dict(payload)
    dedup = summary.get("dedup")
    if dedup:
        summary["dedup"] = [
            {
                **item,
                "detail": (
                    None
                    if item.get("detail") is None
                    else f"<detail {len(item['detail'])} chars omitted>"
                ),
            }
            for item in dedup
        ]
    return summary


def get_recipe_ids(
    count: int,
    elements: list[dict] | None = None,
    dedup: list[dict] | None = None,
) -> list[int]:
    """触发 Agent 获取 ``count`` 个菜谱 id。

    调用 Agent 服务的 ``POST /api/recipes``，把富化后的偏好要素
    （``{id, type, name, sort_order, relation_type}``）与翻译后的去重菜谱
    （``{id, name, elements, detail}``）一并透传给 Agent，从统一信封中取出
    ``data``（菜谱 id 数组）。超时或非 200 状态码视为失败，抛出自定义异常由
    上层兜底。

    Args:
        count: 需要获取的菜谱数量（>= 1）。
        elements: 富化后的偏好要素字典列表，可为空。
        dedup: 去重菜谱完整数据列表（含做法正文），可为空。

    Returns:
        Agent 返回的菜谱 id 列表（可能为空，表示无合适菜谱）。

    Raises:
        AgentServiceError: Agent 服务不可用、超时或返回非成功状态码。
    """
    settings = get_settings()
    url = f"{settings.agent_service_url}{RECIPES_PATH}"
    # elements / dedup 始终显式携带（可为空数组），避免 Agent 端误判为“未传”。
    payload: dict = {
        "count": count,
        "elements": elements or [],
        "dedup": dedup or [],
    }

    try:
        logger.info(
            "agent request: POST %s count=%s elements=%d dedup=%d body=%s",
            url,
            count,
            len(elements or []),
            len(dedup or []),
            _summarize_payload(payload),
        )
        with httpx.Client(timeout=settings.agent_service_timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("agent request failed: url=%s error=%s", url, exc)
        raise AgentServiceError(str(exc)) from exc

    body = response.json()
    if body.get("code") != 200:
        logger.error(
            "agent returned non-200 envelope: url=%s code=%s message=%s",
            url,
            body.get("code"),
            body.get("message"),
        )
        raise AgentServiceError(body.get("message") or "agent returned error")

    recipe_ids = body.get("data") or []
    logger.info("agent request ok: url=%s ids=%s", url, recipe_ids)
    return recipe_ids
