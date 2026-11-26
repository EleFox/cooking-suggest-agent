"""菜谱接口的请求 / 响应 Pydantic 模型。

对应 S3 ``design/sprints/S3/api.md`` 的菜谱接口。列表与详情均以统一的
``elements`` 数组承载菜谱全部关联要素（``{id, type, name, sort_order}``），
由前端 / Agent 按 ``type`` 识别。
"""

from pydantic import BaseModel, Field

from app.schemas.element import ElementOperate, ElementRef


class RecipeCreate(BaseModel):
    """创建菜谱请求体。"""

    name: str = Field(..., description="菜名，必填")
    elements: list[ElementRef] = Field(
        default_factory=list, description="要素数组（{name, type}）"
    )
    detail: str | None = Field(None, description="做法文本，可空")


class RecipeUpdate(BaseModel):
    """更新菜谱请求体（要素为增量 operate 语义）。"""

    id: int = Field(..., description="目标菜谱 id")
    name: str = Field(..., description="菜名，非空")
    elements: list[ElementOperate] = Field(
        default_factory=list, description="要素增量操作数组"
    )
    detail: str | None = Field(None, description="做法文本；为空清除详情文件")


class RecipeDelete(BaseModel):
    """删除菜谱请求体。"""

    id: int = Field(..., description="目标菜谱 id")


class RecipeElementOut(BaseModel):
    """菜谱关联的单个要素。"""

    id: int
    type: str
    name: str
    sort_order: int


class RecipeSummaryOut(BaseModel):
    """菜谱摘要（列表 / 创建 / 更新 / 决策卡片返回）。"""

    id: int
    name: str
    elements: list[RecipeElementOut]
    has_detail: bool


class RecipeDetailOut(BaseModel):
    """菜谱详情（批量详情 / 编辑回显）。"""

    id: int
    name: str
    elements: list[RecipeElementOut]
    detail: str | None


class RecipeListData(BaseModel):
    """菜谱分页列表的 data 内层结构。"""

    list: list[RecipeSummaryOut]
    has_next: bool
    total: int
    page: int
    page_size: int
