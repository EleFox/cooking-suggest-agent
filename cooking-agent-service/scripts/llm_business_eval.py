"""LLM 业务能力评估脚本（手动执行，不参与回归 / 常规提交测试）。

本脚本用于评估 Agent 中 LLM 在真实决策链路上的业务能力：从
``agent.services.recipes.invoke_get_recipes``（内部调用
``cooking_suggest_agent.invoke``）到返回推荐菜谱 id 数组。测试数据全部为按需求
与设计文档构造的**模拟菜谱**，通过替换 ``app.services.recipe_client`` 的 HTTP
取值函数提供，无需真实启动 web-service。

覆盖场景：

1. 禁忌过滤：别称（马铃薯↔土豆）、大类（鱼类 / 水产）、小类（鲫鱼）；
2. 偏好选取率：偏好食材（含别称、大类识别）的菜谱是否比无偏好菜谱更易被选中；
3. 菜谱过少：请求数量大于池中数量时不得编造；
4. 单轮扇出不足：首轮扇出无合适菜谱，需回环到下一轮才能取到；
5. 无符合条件：全部候选均命中禁忌时返回空数组。

.. warning::
   本脚本依赖真实大模型（由 ``LLM_PROVIDER`` 选择 ``custom`` / ``ollama`` /
   ``deepseek`` 供应方并读取对应配置）且结果具有随机性；**不属于回归测试与常规
   提交测试**。``pytest`` 默认只收集 ``tests/``，不会执行本脚本。仅在需要评估
   LLM 业务能力时手动运行。

用法::

    cd cooking-agent-service
    # 运行全部场景
    python -m scripts.llm_business_eval
    # 仅运行偏好选取率场景，跑 20 轮
    python -m scripts.llm_business_eval --scenario preference --runs 20
    # 降低 agent 日志噪音
    LOG_LEVEL=WARNING python -m scripts.llm_business_eval
"""

import argparse
import statistics
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from agent.graph.nodes import MAX_ATTEMPTS
from agent.schemas.recipes_agent import GetRecipesParams
from agent.services.recipes import invoke_get_recipes
from app.services import recipe_client
from common.config import get_settings
from common.logging import get_logger, setup_logging

logger = get_logger("scripts.llm_business_eval")


class ElementRegistry:
    """要素登记表，模拟 web-service 的 ``resolve-or-create``（同 type+name 复用同一 id）。"""

    def __init__(self) -> None:
        self._ids: dict[tuple[str, str], int] = {}
        self._next_id = 1

    def id_for(self, element_type: str, name: str) -> int:
        """按 (type, name) 获取或新建要素 id。"""
        key = (element_type, name)
        if key not in self._ids:
            self._ids[key] = self._next_id
            self._next_id += 1
        return self._ids[key]

    def recipe_element(self, element_type: str, name: str, sort_order: int) -> dict:
        """构造菜谱内嵌要素（不含 relation_type）。"""
        return {
            "id": self.id_for(element_type, name),
            "type": element_type,
            "name": name,
            "sort_order": sort_order,
        }

    def decision_element(
        self, element_type: str, name: str, relation_type: str
    ) -> dict:
        """构造决策要素（含 relation_type，供调用接口使用）。"""
        return {
            "id": self.id_for(element_type, name),
            "type": element_type,
            "name": name,
            "sort_order": 1,
            "relation_type": relation_type,
        }


def make_recipe(
    recipe_id: int,
    name: str,
    registry: ElementRegistry,
    *,
    ingredients: tuple[str, ...] | list[str] = (),
    techniques: tuple[str, ...] | list[str] = (),
    minutes: int | None = None,
    difficulty: str | None = None,
    has_detail: bool = True,
) -> dict:
    """构造一条模拟菜谱摘要（列表接口返回项的结构）。

    Args:
        recipe_id: 菜谱 id。
        name: 菜名。
        registry: 要素登记表，用于分配稳定的要素 id。
        ingredients: 食材名称列表。
        techniques: 料理手段名称列表。
        minutes: 料理时间（分钟），为 None 时不生成 time 要素。
        difficulty: 料理难度，为 None 时不生成 difficulty 要素。
        has_detail: 是否存在做法详情。

    Returns:
        符合 web-service 列表契约的菜谱摘要字典。
    """
    elements: list[dict] = []
    order = 1
    for ingredient in ingredients:
        elements.append(registry.recipe_element("ingredient", ingredient, order))
        order += 1
    for technique in techniques:
        elements.append(registry.recipe_element("technique", technique, order))
        order += 1
    if minutes is not None:
        elements.append(registry.recipe_element("time", str(minutes), order))
        order += 1
    if difficulty:
        elements.append(registry.recipe_element("difficulty", difficulty, order))
        order += 1
    return {
        "id": recipe_id,
        "name": name,
        "elements": elements,
        "has_detail": has_detail,
    }


class FakeRecipeService:
    """内存版 web-service 菜谱接口，按分页 / 排除 id 返回模拟菜谱摘要。

    Args:
        recipes: 默认菜谱池（每项含 ``id`` / ``name`` / ``elements`` / ``has_detail``）。
        page_source: 可选回调，入参为「已处理的整页请求序号」，返回该次查询使用的
            菜谱池；用于模拟不同轮次返回不同数据（默认为 ``recipes``）。
    """

    def __init__(
        self,
        recipes: list[dict] | None = None,
        page_source: Callable[[int], list[dict]] | None = None,
    ) -> None:
        self.recipes = list(recipes or [])
        self.page_source = page_source
        self.requests: list[dict] = []
        self.page_fetch_count = 0

    @staticmethod
    def _parse_id_list(raw: str | None) -> set[int]:
        """解析逗号拼接的 id 串为整型集合；空值返回空集合。"""
        if not raw:
            return set()
        return {int(part) for part in str(raw).split(",") if part.strip()}

    @staticmethod
    def _list_payload(
        page: int, page_size: int, pool: list[dict], exclude: set[int]
    ) -> dict:
        """按分页 + 排除 id 构造列表接口 ``data`` 内层结构。"""
        items = [item for item in pool if item["id"] not in exclude]
        total = len(items)
        start = (page - 1) * page_size
        page_items = items[start : start + page_size]
        return {
            "list": page_items,
            "has_next": start + page_size < total,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def list_data(self, params: dict) -> dict:
        """按 ``fetch_recipe_summaries`` 的查询参数返回列表 ``data`` 内层结构。"""
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))
        self.requests.append({"page": page, "page_size": page_size})
        pool = self.recipes
        if page_size > 1:
            index = self.page_fetch_count
            self.page_fetch_count += 1
            if self.page_source is not None:
                pool = self.page_source(index)
        exclude = self._parse_id_list(params.get("exclude_recipe_ids"))
        return self._list_payload(page, page_size, pool, exclude)


@contextmanager
def fake_web_service(service: FakeRecipeService) -> Iterator[FakeRecipeService]:
    """临时替换菜谱客户端的 HTTP 取值函数。

    只替换 ``app.services.recipe_client._get_json``，不改动全局 ``httpx``——
    否则会破坏 OpenAI SDK 内部对 httpx 的使用。
    """

    def fake_get_json(url: str, params: dict):
        # 详情接口本次评估不使用，直接返回空数组；列表接口走模拟分页。
        if url.endswith("/detail"):
            return []
        return service.list_data(params)

    original = recipe_client._get_json
    recipe_client._get_json = fake_get_json
    try:
        yield service
    finally:
        recipe_client._get_json = original


def invoke_agent(
    service: FakeRecipeService, count: int, elements: list[dict] | None = None
) -> list[int]:
    """在模拟 web-service 下执行 Agent，返回推荐菜谱 id 数组。"""
    with fake_web_service(service):
        return invoke_get_recipes(
            GetRecipesParams(count=count, elements=elements or [])
        )


def _page_requests(service: FakeRecipeService) -> list[dict]:
    """筛选出摘要列表的「整页」请求（page_size > 1），用于统计扇出轮次。"""
    return [item for item in service.requests if item["page_size"] > 1]


def _taboo_dataset() -> tuple[ElementRegistry, list[dict]]:
    """禁忌过滤场景的数据集：覆盖别称 / 大类 / 小类食材。"""
    registry = ElementRegistry()
    recipes = [
        make_recipe(
            1,
            "土豆炖牛肉",
            registry,
            ingredients=["土豆", "牛肉"],
            techniques=["炖"],
            minutes=60,
            difficulty="一般",
        ),
        make_recipe(
            2,
            "马铃薯烧鸡",
            registry,
            ingredients=["马铃薯", "鸡肉"],
            techniques=["烧"],
            minutes=45,
            difficulty="一般",
        ),
        make_recipe(
            3,
            "清蒸鲫鱼",
            registry,
            ingredients=["鲫鱼"],
            techniques=["蒸"],
            minutes=25,
            difficulty="简单",
        ),
        make_recipe(
            4,
            "红烧带鱼",
            registry,
            ingredients=["带鱼"],
            techniques=["烧"],
            minutes=30,
            difficulty="一般",
        ),
        make_recipe(
            5,
            "白灼虾",
            registry,
            ingredients=["虾"],
            techniques=["灼"],
            minutes=15,
            difficulty="简单",
        ),
        make_recipe(
            6,
            "西红柿炒蛋",
            registry,
            ingredients=["西红柿", "鸡蛋"],
            techniques=["炒"],
            minutes=10,
            difficulty="简单",
        ),
        make_recipe(
            7,
            "番茄牛腩煲",
            registry,
            ingredients=["番茄", "牛腩"],
            techniques=["炖"],
            minutes=90,
            difficulty="一般",
        ),
        make_recipe(
            8,
            "清炒青菜",
            registry,
            ingredients=["青菜"],
            techniques=["炒"],
            minutes=8,
            difficulty="简单",
        ),
    ]
    return registry, recipes


def _preference_dataset() -> tuple[ElementRegistry, list[dict]]:
    """偏好选取率场景的数据集：4 道偏好命中（含别称 / 大类）+ 6 道无关菜谱。"""
    registry = ElementRegistry()
    recipes = [
        make_recipe(
            101,
            "醋溜土豆丝",
            registry,
            ingredients=["土豆"],
            techniques=["炒"],
            minutes=12,
            difficulty="简单",
        ),
        make_recipe(
            102,
            "马铃薯炖排骨",
            registry,
            ingredients=["马铃薯", "排骨"],
            techniques=["炖"],
            minutes=70,
            difficulty="一般",
        ),
        make_recipe(
            103,
            "清蒸鲫鱼",
            registry,
            ingredients=["鲫鱼"],
            techniques=["蒸"],
            minutes=25,
            difficulty="简单",
        ),
        make_recipe(
            104,
            "红烧带鱼",
            registry,
            ingredients=["带鱼"],
            techniques=["烧"],
            minutes=30,
            difficulty="一般",
        ),
        make_recipe(
            105,
            "西红柿炒蛋",
            registry,
            ingredients=["西红柿", "鸡蛋"],
            techniques=["炒"],
            minutes=10,
            difficulty="简单",
        ),
        make_recipe(
            106,
            "青菜豆腐汤",
            registry,
            ingredients=["青菜", "豆腐"],
            techniques=["煮"],
            minutes=15,
            difficulty="简单",
        ),
        make_recipe(
            107,
            "香煎鸡排",
            registry,
            ingredients=["鸡肉"],
            techniques=["煎"],
            minutes=20,
            difficulty="简单",
        ),
        make_recipe(
            108,
            "黑椒牛柳",
            registry,
            ingredients=["牛肉"],
            techniques=["炒"],
            minutes=18,
            difficulty="一般",
        ),
        make_recipe(
            109,
            "蒜蓉菠菜",
            registry,
            ingredients=["菠菜"],
            techniques=["炒"],
            minutes=8,
            difficulty="简单",
        ),
        make_recipe(
            110,
            "麻婆豆腐",
            registry,
            ingredients=["豆腐"],
            techniques=["烧"],
            minutes=20,
            difficulty="一般",
        ),
    ]
    return registry, recipes


def _tiny_dataset() -> tuple[ElementRegistry, list[dict]]:
    """菜谱过少场景的数据集：池中仅 2 道可行菜谱。"""
    registry = ElementRegistry()
    recipes = [
        make_recipe(
            1,
            "清炒时蔬",
            registry,
            ingredients=["青菜"],
            techniques=["炒"],
            minutes=8,
            difficulty="简单",
        ),
        make_recipe(
            2,
            "番茄鸡蛋面",
            registry,
            ingredients=["番茄", "鸡蛋"],
            techniques=["煮"],
            minutes=15,
            difficulty="简单",
        ),
    ]
    return registry, recipes


def _fruitless_recipes() -> list[dict]:
    """重试场景首轮数据：21 道菜全部含禁忌「香菜」，分页后每页 3 条。"""
    registry = ElementRegistry()
    return [
        make_recipe(
            1 + index,
            f"首轮禁忌菜{index + 1}",
            registry,
            ingredients=["香菜", "牛肉"],
            techniques=["炒"],
            minutes=10,
            difficulty="简单",
        )
        for index in range(21)
    ]


def _suitable_recipes() -> list[dict]:
    """重试场景次轮数据：21 道无禁忌菜谱，覆盖面足够触发多轮扇出。"""
    registry = ElementRegistry()
    ingredients = [
        "牛肉",
        "鸡肉",
        "猪肉",
        "鸡蛋",
        "青菜",
        "豆腐",
        "虾",
        "排骨",
        "鲈鱼",
        "菠菜",
        "土豆",
        "番茄",
        "茄子",
        "黄瓜",
        "萝卜",
        "芹菜",
        "香菇",
        "海带",
        "玉米",
        "南瓜",
        "山药",
    ]
    return [
        make_recipe(
            1001 + index,
            f"次轮可选菜{index + 1}",
            registry,
            ingredients=[ingredient],
            techniques=["炒"],
            minutes=10,
            difficulty="简单",
        )
        for index, ingredient in enumerate(ingredients)
    ]


def _all_taboo_dataset() -> tuple[ElementRegistry, list[dict]]:
    """无符合条件场景的数据集：8 道菜全部含禁忌「香菜」。"""
    registry = ElementRegistry()
    recipes = [
        make_recipe(
            1 + index,
            f"禁忌菜{index + 1}",
            registry,
            ingredients=["香菜"],
            techniques=["炒"],
            minutes=10,
            difficulty="简单",
        )
        for index in range(8)
    ]
    return registry, recipes


def scenario_taboo() -> str:
    """场景 1：禁忌过滤（别称 / 大类 / 小类）。"""
    registry, recipes = _taboo_dataset()
    cases = [
        ("别称（马铃薯↔土豆）", "马铃薯", {1, 2}, {3, 4, 5, 6, 7, 8}),
        ("大类（鱼类→鲫鱼/带鱼）", "鱼类", {3, 4}, {1, 2, 5, 6, 7, 8}),
        ("大类（水产→鲫鱼/带鱼/虾）", "水产", {3, 4, 5}, {1, 2, 6, 7, 8}),
        ("小类（鲫鱼，不扩大）", "鲫鱼", {3}, {1, 2, 4, 5, 6, 7, 8}),
    ]
    details: list[str] = []
    for title, taboo_name, taboo_ids, safe_ids in cases:
        service = FakeRecipeService(recipes)
        element = registry.decision_element("ingredient", taboo_name, "taboo")
        result = invoke_agent(service, count=len(safe_ids), elements=[element])
        returned = set(result)
        leaked = sorted(returned & taboo_ids)
        assert not leaked, f"{title}: 返回了禁忌菜谱 {leaked}"
        fabricated = sorted(returned - safe_ids)
        assert not fabricated, f"{title}: 返回了候选之外的菜谱 {fabricated}"
        assert sorted(result) == sorted(safe_ids), (
            f"{title}: 期望 {sorted(safe_ids)}，实际 {sorted(result)}"
        )
        details.append(f"{title} OK")
    return "；".join(details)


def scenario_preference(runs: int) -> str:
    """场景 2：偏好菜谱选取率高于无偏好菜谱（含别称 / 大类识别）。"""
    registry, recipes = _preference_dataset()
    preferred = {101, 102, 103, 104}
    others = {item["id"] for item in recipes} - preferred
    elements = [
        registry.decision_element("ingredient", "马铃薯", "preference"),
        registry.decision_element("ingredient", "鱼类", "preference"),
    ]

    counts = {item["id"]: 0 for item in recipes}
    for _ in range(runs):
        result = invoke_agent(FakeRecipeService(recipes), count=4, elements=elements)
        for recipe_id in result:
            assert recipe_id in counts, f"返回了候选之外的菜谱 id={recipe_id}"
            counts[recipe_id] += 1

    preferred_rate = statistics.mean(counts[item] / runs for item in preferred)
    other_rate = statistics.mean(counts[item] / runs for item in others)
    assert preferred_rate > other_rate, (
        f"偏好组平均选取率 {preferred_rate:.2f} 未高于无偏好组 {other_rate:.2f}；"
        f"明细={counts}"
    )
    return (
        f"偏好组均值 {preferred_rate:.2f} > 无偏好组均值 {other_rate:.2f}"
        f"（{runs} 轮，明细={counts}）"
    )


def scenario_few() -> str:
    """场景 3：菜谱过少时按实际数量返回，不编造、不凑数。"""
    _, recipes = _tiny_dataset()
    result = invoke_agent(FakeRecipeService(recipes), count=3)
    expected = sorted(item["id"] for item in recipes)
    assert sorted(result) == expected, f"期望 {expected}，实际 {sorted(result)}"
    return f"请求 3 道、池中 2 道 → 返回 {sorted(result)}"


def scenario_retry() -> str:
    """场景 4：首轮扇出无合适菜谱，回环到下一轮后取到。"""
    taboo_registry, _ = _all_taboo_dataset()
    taboo = taboo_registry.decision_element("ingredient", "香菜", "taboo")
    fruitless = _fruitless_recipes()
    suitable = _suitable_recipes()
    service = FakeRecipeService(
        recipes=suitable,
        page_source=lambda index: fruitless if index < 4 else suitable,
    )
    result = invoke_agent(service, count=2, elements=[taboo])

    assert service.page_fetch_count >= 8, (
        f"未发生多轮扇出，整页请求仅 {service.page_fetch_count} 次"
    )
    suitable_ids = {item["id"] for item in suitable}
    assert result, "多轮扇出后仍未返回任何菜谱"
    assert set(result) <= suitable_ids, (
        f"返回了首轮禁忌或候选之外的菜谱 {sorted(set(result) - suitable_ids)}"
    )
    return (
        f"首轮 4 页全为禁忌 → 回环到次轮取到 {sorted(result)}"
        f"（整页请求 {service.page_fetch_count} 次）"
    )


def scenario_empty() -> str:
    """场景 5：全部候选命中禁忌时返回空数组，且回环次数有上限。"""
    registry, recipes = _all_taboo_dataset()
    taboo = registry.decision_element("ingredient", "香菜", "taboo")
    service = FakeRecipeService(recipes)
    result = invoke_agent(service, count=2, elements=[taboo])

    assert result == [], f"应返回空数组，实际 {result}"
    rounds = len(_page_requests(service))
    assert rounds == MAX_ATTEMPTS, f"回环次数应为 {MAX_ATTEMPTS}，实际 {rounds}"
    return f"全部命中禁忌 → 返回 []，回环 {rounds} 轮后结束"


@dataclass
class ScenarioResult:
    """单个场景的执行结果。"""

    key: str
    title: str
    passed: bool
    detail: str


SCENARIOS: dict[str, tuple[str, Callable[..., str]]] = {
    "taboo": ("禁忌过滤（别称/大类/小类）", scenario_taboo),
    "preference": ("偏好选取率", scenario_preference),
    "few": ("菜谱过少不编造", scenario_few),
    "retry": ("单轮扇出不足后回环", scenario_retry),
    "empty": ("无符合条件返回空", scenario_empty),
}


def _check_llm_settings() -> bool:
    """校验当前 ``llm_provider`` 对应的大模型配置，缺失时给出可读提示。"""
    settings = get_settings()
    required_fields = {
        "custom": ("custom_base_url", "custom_model", "custom_api_key"),
        "ollama": ("ollama_base_url", "ollama_model"),
        "deepseek": ("deepseek_base_url", "deepseek_model", "deepseek_api_key"),
    }
    provider = settings.llm_provider
    missing = [
        name
        for name in required_fields.get(provider, ())
        if not getattr(settings, name)
    ]
    if missing:
        logger.error(
            "LLM_PROVIDER=%s 的配置缺失：%s；请在 .env 中补全后重试。",
            provider,
            ", ".join(missing),
        )
        return False
    logger.info("LLM 供应方：%s", provider)
    return True


def main() -> int:
    """解析参数、执行所选场景并输出汇总结果。"""
    parser = argparse.ArgumentParser(
        description="LLM 业务能力评估脚本（依赖真实大模型，手动执行）"
    )
    parser.add_argument(
        "--scenario",
        "-s",
        choices=[*SCENARIOS.keys(), "all"],
        default="all",
        help="要执行的场景，默认 all",
    )
    parser.add_argument(
        "--runs",
        "-r",
        type=int,
        default=10,
        help="偏好选取率场景的执行轮数，默认 10",
    )
    args = parser.parse_args()

    setup_logging()
    if not _check_llm_settings():
        return 2

    keys = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    results: list[ScenarioResult] = []
    for key in keys:
        title, func = SCENARIOS[key]
        logger.info("=" * 72)
        logger.info("[%s] %s", key, title)
        try:
            if key == "preference":
                detail = func(args.runs)
            else:
                detail = func()
        except Exception as exc:  # 汇总所有失败并继续执行后续场景
            logger.exception("[%s] 执行失败", key)
            results.append(ScenarioResult(key, title, False, str(exc)))
            continue
        logger.info("[%s] 通过：%s", key, detail)
        results.append(ScenarioResult(key, title, True, detail))

    logger.info("=" * 72)
    logger.info("评估汇总")
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        logger.info("[%s] %s - %s", status, result.title, result.detail)
    passed = sum(result.passed for result in results)
    logger.info("合计：%d/%d 通过", passed, len(results))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
