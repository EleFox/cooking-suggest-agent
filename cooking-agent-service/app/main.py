"""应用入口。

负责应用创建、路由注册、生命周期管理与 uvicorn 程序化启动（启动参数读取配置）。
不包含业务逻辑。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.routes import health, recipes
from common.config import get_settings
from common.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时配置日志，关闭时记录日志。"""
    setup_logging()
    logger.info("%s starting up", settings.app_name)
    yield
    logger.info("%s shutting down", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# 只注册契约定义的接口（当前为 /api/health、/api/recipes），不新增文档未定义的路由。
app.include_router(health.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")


def run() -> None:
    """程序化启动 uvicorn 服务器，启动参数从配置读取。"""
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_reload,
    )


if __name__ == "__main__":
    run()
