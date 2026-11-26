"""本地存储生命周期辅助。

数据库文件与菜谱详情目录互为关联数据。当数据库文件不存在但菜谱目录仍存在时
（例如数据库被删除后重建），旧的菜谱目录会与新库失去引用关系，需要先按分钟
备份为 ``recipes_YYYYMMDD_HHMM``，再创建全新的空目录，避免新旧数据混用。
"""

import shutil
import time
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

# 备份目录名的时间戳格式（精确到分钟，本地时间）。
_BACKUP_TIME_FORMAT = "%Y%m%d_%H%M"


def backup_orphan_recipes_dir(database_path: str, recipes_dir: str) -> str | None:
    """数据库不存在但菜谱目录存在时，备份旧目录并创建全新空目录。

    仅当数据库文件缺失、而菜谱目录存在真实内容（忽略仅占位的 ``.gitkeep``）
    时才动作；否则不改动任何文件。

    Args:
        database_path: SQLite 数据库文件路径。
        recipes_dir: 菜谱 MD 详情目录路径。

    Returns:
        备份目录路径；无需备份时返回 None。
    """
    database = Path(database_path)
    recipes = Path(recipes_dir)
    if database.exists() or not _has_recipe_data(recipes):
        return None

    backup = _unique_backup_path(recipes)
    shutil.move(str(recipes), str(backup))
    # 重建空目录，保持后续写入路径稳定。
    recipes.mkdir(parents=True, exist_ok=True)
    logger.info("backed up orphan recipes dir: %s -> %s", recipes, backup)
    return str(backup)


def _has_recipe_data(recipes: Path) -> bool:
    """判断菜谱目录是否存在真实内容（忽略仅用于占位的 ``.gitkeep``）。"""
    if not recipes.is_dir():
        return False
    return any(child.name != ".gitkeep" for child in recipes.iterdir())


def _unique_backup_path(recipes: Path) -> Path:
    """生成不冲突的备份目录路径（同一分钟内追加序号）。"""
    timestamp = time.strftime(_BACKUP_TIME_FORMAT)
    backup = recipes.with_name(f"{recipes.name}_{timestamp}")
    suffix = 1
    while backup.exists():
        backup = recipes.with_name(f"{recipes.name}_{timestamp}_{suffix}")
        suffix += 1
    return backup
