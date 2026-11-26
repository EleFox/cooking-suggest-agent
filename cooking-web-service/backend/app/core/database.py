"""SQLite 持久化基础设施。

提供统一的连接工厂与建表逻辑。数据库为单用户本地存储，每次操作使用
短生命周期连接。

表结构遵循 ``design/project/persistence.md``。此处仅定义当前迭代所需的表，
后续随功能实现逐步补充。
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# 多线程（请求线程池）并发访问 SQLite 时，写锁竞争等待上限（毫秒）。
_BUSY_TIMEOUT_MS = 5000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS t_element (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE(type, name)
);

CREATE TABLE IF NOT EXISTS t_recipe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    file_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS t_recipe_element (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES t_recipe(id),
    element_id INTEGER NOT NULL REFERENCES t_element(id),
    UNIQUE(recipe_id, element_id)
);

CREATE INDEX IF NOT EXISTS idx_recipe_element_element
    ON t_recipe_element(element_id);

CREATE TABLE IF NOT EXISTS t_preference_scheme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS t_scheme_element (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_id INTEGER NOT NULL REFERENCES t_preference_scheme(id),
    element_id INTEGER NOT NULL REFERENCES t_element(id),
    UNIQUE(scheme_id, element_id)
);

CREATE INDEX IF NOT EXISTS idx_scheme_element_element
    ON t_scheme_element(element_id);

CREATE TABLE IF NOT EXISTS t_member (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS t_member_element (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES t_member(id),
    element_id INTEGER NOT NULL REFERENCES t_element(id),
    relation_type TEXT NOT NULL,
    UNIQUE(member_id, element_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_member_element_member
    ON t_member_element(member_id, relation_type);
"""


def _database_path() -> str:
    settings = get_settings()
    return settings.database_path


def get_connection() -> sqlite3.Connection:
    """打开一个按列名访问的新 SQLite 连接。

    每条连接的 ``busy_timeout`` 用于线程池并发下的写锁等待；WAL 日志模式让
    读请求不被写事务阻塞，适配"决策写 / 反向查询读"的并发形态。
    """
    conn = sqlite3.connect(_database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """上下文管理器：成功时提交事务，异常时回滚。

    Yields:
        一个可用的 SQLite 连接；退出时自动提交或回滚并关闭。
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """在数据库不存在时创建所需的表。"""
    with connection() as conn:
        conn.executescript(_SCHEMA)
    logger.info("database initialised at %s", _database_path())
