"""菜谱模拟数据批量导入脚本（无第三方依赖）。

读取 ``datas/recipes.json`` 中本批待审阅的菜谱数据，通过 web-service 的 HTTP
接口逐条写入，**不直接操作数据库**。脚本负责：

1. 读取并本地自检 ``datas/recipes.json`` 的要素硬约束；
2. 插入前探测后端存活（未启动直接失败退出，不自动拉起服务）；
3. 逐条 ``POST /api/recipes``，打印每条结果；
4. 汇总新增 / 失败，有失败则以非零码退出；
5. 用一次 ``GET /api/recipes`` 读取 ``total`` 做数量核对。

按约定**不做去重**：不拉取已有菜名，重复风险由人工审阅把关。

用法::

    python3 scripts/seed_recipes.py --dry-run   # 仅本地校验，不写后端
    python3 scripts/seed_recipes.py             # 读取 datas/recipes.json 并插入
"""

import argparse
import json
import sys
from pathlib import Path
from urllib import error, request

# 合法要素类型（与 web-service ``element_service.VALID_ELEMENT_TYPES`` 保持一致）。
VALID_TYPES = frozenset(
    {"ingredient", "technique", "time", "allergen", "taste", "difficulty"}
)

# 每菜谱至多 1 个的单值要素类型。
SINGLE_VALUE_TYPES = ("time", "difficulty")

# 默认待审阅数据文件：本仓库 ``datas/recipes.json``。
DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent / "datas" / "recipes.json"


def _request(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    """发送 HTTP 请求并解析 JSON 响应。

    Args:
        method: HTTP 方法（GET / POST）。
        url: 完整请求地址。
        payload: 请求体字典；为 None 时发送空请求。

    Returns:
        ``(状态码, 响应 JSON 字典)``；响应体非 JSON 时字典为 ``{}``。

    Raises:
        ConnectionError: 无法连接后端服务。
    """
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, _loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, _loads(body)
    except error.URLError as exc:
        raise ConnectionError(f"无法连接后端: {exc.reason}") from exc


def _loads(text: str) -> dict:
    """尽力把文本解析为 JSON 对象，失败返回空字典。"""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_recipes(path: Path) -> list[dict]:
    """读取待审阅的菜谱 JSON 数组，文件缺失或格式非法抛出 ``ValueError``。"""
    if not path.exists():
        raise ValueError(f"数据文件不存在: {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"数据文件不是合法 JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("数据文件顶层必须是 JSON 数组")
    return parsed


def _validate_recipe(recipe: dict) -> str | None:
    """本地校验单条菜谱，合法返回 None，否则返回错误描述。"""
    if not isinstance(recipe, dict):
        return "条目不是 JSON 对象"
    name = recipe.get("name")
    if not isinstance(name, str) or not name.strip():
        return "菜名为空"

    elements = recipe.get("elements")
    if elements is None:
        elements = []
    if not isinstance(elements, list):
        return "elements 不是数组"

    counts: dict[str, int] = {}
    for element in elements:
        if not isinstance(element, dict):
            return "要素项不是 JSON 对象"
        element_type = element.get("type")
        element_name = element.get("name")
        if element_type not in VALID_TYPES:
            return f"非法要素类型: {element_type}"
        if not isinstance(element_name, str) or not element_name.strip():
            return "要素名为空"
        if element_type == "time":
            candidate = element_name.strip()
            if not candidate.isdigit() or int(candidate) < 1:
                return f"时间要素必须为正整数分钟数: {element_name}"
        counts[element_type] = counts.get(element_type, 0) + 1

    for single_type in SINGLE_VALUE_TYPES:
        if counts.get(single_type, 0) > 1:
            return f"{single_type} 类型要素至多 1 个"
    return None


def fetch_total(base_url: str) -> int:
    """读取菜谱总数（分页信封的 total）。"""
    _, body = _request("GET", f"{base_url}/recipes?page=1&page_size=1")
    data = body.get("data") or {}
    return int(data.get("total") or 0)


def main() -> int:
    """脚本入口：读取数据文件并逐条导入。"""
    parser = argparse.ArgumentParser(description="菜谱模拟数据批量导入")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="待审阅菜谱 JSON 文件（默认 datas/recipes.json）",
    )
    parser.add_argument("--limit", type=int, default=0, help="最多导入条数，0 表示全部")
    parser.add_argument(
        "--base-url", default="http://localhost:8000/api", help="后端 API 基址"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="仅本地校验，不写入后端"
    )
    args = parser.parse_args()

    try:
        recipes = _load_recipes(args.file)
    except ValueError as exc:
        print(f"[错误] {exc}")
        return 2
    if args.limit > 0:
        recipes = recipes[: args.limit]

    # dry-run 只做本地校验，不依赖后端。
    if args.dry_run:
        failed = 0
        for index, recipe in enumerate(recipes, start=1):
            problem = _validate_recipe(recipe)
            if problem:
                failed += 1
                print(f"[校验失败] #{index} {problem}")
        print(f"\n[完成] 共校验 {len(recipes)} 条，失败 {failed} 条（dry-run 未写入）")
        return 1 if failed else 0

    # 插入前探测后端存活，未启动直接暂停（非零退出）。
    try:
        _request("GET", f"{args.base_url}/recipes?page=1&page_size=1")
    except ConnectionError as exc:
        print(f"[暂停] {exc}")
        print("请先启动 web-service 后端（默认 http://localhost:8000）后重试。")
        return 2

    print(f"[信息] 读取 {args.file}，开始导入 {len(recipes)} 条\n")

    created = failed = 0
    for index, recipe in enumerate(recipes, start=1):
        problem = _validate_recipe(recipe)
        if problem:
            failed += 1
            print(f"[失败] #{index} 校验不通过: {problem}")
            continue

        name = recipe["name"].strip()
        try:
            status, body = _request(
                "POST",
                f"{args.base_url}/recipes",
                {
                    "name": name,
                    "elements": recipe.get("elements") or [],
                    "detail": recipe.get("detail"),
                },
            )
        except ConnectionError as exc:
            failed += 1
            print(f"[失败] #{index} {name}: {exc}")
            continue

        if status == 200 and body.get("code") == 200:
            created += 1
            recipe_id = (body.get("data") or {}).get("id")
            print(f"[新增] #{index} {name} -> id={recipe_id}")
        else:
            failed += 1
            message = body.get("message") or f"HTTP {status}"
            print(f"[失败] #{index} {name}: {message}")

    # 汇总 + 数量核对。
    print(f"\n[统计] 新增 {created}，失败 {failed}")
    try:
        total = fetch_total(args.base_url)
        print(f"[核对] 当前后端菜谱 total={total}")
    except ConnectionError as exc:
        print(f"[警告] 核对总数失败: {exc}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
