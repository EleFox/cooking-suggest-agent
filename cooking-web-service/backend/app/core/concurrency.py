"""请求链路的并发资源隔离。

决策链路会同步等待外部 Agent 服务（可能长达数百秒），而 Agent 又会在决策
过程中反向调用本服务的菜谱查询 / 详情 API（数据面）。若两者共享同一份稀缺
资源（事件循环或默认线程池），就会形成互相等待。

因此为决策链路提供**独立的、有界的线程池**：长耗时调用只占用专用池，
默认请求线程池始终为反向数据面等短请求保留容量。
"""

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def get_decision_executor() -> ThreadPoolExecutor:
    """返回决策链路的专用有界线程池（隔离于默认请求线程池）。"""
    settings = get_settings()
    return ThreadPoolExecutor(
        max_workers=settings.decision_max_workers,
        thread_name_prefix="decision",
    )


def shutdown_decision_executor() -> None:
    """关闭决策线程池（应用关停时调用，不等待在途任务）。"""
    get_decision_executor().shutdown(wait=False)
