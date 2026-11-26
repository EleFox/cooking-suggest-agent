"""决策接口的请求 Pydantic 模型。

对应 ``design/sprints/S3/api.md`` 中 ``POST /api/decisions`` 的请求结构：
``elements`` 每项为 ``{type, element_id, relation_type}``，其中 ``relation_type``
取值与 ``t_member_element.relation_type`` 一致（``preference`` / ``taboo``）。
响应 ``data`` 直接为菜谱卡片数组（见 ``schemas/recipe.py`` 的
``RecipeSummaryOut``），不再嵌套。
"""

from typing import Literal

from pydantic import BaseModel, Field

ElementType = str

# 决策要素关系类型：偏好 / 禁忌。
RelationType = Literal["preference", "taboo"]


class DecisionElement(BaseModel):
    """单个要素偏好项。"""

    type: str = Field(
        ...,
        description="要素类型：ingredient / technique / time / allergen / taste / difficulty",
    )
    element_id: int = Field(..., description="指向 t_element.id 的具体偏好要素")
    relation_type: RelationType = Field(
        ..., description="关系类型：preference 偏好 / taboo 禁忌"
    )


class DecisionRequest(BaseModel):
    """决策请求体。"""

    count: int = Field(1, ge=1, description="本次生成数量")
    dedup_ids: list[int] = Field(
        default_factory=list, description="已展示的菜谱 id（去重列表）"
    )
    elements: list[DecisionElement] = Field(
        default_factory=list,
        description="要素偏好数组（{type, element_id, relation_type}）",
    )
