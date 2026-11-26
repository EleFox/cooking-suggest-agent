"""料理偏好方案接口路由。

对应 ``design/sprints/S2/api.md`` 的方案接口（创建 / 列表 / 更新 / 删除）。
路由层仅处理请求/响应与错误信封转换，业务逻辑委托给服务层。
"""

from fastapi import APIRouter, Query

from app.core.logging import get_logger
from app.schemas.envelope import Envelope, error, ok
from app.schemas.preference_scheme import (
    PreferenceSchemeCreate,
    PreferenceSchemeDelete,
    PreferenceSchemeUpdate,
)
from app.services.errors import ApiError
from app.services.preference_scheme_service import (
    create_scheme,
    delete_scheme,
    get_default_scheme,
    list_schemes,
    update_scheme,
)

logger = get_logger(__name__)

router = APIRouter()

# 列表接口默认分页参数（遵循 api-conventions）。
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20


@router.post("/preference-schemes", response_model=Envelope)
def create_scheme_route(request: PreferenceSchemeCreate) -> Envelope:
    """创建料理偏好方案。"""
    logger.debug("create scheme request received: name=%s", request.name)
    try:
        return ok(data=create_scheme(request.name, request.element_ids))
    except ApiError as exc:
        logger.debug("create scheme failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)


@router.get("/preference-schemes", response_model=Envelope)
def list_schemes_route(
    page: int = Query(DEFAULT_PAGE, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, description="每页条数"),
) -> Envelope:
    """分页查询方案列表（每项含完整 element_ids）。"""
    logger.debug("list schemes request received: page=%s page_size=%s", page, page_size)
    return ok(data=list_schemes(page, page_size))


@router.get("/preference-schemes/default", response_model=Envelope)
def get_default_scheme_route() -> Envelope:
    """查询默认方案；无默认方案时 data 为 null。"""
    logger.debug("get default scheme request received")
    return ok(data=get_default_scheme())


@router.put("/preference-schemes", response_model=Envelope)
def update_scheme_route(request: PreferenceSchemeUpdate) -> Envelope:
    """更新方案名称 / 勾选项 / 默认标记。"""
    logger.debug("update scheme request received: id=%s", request.id)
    try:
        return ok(
            data=update_scheme(
                request.id, request.name, request.element_ids, request.is_default
            )
        )
    except ApiError as exc:
        logger.debug("update scheme failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)


@router.delete("/preference-schemes", response_model=Envelope)
def delete_scheme_route(request: PreferenceSchemeDelete) -> Envelope:
    """删除方案及其勾选关联。"""
    logger.debug("delete scheme request received: id=%s", request.id)
    try:
        delete_scheme(request.id)
    except ApiError as exc:
        logger.debug("delete scheme failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)
    return ok(data=None)
