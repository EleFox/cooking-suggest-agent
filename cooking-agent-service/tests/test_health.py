"""健康检查接口测试。"""


async def test_health_returns_ok(client):
    """正向路径：健康检查返回存活状态。"""
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_content_type_is_json(client):
    """边界情况：健康检查响应必须为 JSON。"""
    response = await client.get("/api/health")

    assert response.headers["content-type"] == "application/json"


async def test_root_path_is_not_exposed(client):
    """无效输入：文档未定义的根路径不对外暴露（返回 404）。"""
    response = await client.get("/")

    assert response.status_code == 404


async def test_unknown_path_returns_404(client):
    """无效输入：未注册的路径返回 404。"""
    response = await client.get("/api/unknown")

    assert response.status_code == 404
