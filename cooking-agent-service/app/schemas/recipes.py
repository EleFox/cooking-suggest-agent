"""获取菜谱接口的请求模型。

请求参数遵循 ``design/agreement/api-conventions.md`` 的字段命名与
校验约定（snake_case、参数校验失败统一 422）；响应使用统一信封
``app.schemas.envelope.Envelope``。

请求体结构与 ``cooking-web-service`` 决策接口透传给 Agent 的格式一致
（见 ``design/sprints/S3/api.md``）：``count`` + 富化 ``elements`` +
翻译后的 ``dedup`` 菜谱；后两者为空时可不传。
"""

from pydantic import BaseModel, Field

from agent.schemas.recipes_agent import DecisionElement, Recipe


class GetRecipesRequest(BaseModel):
    """获取菜谱请求模型。

    Args:
        count: 需要获取的菜谱数量，最小为 1。
        elements: 富化后的偏好/禁忌要素数组（relation_type 区分偏好与禁忌）。
        dedup: 已展示菜谱翻译成的完整去重列表（含做法正文）。
    """

    count: int = Field(ge=1, description="需要获取的菜谱数量")
    elements: list[DecisionElement] = Field(
        default_factory=list, description="富化后的偏好/禁忌要素数组"
    )
    dedup: list[Recipe] = Field(
        default_factory=list, description="已展示菜谱翻译成的完整去重列表"
    )
