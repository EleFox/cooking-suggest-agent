"""健康检查接口响应模型。

健康检查为运维专用例外，不套业务信封（见
``design/agreement/api-conventions.md``）。
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查响应，仅返回精简的存活状态。"""

    status: str
