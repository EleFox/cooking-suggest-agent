"""要素相关 Pydantic 模型。

包含要素查询响应模型，以及成员 / 菜谱接口共用的「要素统一契约」：

- 创建：``{name, type}``；
- 更新：``{name, type, id, operate}`` 增量语义（见 S3 api.md）。
"""

from pydantic import BaseModel, Field


class ElementOut(BaseModel):
    """单个烹饪要素字典项。"""

    id: int
    type: str
    name: str
    sort_order: int


class ElementRef(BaseModel):
    """创建资源时的要素引用（按 ``(type, name)`` resolve-or-create）。"""

    name: str = Field(..., description="要素名；time 类型为正整数分钟数字符串")
    type: str = Field(..., description="要素类型")


class ElementOperate(BaseModel):
    """更新资源时的增量要素操作项。"""

    name: str = Field(..., description="要素名")
    type: str = Field(..., description="要素类型")
    id: int | None = Field(None, description="既有要素 id；新增项无此字段")
    operate: str = Field(..., description="操作：add / remove / edit")
