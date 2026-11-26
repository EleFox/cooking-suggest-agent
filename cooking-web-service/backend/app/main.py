"""应用入口。

负责应用创建、路由注册与生命周期管理（启动时初始化数据库与种子数据）。
不包含业务逻辑。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import (
    decisions,
    elements,
    health,
    members,
    preference_schemes,
    recipes,
)
from app.core.concurrency import shutdown_decision_executor
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import get_logger, setup_logging
from app.core.seed import seed
from app.core.storage import backup_orphan_recipes_dir

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时配置日志、初始化数据库与种子，关闭时记录日志。"""
    setup_logging()
    # 数据库缺失但菜谱目录存在时先备份旧目录，避免新旧数据混用。
    backup_orphan_recipes_dir(settings.database_path, settings.recipes_dir)
    init_db()
    seed()
    logger.info("%s starting up", settings.app_name)
    yield
    shutdown_decision_executor()
    logger.info("%s shutting down", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(health.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(elements.router, prefix="/api")
app.include_router(preference_schemes.router, prefix="/api")
app.include_router(members.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    """把 FastAPI/Pydantic 校验失败统一包装为业务信封（HTTP 422）。"""
    return JSONResponse(
        status_code=422,
        content={"code": 422, "data": None, "message": "请求参数校验失败"},
    )


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """把 HTTP 异常（404 / 405 等）包装为业务信封，保持 code 与状态码一致。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "data": None, "message": str(exc.detail)},
    )


@app.get("/")
async def root() -> dict[str, str]:
    """返回服务基本信息。"""
    return {
        "service": "cooking-web-service",
        "message": "Hello from Cooking Web Service",
    }
