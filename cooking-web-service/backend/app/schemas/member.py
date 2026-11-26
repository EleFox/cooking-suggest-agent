"""成员接口的请求 / 响应 Pydantic 模型。

对应 S3 ``design/sprints/S3/api.md`` 的成员接口。
"""

from pydantic import BaseModel, Field

from app.schemas.element import ElementOperate, ElementRef


class MemberCreate(BaseModel):
    """创建成员请求体。"""

    name: str = Field(..., description="成员名，必填；允许重名")
    preferences: list[ElementRef] = Field(
        default_factory=list, description="偏好要素数组（{name, type}）"
    )
    taboos: list[ElementRef] = Field(
        default_factory=list, description="禁忌要素数组（{name, type}）"
    )


class MemberUpdate(BaseModel):
    """更新成员请求体（要素为增量 operate 语义）。"""

    id: int = Field(..., description="目标成员 id")
    name: str = Field(..., description="成员名，非空")
    preferences: list[ElementOperate] = Field(
        default_factory=list, description="偏好要素增量操作数组"
    )
    taboos: list[ElementOperate] = Field(
        default_factory=list, description="禁忌要素增量操作数组"
    )


class MemberDelete(BaseModel):
    """删除成员请求体。"""

    id: int = Field(..., description="目标成员 id")


class MemberElementOut(BaseModel):
    """成员关联的单个要素。"""

    id: int
    name: str
    type: str


class MemberOut(BaseModel):
    """成员对象（含偏好 / 禁忌要素明细）。"""

    id: int
    name: str
    preferences: list[MemberElementOut]
    taboos: list[MemberElementOut]
    created_at: str
    updated_at: str
