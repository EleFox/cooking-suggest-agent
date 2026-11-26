"""应用日志基础设施。

提供一套统一、一致的日志获取与配置方式。仅使用 Python 标准库 ``logging``，
不引入第三方依赖。

用法：:

    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("message")
"""

import logging
import sys

from app.core.config import get_settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_LEVEL = logging.INFO


def _resolve_level(level: str | None) -> int:
    """把日志级别字符串解析为 logging 级别数值，空值回退到默认级别。"""
    return logging.getLevelName(level) if level else DEFAULT_LEVEL


def get_logger(name: str) -> logging.Logger:
    """返回使用应用标准格式配置好的 logger。

    Args:
        name: 通常传入 ``__name__``，用于日志中标识来源模块。
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(_resolve_level(get_settings().log_level))
        logger.propagate = False
    return logger


def setup_logging(level: int = DEFAULT_LEVEL) -> None:
    """配置整个应用使用的根 logger。

    应在应用启动时调用一次（例如在 main.py 中）。
    """
    logging.basicConfig(
        level=_resolve_level(get_settings().log_level) or level,
        format=LOG_FORMAT,
        stream=sys.stdout,
    )
