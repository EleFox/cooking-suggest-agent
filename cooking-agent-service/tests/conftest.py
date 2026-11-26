"""pytest 全局夹具。

通过 httpx 的 ASGITransport 直接在内存中驱动 FastAPI 应用，
无需真正启动 uvicorn 进程。
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """返回基于 ASGI 的异步测试客户端。"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
