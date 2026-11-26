"""用于规定获取推荐菜谱的 agent 的模型。

本模块是要素 / 菜谱结构的**唯一来源**：既描述 web-service 决策接口透传给
Agent 的请求体（``GetRecipesParams``：``count`` + 富化 ``elements`` +
翻译后的 ``dedup`` 菜谱），也描述 Agent 反向调用菜谱接口得到的响应结构
（``RecipeSummary`` / ``RecipeListData`` / ``Recipe``），避免两套同构定义。

全部结构统一使用 Pydantic ``BaseModel``：既满足 API 边界的类型校验，也满足
``trustcall`` 等结构化抽取 / 更新工具对 JSON Schema 与字段描述的需求。
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# 要素与决策的关系类型：preference 偏好 / taboo 禁忌。
RelationType = Literal["preference", "taboo"]


class Element(BaseModel):
    """菜谱要素。"""

    id: int = Field(description="菜谱要素的id")
    type: str = Field(
        description="菜谱要素类型，主要取值有：ingredient / technique / time / taste / difficulty"
    )
    name: str = Field(description="要菜谱素名称（time 类型为纯数字分钟字符串）")
    sort_order: int = Field(description="要素排序值")


class DecisionElement(Element):
    """决策请求中的偏好/禁忌要素。

    在菜谱要素上补充 ``relation_type``，用于区分偏好与禁忌。
    """

    relation_type: RelationType = Field(
        description="关系的类型，主要取值有：preference / taboo"
    )


class Recipe(BaseModel):
    """菜谱（完整数据，含做法正文）。"""

    id: int = Field(description="菜谱对应的id")
    name: str = Field(description="菜谱名")
    elements: list[Element] = Field(
        default_factory=list, description="该菜谱关联的全部要素数组"
    )
    detail: str | None = Field(default=None, description="做法正文；无详情为 None")


class RecipeSummary(BaseModel):
    """菜谱摘要（列表接口输出项，不含做法正文）。"""

    id: int = Field(description="菜谱对应的id")
    name: str = Field(description="菜谱名")
    elements: list[Element] = Field(
        default_factory=list, description="该菜谱关联的全部要素数组"
    )
    has_detail: bool = Field(description="是否存在菜谱详情")


class RecipeListData(BaseModel):
    """菜谱分页列表结构（列表接口 ``data`` 内层）。"""

    list: Annotated[list[RecipeSummary], Field(description="当前页菜谱摘要数组")]
    has_next: bool = Field(description="是否还有下一页")
    total: int = Field(description="总条数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="当前每页条数")


class ResultRecipeList(BaseModel):
    """菜谱查询工具调用的结构限制，用于限制模型返回。"""

    list: Annotated[list[RecipeSummary], Field(description="菜谱摘要数组")]


class GetRecipesParams(BaseModel):
    """用于调用获取推荐菜谱时的参数模型。

    与 web-service 决策接口的下游透传格式一致；``elements`` / ``dedup``
    为空时 web-service 不传该字段，故均给默认空数组。
    """

    count: int = Field(description="需要获取的菜谱数量")
    elements: list[DecisionElement] = Field(
        default_factory=list, description="富化后的偏好/禁忌要素数组"
    )
    dedup: list[Recipe] = Field(
        default_factory=list, description="已展示菜谱翻译成的完整去重列表"
    )
