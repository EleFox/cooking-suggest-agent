"""调用 cooking-web-service 菜谱接口的 HTTP 客户端。

Agent 决策过程中的两个反向依赖（见 ``design/project/integrations.md``）：

- ``GET /api/recipes``：按分页 + 去重参数（``exclude_recipe_ids``）拉取菜谱摘要，
  供 Agent 筛选候选；
- ``GET /api/recipes/detail``：按 id 批量拉取菜谱详情（含做法正文）。

调用方向为 Agent → web-service。统一信封解析与错误兜底集中在本模块，
失败时抛 :class:`RecipeServiceError`，由上层决定降级或终止。
"""

from typing import Any

import httpx

from agent.schemas.recipes_agent import Recipe, RecipeListData
from app.schemas.recipe_client import RecipeDetailRequest, RecipeListRequest
from common.config import get_settings
from common.logging import get_logger

logger = get_logger(__name__)

# 统一信封成功码（见 design/agreement/api-conventions.md）。
SUCCESS_CODE = 200

# 文档定义的状态码与兜底文案，web-service 未给出 message 时使用。
ERROR_CODE_MESSAGES = {
    400: "请求格式错误",
    404: "资源不存在",
    409: "资源冲突",
    422: "请求校验失败",
    500: "服务器内部错误",
    502: "上游服务不可用",
    504: "上游服务超时",
}


class RecipeServiceError(Exception):
    """调用 web-service 菜谱接口失败（网络错误、超时或返回非成功信封）。"""


def _get_json(url: str, params: dict) -> Any:
    """发起 GET 请求并返回统一信封中的 ``data``。

    Args:
        url: web-service 菜谱接口完整地址。
        params: 查询参数。

    Returns:
        信封中的 ``data``（结构随接口而异）。

    Raises:
        RecipeServiceError: 网络 / 超时错误，或信封 ``code`` 非 200。
    """
    settings = get_settings()
    try:
        logger.info("web-service request: GET %s params=%s", url, params)
        with httpx.Client(timeout=settings.api_timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("web-service request failed: url=%s error=%s", url, exc)
        raise RecipeServiceError(str(exc)) from exc

    body = response.json()
    code = body.get("code")
    if code != SUCCESS_CODE:
        message = body.get("message") or ERROR_CODE_MESSAGES.get(
            code, f"未知错误 code={code}"
        )
        logger.error(
            "web-service returned non-200 envelope: url=%s code=%s message=%s",
            url,
            code,
            message,
        )
        raise RecipeServiceError(message)
    return body.get("data")


def fetch_recipe_summaries(
    page: int = 1,
    page_size: int = 1,
    exclude_recipe_ids: list[int] | None = None,
) -> RecipeListData:
    """分页查询菜谱摘要列表。

    Args:
        page: 页码，从 1 开始。
        page_size: 每页条数，上限 100。
        exclude_recipe_ids: 需从结果中排除的菜谱 id 数组（去重；不存在的 id
            忽略）。web-service 以逗号拼接字符串接收，本函数负责拼接；为空则
            不传该参数。

    Returns:
        分页列表结构（含 ``list`` / ``has_next`` / ``total`` 等）。

    Raises:
        RecipeServiceError: 调用失败或返回非成功信封。
    """
    request = RecipeListRequest(
        page=page,
        page_size=page_size,
        exclude_recipe_ids=exclude_recipe_ids or [],
    )
    params: dict = {"page": request.page, "page_size": request.page_size}
    # web-service 以逗号串接收排除 id；为空时不传该参数。
    if exclude_recipe_ids:
        params["exclude_recipe_ids"] = ",".join(
            str(recipe_id) for recipe_id in exclude_recipe_ids
        )
    data = _get_json(get_settings().api_recipes_query, params)
    return RecipeListData.model_validate(data)


def fetch_recipe_details(recipe_ids: list[int]) -> list[Recipe]:
    """按 id 批量查询菜谱详情，自动拼接为逗号串。

    Args:
        recipe_ids: 菜谱 id 数组；为空时直接返回空数组、不发起请求。

    Returns:
        菜谱详情数组（不存在的 id 由 web-service 忽略）。

    Raises:
        RecipeServiceError: 调用失败或返回非成功信封。
    """
    request = RecipeDetailRequest(ids=recipe_ids)
    if not request.ids:
        return []
    params = {"ids": ",".join(str(recipe_id) for recipe_id in request.ids)}
    data = _get_json(get_settings().api_recipe_detail_query, params)
    return [Recipe.model_validate(item) for item in data or []]
