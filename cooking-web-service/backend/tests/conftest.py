# ruff: noqa: I001
# 测试库路径必须在导入任何 app 模块前设置：app 模块在 import 时会通过
# get_logger() 触发 get_settings() 缓存，提前设置 DATABASE_PATH 才能确保
# 测试使用独立临时库而非 .env 中的路径。
import os
import shutil
import tempfile

TEST_DB = os.path.join(tempfile.gettempdir(), "cooking_web_service_test.db")
os.environ["DATABASE_PATH"] = TEST_DB

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import init_db
from app.core.seed import seed

from app.main import app


@pytest.fixture(autouse=True)
def _fresh_db():
    # WAL 模式会生成 -wal / -shm 附属文件，需与主库一并清理，避免跨用例残留。
    for suffix in ("", "-wal", "-shm"):
        path = f"{TEST_DB}{suffix}"
        if os.path.exists(path):
            os.remove(path)
    # 菜谱详情文件与数据库同目录，逐例清理避免跨用例串数据。
    recipes_dir = os.path.join(tempfile.gettempdir(), "recipes")
    if os.path.isdir(recipes_dir):
        shutil.rmtree(recipes_dir)
    init_db()
    seed()
    yield


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
