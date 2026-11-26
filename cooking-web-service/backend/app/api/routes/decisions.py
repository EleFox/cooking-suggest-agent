"""决策接口路由。

对应 ``design/sprints/S2/api.md`` 中的 ``POST /api/decisions``。
路由层仅处理请求/响应，业务逻辑委托给服务层。

决策会同步等待外部 Agent（可能长达数百秒），因此本路由保持 ``async`` 并把
阻塞的 ``decide`` 投递到**决策专用线程池**，避免阻塞事件循环与默认请求
线程池，保证 Agent 的反向数据面调用仍可被处理。
"""

import asyncio

from fastapi import APIRouter

from app.core.concurrency import get_decision_executor
from app.core.logging import get_logger
from app.schemas.decision import DecisionRequest
from app.schemas.envelope import Envelope, error, ok
from app.services.agent_client import AgentServiceError
from app.services.decision_service import NO_RESULT_MESSAGE, decide
from app.services.errors import ApiError

logger = get_logger(__name__)

router = APIRouter()

# Agent 服务异常 / 超时时的兜底提示文案（对应 S2 api.md 的错误信封）。
SERVICE_UNAVAILABLE_MESSAGE = "服务暂时不可用，请稍后重试"


@router.post("/decisions", response_model=Envelope)
async def create_decision(request: DecisionRequest) -> Envelope:
    """生成一张菜谱卡片（首次生成与"再来一道"复用同一接口）。

    Args:
        request: 决策请求（数量、去重列表、要素偏好）。

    Returns:
        统一信封包裹的决策结果（``data`` 直接为卡片数组）；偏好校验失败返回
        422，Agent 不可用/超时返回 500 错误信封。
    """
    logger.debug("decision request received: count=%s", request.count)
    loop = asyncio.get_running_loop()
    try:
        cards = await loop.run_in_executor(get_decision_executor(), decide, request)
    except ApiError as exc:
        logger.debug(
            "decision validation failed: code=%s message=%s", exc.code, exc.message
        )
        return error(code=exc.code, message=exc.message)
    except AgentServiceError:
        logger.error("decision failed: agent service unavailable")
        return error(code=500, message=SERVICE_UNAVAILABLE_MESSAGE)
    if not cards:
        return ok(data=[], message=NO_RESULT_MESSAGE)
    return ok(data=cards)
