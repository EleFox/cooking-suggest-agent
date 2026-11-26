"""菜谱接口路由。

对应 S3 ``design/sprints/S3/api.md`` 的菜谱接口（列表 / 详情 / 创建 / 更新 /
删除）。路由层仅处理请求 / 响应与错误信封转换，业务逻辑委托给服务层。
"""

from fastapi import APIRouter, Query

from app.core.logging import get_logger
from app.schemas.envelope import Envelope, error, ok
from app.schemas.recipe import RecipeCreate, RecipeDelete, RecipeUpdate
from app.services.errors import ApiError
from app.services.recipe_service import (
    create_recipe,
    delete_recipe,
    get_recipe_details,
    list_recipes,
    update_recipe,
)

logger = get_logger(__name__)

router = APIRouter()

# 列表接口默认分页参数（遵循 api-conventions）。
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20


def _parse_ids(raw: str) -> list[int] | None:
    """解析逗号拼接的菜谱 id 串；空串或含非整数返回 None（由调用方回 422）。"""
    if not raw.strip():
        return None
    parts = [part.strip() for part in raw.split(",")]
    if any(not part for part in parts):
        return None
    try:
        return [int(part) for part in parts]
    except ValueError:
        return None


def _parse_optional_ids(raw: str | None) -> list[int] | None:
    """解析可选的逗号拼接 id 串。

    ``None`` / 空串视为不过滤（返回空列表）；含非整数返回 ``None``（由调用方
    回 422）。
    """
    if raw is None or not raw.strip():
        return []
    parts = [part.strip() for part in raw.split(",")]
    if any(not part for part in parts):
        return None
    try:
        return [int(part) for part in parts]
    except ValueError:
        return None


@router.get("/recipes", response_model=Envelope)
def list_recipes_route(
    keyword: str | None = Query(None, description="菜名模糊匹配关键字"),
    exclude_recipe_ids: str | None = Query(
        None, description="逗号拼接的菜谱 id，返回结果中排除（去重）"
    ),
    page: int = Query(DEFAULT_PAGE, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, description="每页条数"),
) -> Envelope:
    """分页查询菜谱摘要列表（同时作为 Agent 反向调用的菜谱查询 API）。"""
    logger.debug(
        "list recipes request received: keyword=%s exclude=%s page=%s page_size=%s",
        keyword,
        exclude_recipe_ids,
        page,
        page_size,
    )
    exclude_ids = _parse_optional_ids(exclude_recipe_ids)
    if exclude_ids is None:
        return error(code=422, message="exclude_recipe_ids 参数非法")
    return ok(data=list_recipes(keyword, page, page_size, exclude_ids))


@router.get("/recipes/detail", response_model=Envelope)
def get_recipe_detail_route(
    ids: str = Query(..., description="逗号拼接的菜谱 id，如 1,2,3"),
) -> Envelope:
    """批量查询菜谱详情（编辑回显 + Agent 详情 API）。

    不存在的 id 忽略；``ids`` 空串或含非整数返回 422。
    """
    logger.debug("get recipe details request received: ids=%s", ids)
    recipe_ids = _parse_ids(ids)
    if recipe_ids is None:
        return error(code=422, message="ids 参数非法")
    return ok(data=get_recipe_details(recipe_ids))


@router.post("/recipes", response_model=Envelope)
def create_recipe_route(request: RecipeCreate) -> Envelope:
    """创建菜谱（要素 resolve-or-create，做法非空时生成 MD 文件）。"""
    logger.debug("create recipe request received: name=%s", request.name)
    try:
        result = create_recipe(request.name, request.elements, request.detail)
    except ApiError as exc:
        logger.debug("create recipe failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)
    return ok(data=result)


@router.put("/recipes", response_model=Envelope)
def update_recipe_route(request: RecipeUpdate) -> Envelope:
    """更新菜谱（姓名 / 做法全量 + 要素增量，做法联动 MD 文件）。"""
    logger.debug("update recipe request received: id=%s", request.id)
    try:
        result = update_recipe(
            request.id, request.name, request.elements, request.detail
        )
    except ApiError as exc:
        logger.debug("update recipe failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)
    return ok(data=result)


@router.delete("/recipes", response_model=Envelope)
def delete_recipe_route(request: RecipeDelete) -> Envelope:
    """物理删除菜谱及其关联行与 MD 文件。"""
    logger.debug("delete recipe request received: id=%s", request.id)
    try:
        delete_recipe(request.id)
    except ApiError as exc:
        logger.debug("delete recipe failed: code=%s message=%s", exc.code, exc.message)
        return error(code=exc.code, message=exc.message)
    return ok(data=None)
