"""LangGraph 工作流构建与编译。

以 :class:`RecipeAgentState` 为内部状态、:class:`OutputState` 为输出状态，组装
「规划 → 并行查询 → 决策 → 回环」的菜谱挑选工作流，并编译为可调用的
``cooking_suggest_agent``，供 ``agent.services.recipes`` 执行。
"""

from langgraph.graph import END, START, StateGraph

from agent.graph.nodes import (
    DECISION,
    FETCH,
    PLAN,
    decision_result_recipes,
    dispatch_recipe_fetch,
    fetch_recipes,
    plan_fetch_recipes,
    route_after_decision,
)
from agent.graph.state import OutputState, RecipeAgentState

graph = StateGraph(RecipeAgentState, output_schema=OutputState)

# Nodes
graph.add_node(PLAN, plan_fetch_recipes)
graph.add_node(FETCH, fetch_recipes)
graph.add_node(DECISION, decision_result_recipes)

# graph
graph.add_edge(START, PLAN)
graph.add_conditional_edges(PLAN, dispatch_recipe_fetch)
graph.add_edge(FETCH, DECISION)
graph.add_conditional_edges(
    DECISION,
    route_after_decision,
    {
        PLAN: PLAN,
        END: END,
    },
)

cooking_suggest_agent = graph.compile()
