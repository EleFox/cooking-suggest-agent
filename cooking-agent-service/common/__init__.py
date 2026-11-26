"""跨服务共享的通用功能模块。

当前包含应用配置基类（``common.config``）与日志基础设施（``common.logging``），
供 ``cooking-web-service`` 与 ``cooking-agent-service`` 两个系统共同使用。
"""

from common.config import Settings, get_settings
from common.logging import get_logger, setup_logging

__all__ = ["Settings", "get_logger", "get_settings", "setup_logging"]
