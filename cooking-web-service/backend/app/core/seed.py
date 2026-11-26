"""本地字典种子数据。

仅填充引用字典表 ``t_element``（烹饪难度 / 料理手段 / 时间档位），使设置页与
菜谱表单有可选项。**不写入任何业务数据**：成员、菜谱、方案等均由用户创建，
新数据库启动时为空。

种子导入是幂等的：已存在的行不会被改动，且会回填早期版本缺失的
``sort_order``（难度要素）。
"""

from app.core.database import connection
from app.core.logging import get_logger

logger = get_logger(__name__)

# 要素类型常量，与应用其余部分共享。
TYPE_DIFFICULTY = "difficulty"
TYPE_TECHNIQUE = "technique"
TYPE_TIME = "time"

_DIFFICULTIES = ["简单", "一般", "困难"]

# 料理手段要素（设置页按 sort_order 升序展示）。
_TECHNIQUES = ["煎", "炒", "凉拌", "油炸", "蒸", "炖", "煮", "烤"]

# 料理时间档位要素（name 存纯数字分钟数，作为偏好区间上限）。
_TIME_TIERS = ["15", "30", "60"]


def _get_or_create_element(
    conn, element_type: str, name: str, sort_order: int = 0
) -> int:
    """按 (type, name) 取要素 id，不存在则创建后返回新 id。

    已存在且 ``sort_order`` 为 0、而本次传入期望排序时，回填 ``sort_order``，
    以修复早期版本创建的难度要素（无排序）导致的选项缺失。

    Args:
        conn: 复用调用方事务的 SQLite 连接。
        element_type: 要素类型。
        name: 要素名。
        sort_order: 展示排序，0 表示不作为选项展示。

    Returns:
        对应 ``t_element.id``。
    """
    row = conn.execute(
        "SELECT id, sort_order FROM t_element WHERE type = ? AND name = ?",
        (element_type, name),
    ).fetchone()
    if row is not None:
        if sort_order > 0 and row["sort_order"] == 0:
            conn.execute(
                "UPDATE t_element SET sort_order = ? WHERE id = ?",
                (sort_order, row["id"]),
            )
        return row["id"]
    cur = conn.execute(
        "INSERT INTO t_element (type, name, sort_order) VALUES (?, ?, ?)",
        (element_type, name, sort_order),
    )
    return cur.lastrowid


def seed() -> None:
    """幂等写入要素字典种子（难度 / 料理手段 / 时间档位）。

    不写入成员 / 菜谱 / 方案等业务数据，新库业务数据保持为空。
    """
    with connection() as conn:
        for sort_order, name in enumerate(_DIFFICULTIES, start=1):
            _get_or_create_element(conn, TYPE_DIFFICULTY, name, sort_order=sort_order)
        for sort_order, name in enumerate(_TECHNIQUES, start=1):
            _get_or_create_element(conn, TYPE_TECHNIQUE, name, sort_order=sort_order)
        for sort_order, name in enumerate(_TIME_TIERS, start=1):
            _get_or_create_element(conn, TYPE_TIME, name, sort_order=sort_order)

    logger.info("seeded dictionary elements (difficulty / technique / time)")
