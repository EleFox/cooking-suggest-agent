"""调用 cooking-web-service 菜谱接口的**请求参数**模型。

响应结构已统一到唯一来源 ``agent.schemas.recipes_agent``（``Recipe`` /
``RecipeSummary`` / ``RecipeListData`` / ``Element``），本模块不再重复定义
响应模型，避免同构两套。

对应 web-service 契约（见 ``design/sprints/S3/api.md`` 与
``design/project/integrations.md``）：

- 列表接口 ``GET /api/recipes``：分页参数 ``page`` / ``page_size``，
  以及去重参数 ``exclude_recipe_ids``（排除已展示/已选菜谱）；
- 详情接口 ``GET /api/recipes/detail``：``ids`` 由客户端拼成逗号串。

> 注意：列表与详情的 id 数组，web-service 均以**逗号拼接字符串**接收，
> 因此模型内保存 ``list[int]``，由客户端在发请求前拼接。
"""

from pydantic import BaseModel, Field


class RecipeListRequest(BaseModel):
    """列表接口请求参数（暂不含 keyword）。"""

    page: int = Field(1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(20, ge=1, le=100, description="每页条数，上限 100")
    exclude_recipe_ids: list[int] = Field(
        default_factory=list,
        description="需排除的菜谱 id 数组（去重；不存在的 id 忽略）",
    )


class RecipeDetailRequest(BaseModel):
    """详情接口请求参数；``ids`` 由客户端拼接为逗号串。"""

    ids: list[int] = Field(default_factory=list, description="菜谱 id 数组")
