"""健康检查接口响应模型。"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查响应，不套业务信封。"""

    status: str
