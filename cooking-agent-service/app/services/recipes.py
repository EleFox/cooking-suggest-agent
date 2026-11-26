"""获取菜谱服务层。

接收接口层传入的请求参数，构造 ``agent`` 的入参模型后调用
``agent.services.recipes.invoke_get_recipes`` 执行 Agent 工作流，
并将 Agent 返回的菜谱 id 数组直接透传给接口层。
"""

import time

from agent.schemas.recipes_agent import DecisionElement, GetRecipesParams, Recipe
from agent.services.recipes import invoke_get_recipes
from common.logging import get_logger

logger = get_logger(__name__)


def get_recipes(
    count: int,
    elements: list[DecisionElement] | None = None,
    dedup: list[Recipe] | None = None,
) -> list[int]:
    """调用 Agent 获取菜谱 id 数组。

    Args:
        count: 需要获取的菜谱数量。
        elements: 富化后的偏好/禁忌要素数组，可为空。
        dedup: 已展示菜谱翻译成的完整去重列表，可为空。

    Returns:
        Agent 返回的菜谱 id 数组，服务层直接透传、不做加工。

    Raises:
        Exception: Agent 执行异常时向上抛出，由接口层统一兜底处理。
    """
    start = time.perf_counter()
    logger.info(
        "agent get_recipes request: count=%d, elements=%d, dedup=%d",
        count,
        len(elements or []),
        len(dedup or []),
    )
    try:
        result = invoke_get_recipes(
            GetRecipesParams(
                count=count,
                elements=elements or [],
                dedup=dedup or [],
            )
        )
    except Exception:
        logger.exception("agent get_recipes failed: count=%d", count)
        raise
    duration = time.perf_counter() - start
    logger.info("agent get_recipes response: %s, duration=%.3fs", result, duration)
    return result
