"""菜谱相关 agent 逻辑的服务。

负责把 web-service 透传的 :class:`GetRecipesParams` 转换为 LangGraph 工作流的
初始 :class:`RecipeAgentState`，执行决策工作流，再把工作流产出的推荐菜谱转换为
web-service 约定的菜谱 id 数组（``list[int]``）返回。
"""

import time

from agent.graph.graph import cooking_suggest_agent
from agent.graph.state import RecipeAgentState
from agent.schemas.recipes_agent import (
    DecisionElement,
    Element,
    GetRecipesParams,
)
from common.logging import get_logger

logger = get_logger(__name__)


def _to_element(element: DecisionElement) -> Element:
    """剥离决策要素的关系类型，得到纯菜谱元素。"""
    return Element(
        id=element.id,
        type=element.type,
        name=element.name,
        sort_order=element.sort_order,
    )


def _build_initial_state(params: GetRecipesParams) -> RecipeAgentState:
    """把接口参数转换为工作流的初始 State。

    ``elements`` 按 ``relation_type`` 拆分为偏好 / 禁忌两个通道，供后续节点
    分别处理；``dedup``（上一次已展示的菜谱）写入 ``select_recipes`` 作为不可改
    的已选集合，避免重复推荐。查询控制字段（``pending_pages`` / ``attempts`` /
    ``fetched_pages`` 等）统一从零起始，由 ``PLAN`` / ``FETCH`` 节点在流程中填充。

    Args:
        params: web-service 透传的获取菜谱参数。

    Returns:
        初始 State：含偏好/禁忌要素、已选菜谱、空的产出通道与查询控制字段。
    """
    return {
        "messages": [],
        "count": params.count,
        "preference_elements": [
            _to_element(element)
            for element in params.elements
            if element.relation_type == "preference"
        ],
        "taboo_elements": [
            _to_element(element)
            for element in params.elements
            if element.relation_type == "taboo"
        ],
        "select_recipes": params.dedup,
        "reference_recipes": [],
        "result_recipes": [],
        "pending_pages": [],
        "page_size": 1,
        "page": 1,
        "total": 0,
        "attempts": 0,
        "fetched_pages": [],
    }


def invoke_get_recipes(params: GetRecipesParams) -> list[int]:
    """执行获取菜谱的 Agent 工作流，返回推荐菜谱 id 数组。

    Args:
        params: web-service 透传的获取菜谱参数（数量、偏好/禁忌要素、去重菜谱）。

    Returns:
        工作流最终决定的菜谱 id 数组；无合适菜谱时为空数组。

    Raises:
        Exception: 工作流执行异常时向上抛出，由服务层/接口层统一兜底。
    """
    start = time.perf_counter()
    logger.info(
        "invoke_get_recipes start: count=%d, elements=%d, dedup=%d",
        params.count,
        len(params.elements),
        len(params.dedup),
    )
    try:
        state = _build_initial_state(params)
        result = cooking_suggest_agent.invoke(state)
    except Exception:
        logger.exception("invoke_get_recipes failed: count=%d", params.count)
        raise

    recipe_ids = [recipe.id for recipe in result["result_recipes"]]
    logger.info(
        "invoke_get_recipes done: ids=%s, duration=%.3fs",
        recipe_ids,
        time.perf_counter() - start,
    )
    return recipe_ids
