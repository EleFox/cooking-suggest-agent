async def test_health_returns_ok(client):
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_content_type_is_json(client):
    response = await client.get("/api/health")

    assert response.headers["content-type"] == "application/json"


async def test_root_returns_service_info(client):
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "cooking-web-service"
    assert data["message"] == "Hello from Cooking Web Service"
