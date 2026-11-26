"""料理偏好方案接口的请求/响应 Pydantic 模型。

对应 S2 ``design/sprints/S2/api.md`` 的方案接口（创建 / 列表 / 更新 / 删除）。
"""

from pydantic import BaseModel, Field


class PreferenceSchemeCreate(BaseModel):
    """创建方案请求体。"""

    name: str = Field(..., description="方案名，非空，允许重名")
    element_ids: list[int] = Field(
        default_factory=list, description="偏好要素 id 数组，可为空"
    )


class PreferenceSchemeUpdate(BaseModel):
    """更新方案请求体。"""

    id: int = Field(..., description="目标方案 id")
    name: str = Field(..., description="更新后的方案名，非空")
    element_ids: list[int] = Field(
        default_factory=list, description="更新后的勾选要素 id 数组"
    )
    is_default: int = Field(0, ge=0, le=1, description="1=设为默认，0=取消默认")


class PreferenceSchemeDelete(BaseModel):
    """删除方案请求体。"""

    id: int = Field(..., description="目标方案 id")


class PreferenceSchemeOut(BaseModel):
    """方案对象（含完整 element_ids，无需单独详情接口）。"""

    id: int
    name: str
    is_default: int
    element_ids: list[int]
    created_at: str
    updated_at: str


class PreferenceSchemeListData(BaseModel):
    """方案列表的分页信封内层结构（遵循 api-conventions 分页约定）。"""

    list: list[PreferenceSchemeOut]
    has_next: bool
    total: int
    page: int
    page_size: int
