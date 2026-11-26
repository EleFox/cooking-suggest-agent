"""Agent 工作流的状态定义。

本模块集中声明菜谱决策图（LangGraph）使用的状态结构：

- :class:`RecipeAgentState`：图的内部状态，贯穿规划、查询、决策节点；
- :class:`OutputState`：图对外输出的状态，仅保留最终推荐菜谱。

列表字段通过 ``Annotated`` 声明归约器（reducer）：在并行节点或跨轮次写入时由
归约器合并，而非直接覆盖。``MessagesState`` 已内置 ``messages`` 通道及其归约规则。
"""

import operator
from typing import Annotated

from langgraph.graph import MessagesState
from typing_extensions import TypedDict

from agent.schemas.recipes_agent import Element, Recipe, RecipeSummary


def clearable_add(
    left: list[RecipeSummary], right: list[RecipeSummary]
) -> list[RecipeSummary]:
    """可清空的列表归约器（reducer）。

    LangGraph 的列表归约默认只做追加，无法在轮次之间清空历史候选。本归约器约定：
    右侧写入空列表时视为「清空」信号，返回空列表；否则按常规追加合并。

    Args:
        left: 已累积的列表。
        right: 本次节点写入的列表；为空列表时表示清空。

    Returns:
        合并（或清空）后的列表。
    """
    if right == []:  # 收到空列表信号，执行清空
        return []
    return left + right


class RecipeAgentState(MessagesState):
    """菜谱决策工作流的内部状态。

    继承 ``MessagesState`` 以携带 ``messages`` 通道。字段分为三类：本次决策的
    输入约束（``count`` / 偏好 / 禁忌 / 已选菜谱）、节点间流转的中间数据
    （候选菜谱、待查页码）、以及跨轮次累积的查询控制信息（轮次、已拉取页码）。
    """

    count: int  # 本次需要获取的推荐菜谱数量
    preference_elements: list[Element]  # 偏好的料理要素
    taboo_elements: list[Element]  # 禁忌的料理要素（硬过滤）
    select_recipes: list[Recipe]  # 已选菜谱，参与去重与均衡，跨轮次不可改
    reference_recipes: Annotated[
        list[RecipeSummary], clearable_add
    ]  # 本轮候选菜谱；写入空列表表示清空
    result_recipes: Annotated[
        list[RecipeSummary], operator.add
    ]  # 各轮决策产出的推荐菜谱，追加累积
    pending_pages: list[int]  # 本轮待并行查询的页码，由规划节点写入

    page_size: int  # 本轮单页条数
    page: int  # 当前查询页码（由 Send 注入单页查询节点）
    total: int  # 排除已选菜谱后的候选总量
    attempts: int  # 已执行的查询轮次，用于限制回环重试
    fetched_pages: Annotated[list[int], operator.add]  # 已拉取的页码，追加累积


class OutputState(TypedDict):
    """工作流对外输出的状态。

    仅暴露最终推荐菜谱，屏蔽中间的查询与规划状态。
    """

    result_recipes: Annotated[list[RecipeSummary], operator.add]  # 最终推荐的菜谱摘要
