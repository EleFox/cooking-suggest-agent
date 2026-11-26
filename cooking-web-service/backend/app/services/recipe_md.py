"""菜谱 MD 详情文件读写。

菜谱做法详情以 Markdown 文件存储（辅助数据，可缺失）：front-matter 由表单
字段生成，正文为做法步骤。文件名固定为 ``r-{id}.md``，目录复用数据库所在
数据目录下的 ``recipes`` 子目录（见 ``Settings.recipes_dir``）。
"""

from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# front-matter 分隔线。
_FRONT_MATTER_DELIMITER = "---"


def recipes_dir() -> Path:
    """返回菜谱 MD 文件目录，不存在时创建。"""
    path = Path(get_settings().recipes_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def recipe_file_path(recipe_id: int) -> Path:
    """返回菜谱 id 对应的 MD 文件路径（不保证文件存在）。"""
    return recipes_dir() / f"r-{recipe_id}.md"


def write_recipe_file(
    recipe_id: int, name: str, elements: list[dict], detail: str
) -> str:
    """写入 / 覆盖菜谱 MD 文件，返回文件路径字符串。

    Args:
        recipe_id: 菜谱 id（决定文件名）。
        name: 菜名（写入 front-matter）。
        elements: 菜谱关联要素（含 name / type），用于生成 front-matter 标签。
        detail: 做法正文。

    Returns:
        MD 文件路径字符串。

    Raises:
        OSError: 文件写入失败（由调用方回滚事务）。
    """
    path = recipe_file_path(recipe_id)
    front_matter = _build_front_matter(name, elements)
    content = f"{front_matter}\n{detail.strip()}\n"
    path.write_text(content, encoding="utf-8")
    logger.info("wrote recipe md: id=%s path=%s", recipe_id, path)
    return str(path)


def read_recipe_detail(file_path: str | None) -> str | None:
    """读取 MD 文件正文作为做法；文件缺失或路径为空返回 None。

    Args:
        file_path: ``t_recipe.file_path`` 存储的文件路径。

    Returns:
        去掉 front-matter 后的正文文本；无内容返回 None。
    """
    if not file_path:
        return None
    path = Path(file_path)
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")
    body = _strip_front_matter(text).strip()
    return body or None


def delete_recipe_file(file_path: str | None) -> None:
    """删除菜谱 MD 文件；路径为空或文件已缺失时静默忽略。"""
    if not file_path:
        return
    Path(file_path).unlink(missing_ok=True)
    logger.info("deleted recipe md: path=%s", file_path)


def _build_front_matter(name: str, elements: list[dict]) -> str:
    """按要素类型聚合生成 front-matter 文本。"""
    ingredients = [e["name"] for e in elements if e["type"] == "ingredient"]
    techniques = [e["name"] for e in elements if e["type"] == "technique"]
    times = [e["name"] for e in elements if e["type"] == "time"]
    difficulties = [e["name"] for e in elements if e["type"] == "difficulty"]

    lines = [_FRONT_MATTER_DELIMITER, f"name: {name}"]
    if ingredients:
        lines.append(f"ingredients: [{', '.join(ingredients)}]")
    if techniques:
        lines.append(f"techniques: [{', '.join(techniques)}]")
    if times:
        lines.append(f"time: {times[0]}")
    if difficulties:
        lines.append(f"difficulty: {difficulties[0]}")
    lines.append(_FRONT_MATTER_DELIMITER)
    return "\n".join(lines)


def _strip_front_matter(text: str) -> str:
    """剥离首部 ``---`` front-matter，返回正文；无 front-matter 原样返回。"""
    if not text.startswith(_FRONT_MATTER_DELIMITER):
        return text
    # 找到第二个分隔线之后的内容。
    end = text.find(f"\n{_FRONT_MATTER_DELIMITER}", len(_FRONT_MATTER_DELIMITER))
    if end == -1:
        return text
    body_start = text.find("\n", end + 1)
    if body_start == -1:
        return ""
    return text[body_start + 1 :]
