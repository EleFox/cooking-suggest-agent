"""要素查询接口路由。

对应 ``design/sprints/S2/api.md`` 中的 ``GET /api/elements``。
路由层仅处理请求/响应，业务逻辑委托给服务层。
"""

from typing import Literal

from fastapi import APIRouter

from app.core.logging import get_logger
from app.schemas.envelope import Envelope, ok
from app.services.element_service import list_elements

logger = get_logger(__name__)

router = APIRouter()

# 本轮需要素类型：设置页勾选（technique / time）与菜谱表单难度单选（difficulty）。
# 新增类型时在此扩展即可，接口字段与返回结构不变。
ElementTypeParam = Literal["technique", "time", "difficulty"]


@router.get("/elements", response_model=Envelope)
def get_elements(type: ElementTypeParam) -> Envelope:
    """按要素类型返回字典列表（小字典，不分页，按 sort_order 升序）。

    Args:
        type: 要素类型（technique / time / difficulty）。

    Returns:
        统一信封包裹的要素字典数组。
    """
    logger.debug("elements request received: type=%s", type)
    return ok(data=list_elements(type))
