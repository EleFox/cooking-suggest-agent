"""Agent 菜谱相关工具。

定义可被 LLM 绑定的菜谱查询工具，以及用于约束模型输出结构的返回模型列表。
"""

from langchain.tools import tool

from agent.schemas.recipes_agent import RecipeSummary, ResultRecipeList
from app.services.recipe_client import fetch_recipe_summaries


@tool
def get_reference_recipes(page: int, page_size: int) -> list[RecipeSummary]:
    """按分页获取参考菜谱摘要数组。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页条数。

    Returns:
        当前页的菜谱摘要数组。

    Raises:
        RecipeServiceError: 调用 web-service 失败或返回非成功信封。
    """
    result = fetch_recipe_summaries(page, page_size)
    return result.list


recipes_tools = [get_reference_recipes, ResultRecipeList]
