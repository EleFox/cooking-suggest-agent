"""获取菜谱服务层测试。"""

from unittest.mock import patch

import pytest

from agent.schemas.recipes_agent import GetRecipesParams
from app.services.recipes import get_recipes


def test_get_recipes_passes_count_to_agent():
    """正向路径：按接口层传入的数量构造 Agent 参数并调用。"""
    with patch(
        "app.services.recipes.invoke_get_recipes", return_value=[2, 3, 5]
    ) as mock_invoke:
        result = get_recipes(count=3)

    assert result == [2, 3, 5]
    mock_invoke.assert_called_once_with(GetRecipesParams(count=3))


def test_get_recipes_returns_agent_result_unmodified():
    """边界情况：服务层直接透传 Agent 结果，不做任何加工。"""
    agent_result = [1, 2, 3, 4, 5]
    with patch("app.services.recipes.invoke_get_recipes", return_value=agent_result):
        result = get_recipes(count=5)

    assert result == agent_result


def test_get_recipes_single_count_edge():
    """边界情况：数量为 1 时返回单元素数组。"""
    with patch("app.services.recipes.invoke_get_recipes", return_value=[7]):
        result = get_recipes(count=1)

    assert result == [7]


def test_get_recipes_empty_result_passthrough():
    """边界情况：Agent 无结果时透传空数组。"""
    with patch("app.services.recipes.invoke_get_recipes", return_value=[]):
        result = get_recipes(count=3)

    assert result == []


def test_get_recipes_agent_failure_raises():
    """异常路径：Agent 执行失败时向上抛出，交由接口层兜底。"""
    with (
        patch(
            "app.services.recipes.invoke_get_recipes",
            side_effect=RuntimeError("agent down"),
        ),
        pytest.raises(RuntimeError),
    ):
        get_recipes(count=3)


def test_get_recipes_forwards_elements_and_dedup_to_agent():
    """正向路径：要素与去重菜谱完整透传到 Agent 参数。"""
    elements = [
        {
            "id": 3,
            "type": "technique",
            "name": "炖",
            "sort_order": 1,
            "relation_type": "preference",
        }
    ]
    dedup = [
        {
            "id": 7,
            "name": "去重菜",
            "elements": [{"id": 3, "type": "technique", "name": "炖", "sort_order": 1}],
            "detail": "先切再炒",
        }
    ]
    with patch(
        "app.services.recipes.invoke_get_recipes", return_value=[2]
    ) as mock_invoke:
        result = get_recipes(count=1, elements=elements, dedup=dedup)

    assert result == [2]
    mock_invoke.assert_called_once_with(
        GetRecipesParams(count=1, elements=elements, dedup=dedup)
    )


def test_get_recipes_none_elements_and_dedup_become_empty():
    """边界情况：未传要素/去重时构造为空数组。"""
    with patch(
        "app.services.recipes.invoke_get_recipes", return_value=[]
    ) as mock_invoke:
        result = get_recipes(count=2)

    assert result == []
    mock_invoke.assert_called_once_with(GetRecipesParams(count=2))
