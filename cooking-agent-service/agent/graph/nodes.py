"""Agent 图节点逻辑。

本模块定义菜谱挑选工作流的三个节点及其路由函数：

- :func:`plan_fetch_recipes`（``PLAN``）：统计可检索的候选菜谱总量，规划本轮
  需要并行拉取的页码；
- :func:`fetch_recipes`（``FETCH``）：按单页分页参数从 web-service 拉取菜谱摘要，
  作为决策候选；
- :func:`decision_result_recipes`（``DECISION``）：把候选菜谱与用户偏好/禁忌约束
  交给大模型，按约束过滤、打分并抽取最终推荐菜谱。

节点只返回对 ``RecipeAgentState`` 的增量更新；图的连边与条件路由在
``agent/graph/graph.py`` 中定义。本模块中的 ``dispatch_recipe_fetch`` /
``route_after_decision`` 为路由函数，仅负责选择下一跳节点。
"""

import json
import random
from typing import cast

from langchain.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END
from langgraph.types import Send
from trustcall import create_extractor

from agent.graph.llm import main_llm
from agent.graph.state import OutputState, RecipeAgentState
from agent.prompts.utils import load_prompt
from agent.schemas.recipes_agent import ResultRecipeList
from app.services.recipe_client import fetch_recipe_summaries
from common.logging import get_logger

# 最大查询轮次：候选反复不足时限制回环次数，避免工作流陷入死循环。
MAX_ATTEMPTS = 4

logger = get_logger(__name__)
extractor = create_extractor(
    main_llm,
    tools=[ResultRecipeList],
    tool_choice="ResultRecipeList",
)


def _total_pages(total: int, page_size: int) -> int:
    """由总数与每页条数推算总页数。"""
    if total <= 0 or page_size <= 0:
        return 0
    return (total + page_size - 1) // page_size


# 已废弃节点：早期「一次性让模型自行调工具查菜谱」的实现，现由
# PLAN → FETCH → DECISION 工作流取代，当前图未引用；待确认后移除。
def get_recipes(state: RecipeAgentState):
    """构建菜谱查询的状态"""
    result = fetch_recipe_summaries(1, 1)
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=load_prompt("system-get-recipes.md")),
            (
                "human",
                """菜谱总数为：{total}
需要返回的菜谱数量为：{count}""",
            ),
        ]
    )
    chain = prompt_template | main_llm
    recipes_result = chain.invoke({"total": result.total, "count": state["count"]})
    logger.info("模型输出：%s", recipes_result.content)
    recipes = ResultRecipeList.model_validate_json(cast(str, recipes_result.content))
    return {"result_recipes": recipes.list, "messages": recipes_result}


def plan_fetch_recipes(state: RecipeAgentState) -> dict:
    """规划本轮的菜谱查询计划。

    以「已选菜谱」为排除条件统计剩余候选总量：总量较多时按固定页大小随机抽取
    若干页并行查询，较少时直接整量查询；同时递增查询轮次，并在进入新一轮时清空
    上一轮候选。

    Args:
        state: 当前工作流状态，读取 ``attempts`` / ``select_recipes`` /
            ``reference_recipes``。

    Returns:
        状态增量字典，包含 ``attempts`` / ``total`` / ``page_size`` /
        ``pending_pages``；上一轮存在候选时附带清空后的 ``reference_recipes``。
    """
    update_state: dict = {"attempts": state["attempts"] + 1}
    update_state["total"] = fetch_recipe_summaries(
        1, 1, exclude_recipe_ids=[item.id for item in state["select_recipes"]]
    ).total
    if update_state["total"] > 20:
        update_state["page_size"] = 3
        page_total = _total_pages(update_state["total"], update_state["page_size"])
        # 候选较多时随机抽样页面，避免总是命中同一批低相关度菜谱。
        update_state["pending_pages"] = random.sample(range(1, page_total + 1), 4)
    else:
        update_state["page_size"] = update_state["total"]
        update_state["pending_pages"] = [1]
    if len(state["reference_recipes"]) > 0:
        update_state["reference_recipes"] = []
    return update_state


# 固定Node命名
PLAN = plan_fetch_recipes.__name__


def fetch_recipes(state: RecipeAgentState) -> dict:
    """按单页参数查询菜谱摘要，作为决策候选。

    Args:
        state: 由 :func:`dispatch_recipe_fetch` 通过 ``Send`` 注入的单页状态，
            包含 ``page`` / ``page_size`` / ``select_recipes``。

    Returns:
        状态增量字典：``reference_recipes`` 为当前页摘要，``fetched_pages``
        记录本次拉取的页码。
    """
    data = fetch_recipe_summaries(
        state["page"],
        state["page_size"],
        exclude_recipe_ids=[item.id for item in state["select_recipes"]],
    )
    logger.info("query_recipes: page=%d got=%d", state["page"], len(data.list))
    return {"reference_recipes": data.list, "fetched_pages": [state["page"]]}


# 固定Node命名
FETCH = fetch_recipes.__name__


def decision_result_recipes(state: RecipeAgentState) -> OutputState:
    """执行菜谱挑选决策，产出最终推荐菜谱。

    将偏好/禁忌要素、已选菜谱与本轮候选菜谱装配进提示词，交由大模型按约束过滤、
    打分并挑选，最后以结构化工具调用抽取推荐结果。候选为空时直接返回空结果，
    避免无意义的模型调用。

    Args:
        state: 当前工作流状态，读取 ``count`` / ``preference_elements`` /
            ``taboo_elements`` / ``select_recipes`` / ``reference_recipes``。

    Returns:
        输出状态增量：``result_recipes`` 为模型挑选出的菜谱摘要数组，
        无候选或模型未给出结果时为空数组。
    """
    result_recipes: list = []
    if len(state["reference_recipes"]) == 0:
        return {"result_recipes": result_recipes}
    prompt_template = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=load_prompt("system-get-recipes.md")),
            ("human", load_prompt("human-get-recipes.md")),
        ]
    )
    chain = prompt_template | extractor
    output = chain.invoke(
        {
            "count": state["count"],
            "preference_elements": json.dumps(
                [e.model_dump() for e in state["preference_elements"]],
                ensure_ascii=False,
            ),
            "taboo_elements": json.dumps(
                [e.model_dump() for e in state["taboo_elements"]], ensure_ascii=False
            ),
            "select_recipes": json.dumps(
                [r.model_dump() for r in state["select_recipes"]], ensure_ascii=False
            ),
            "reference_recipes": json.dumps(
                [r.model_dump() for r in state["reference_recipes"]], ensure_ascii=False
            ),
        }
    )
    tool_calls = output["messages"][-1].tool_calls
    recipe_data = ResultRecipeList(**tool_calls[0]["args"])
    recipe_list = recipe_data.list[:state["count"]] # 防止过多
    logger.info("查询菜谱返回值：%s", recipe_list)
    return {"result_recipes": recipe_list}


# 固定Node命名
DECISION = decision_result_recipes.__name__


def dispatch_recipe_fetch(state: RecipeAgentState) -> str | list[Send]:
    """路由：按待查页码扇出并行查询。

    Args:
        state: 当前工作流状态，读取 ``pending_pages`` / ``page_size`` /
            ``select_recipes``。

    Returns:
        待查页非空时返回一组 ``Send``（每页一个 ``FETCH`` 调用，实现并行抓取）；
        无待查页时返回 ``DECISION`` 节点名，直接进入决策。
    """
    pending = state["pending_pages"]
    if not pending:
        return DECISION
    return [
        Send(
            FETCH,
            {
                "page": page,
                "page_size": state["page_size"],
                "select_recipes": state["select_recipes"],
            },
        )
        for page in pending
    ]


def route_after_decision(state: RecipeAgentState) -> str:
    """路由：判断是否需要继续查询候选。

    Args:
        state: 当前工作流状态，读取 ``result_recipes`` / ``count`` / ``attempts``。

    Returns:
        已挑选数量达到 ``count`` 或轮次用尽时返回 ``END`` 结束工作流，
        否则返回 ``PLAN`` 节点名开启下一轮查询。
    """
    if len(state["result_recipes"]) >= state["count"]:
        return END
    if state["attempts"] >= MAX_ATTEMPTS:
        return END
    return PLAN
