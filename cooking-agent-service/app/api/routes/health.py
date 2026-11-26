"""健康检查接口路由。

健康检查用于服务存活探测，不套业务信封（见
``design/agreement/api-conventions.md``）。
"""

from fastapi import APIRouter

from app.schemas.health import HealthResponse
from common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """返回服务存活状态。"""
    logger.debug("health endpoint hit")
    return HealthResponse(status="ok")
