"""决策业务逻辑。

决策接口接收请求后，先校验并富化偏好要素（补全 ``name`` / ``sort_order``），
再把去重列表翻译为完整菜谱，随后把这些上下文透传给 Agent 服务获取候选菜谱
id 数组，最后按这些 id 从本地菜谱池组装卡片返回。契约遵循
``design/sprints/S3/api.md``（响应 ``data`` 直接为卡片数组）。
"""

from app.core.database import connection
from app.core.logging import get_logger
from app.schemas.decision import DecisionRequest
from app.services.agent_client import get_recipe_ids
from app.services.errors import ElementValidationError
from app.services.recipe_repository import find_recipe_summaries
from app.services.recipe_service import get_recipe_details

logger = get_logger(__name__)

# 无候选菜谱时的业务提示文案。
NO_RESULT_MESSAGE = "没有合适的菜了"


def _enrich_elements(elements) -> list[dict]:
    """校验并补全偏好要素信息，任一不满足抛出 422。

    按 ``element_id`` 查回要素的 ``id`` / ``type`` / ``name`` / ``sort_order``，
    并与请求声明的 ``type`` 比对；保留请求的 ``relation_type``。

    Args:
        elements: 决策请求中的偏好要素列表。

    Returns:
        富化后的要素字典列表（``{id, type, name, sort_order, relation_type}``）。

    Raises:
        ElementValidationError: 要素不存在或类型不符。
    """
    if not elements:
        return []

    enriched = []
    with connection() as conn:
        for element in elements:
            row = conn.execute(
                "SELECT id, type, name, sort_order FROM t_element WHERE id = ?",
                (element.element_id,),
            ).fetchone()
            if row is None:
                raise ElementValidationError(f"要素不存在: {element.element_id}")
            if row["type"] != element.type:
                raise ElementValidationError(
                    f"要素类型不符: id={element.element_id} type={element.type}"
                )
            enriched.append(
                {
                    "id": row["id"],
                    "type": row["type"],
                    "name": row["name"],
                    "sort_order": row["sort_order"],
                    "relation_type": element.relation_type,
                }
            )
    return enriched


def decide(request: DecisionRequest) -> list[dict]:
    """生成至多 ``request.count`` 张菜谱卡片。

    富化要素 + 翻译去重列表后透传给 Agent 获取候选菜谱 id，再据此组装卡片。

    Args:
        request: 决策请求，含生成数量、去重列表与偏好要素。

    Returns:
        决策结果卡片列表；无候选时返回空列表。

    Raises:
        AgentServiceError: Agent 服务不可用或超时时抛出，由路由层兜底。
        ElementValidationError: 偏好要素不存在或类型不符。
    """
    elements_payload = _enrich_elements(request.elements)
    dedup_payload = get_recipe_details(request.dedup_ids)
    logger.info(
        "decision request: count=%s elements=%d dedup=%d",
        request.count,
        len(elements_payload),
        len(dedup_payload),
    )
    recipe_ids = get_recipe_ids(request.count, elements_payload, dedup_payload)
    cards = find_recipe_summaries(recipe_ids)

    if not cards:
        logger.info("decision returned no results (count=%s)", request.count)
    else:
        logger.info("decision returned %d card(s)", len(cards))
    return cards
