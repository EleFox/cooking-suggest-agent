"""菜谱目录生命周期（孤儿目录备份）测试。"""

from pathlib import Path

from app.core import storage
from app.core.storage import backup_orphan_recipes_dir


def _write_marker(recipes: Path) -> None:
    (recipes / "r-1.md").write_text("old detail", encoding="utf-8")


def test_no_backup_when_database_exists(tmp_path):
    db = tmp_path / "cooking.db"
    db.write_text("", encoding="utf-8")
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    _write_marker(recipes)

    assert backup_orphan_recipes_dir(str(db), str(recipes)) is None
    # 数据库存在时不改动菜谱目录。
    assert (recipes / "r-1.md").exists()


def test_no_backup_when_recipes_missing(tmp_path):
    db = tmp_path / "cooking.db"

    assert backup_orphan_recipes_dir(str(db), str(tmp_path / "recipes")) is None


def test_no_backup_when_recipes_dir_only_gitkeep(tmp_path):
    db = tmp_path / "cooking.db"
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / ".gitkeep").write_text("", encoding="utf-8")

    assert backup_orphan_recipes_dir(str(db), str(recipes)) is None
    # 占位目录原样保留，未被备份。
    assert (recipes / ".gitkeep").exists()
    assert list(tmp_path.glob("recipes_*")) == []


def test_backs_up_orphan_recipes_dir(tmp_path):
    db = tmp_path / "cooking.db"
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    _write_marker(recipes)

    backup = backup_orphan_recipes_dir(str(db), str(recipes))

    assert backup is not None
    backup_path = Path(backup)
    assert backup_path.name.startswith("recipes_")
    assert backup_path.is_dir()
    # 旧内容完整保留在备份目录。
    assert (backup_path / "r-1.md").read_text(encoding="utf-8") == "old detail"
    # 新建的菜谱目录为空。
    assert recipes.is_dir()
    assert list(recipes.iterdir()) == []


def test_backup_name_collision_appends_suffix(tmp_path, monkeypatch):
    class _FixedTime:
        @staticmethod
        def strftime(_fmt: str) -> str:
            return "20260911_2105"

    monkeypatch.setattr(storage, "time", _FixedTime)

    db = tmp_path / "cooking.db"
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    _write_marker(recipes)
    (tmp_path / "recipes_20260911_2105").mkdir()

    backup = backup_orphan_recipes_dir(str(db), str(recipes))

    assert Path(backup).name == "recipes_20260911_2105_1"
