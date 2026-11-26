"""获取菜谱接口路由。

接收请求参数并调用服务层执行 Agent，返回统一信封包裹的菜谱 id 数组。
仅做请求/响应处理，不包含业务逻辑。
"""

from fastapi import APIRouter

from app.schemas.envelope import Envelope, ok
from app.schemas.recipes import GetRecipesRequest
from app.services import recipes as recipe_service
from common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/recipes", response_model=Envelope[list[int]])
def get_recipes(request: GetRecipesRequest) -> Envelope[list[int]]:
    """触发 Agent 获取菜谱 id 数组。

    Args:
        request: 获取菜谱请求参数（数量、偏好/禁忌要素、去重菜谱）。

    Returns:
        统一信封，``data`` 为菜谱 id 数组。
    """
    logger.debug(
        "get recipes endpoint hit: count=%d, elements=%d, dedup=%d",
        request.count,
        len(request.elements),
        len(request.dedup),
    )
    ids = recipe_service.get_recipes(request.count, request.elements, request.dedup)
    return ok(ids)
