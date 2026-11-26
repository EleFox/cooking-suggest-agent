"""成员接口路由。

对应 S3 ``design/sprints/S3/api.md`` 的成员接口（查询 / 创建 / 更新 / 删除）。
路由层仅处理请求 / 响应与错误信封转换，业务逻辑委托给服务层。
"""

from fastapi import APIRouter

from app.core.logging import get_logger
from app.schemas.envelope import Envelope, error, ok
from app.schemas.member import MemberCreate, MemberDelete, MemberUpdate
from app.services.errors import ApiError
from app.services.member_service import (
    create_member,
    delete_member,
    list_members,
    update_member,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/members", response_model=Envelope)
def list_members_route() -> Envelope:
    """查询成员列表（不分页，含完整偏好 / 禁忌要素）。"""
    logger.debug("list members request received")
    return ok(data=list_members())


@router.post("/members", response_model=Envelope)
def create_member_route(request: MemberCreate) -> Envelope:
    """创建成员（要素 resolve-or-create，单事务）。"""
    logger.debug("create member request received: name=%s", request.name)
    try:
        result = create_member(request.name, request.preferences, request.taboos)
    except ApiError as exc:
        logger.debug("create member failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)
    return ok(data=result)


@router.put("/members", response_model=Envelope)
def update_member_route(request: MemberUpdate) -> Envelope:
    """更新成员（姓名全量 + 要素增量 operate）。"""
    logger.debug("update member request received: id=%s", request.id)
    try:
        result = update_member(
            request.id, request.name, request.preferences, request.taboos
        )
    except ApiError as exc:
        logger.debug("update member failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)
    return ok(data=result)


@router.delete("/members", response_model=Envelope)
def delete_member_route(request: MemberDelete) -> Envelope:
    """删除成员及其关联行。"""
    logger.debug("delete member request received: id=%s", request.id)
    try:
        delete_member(request.id)
    except ApiError as exc:
        logger.debug("delete member failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)
    return ok(data=None)
