"""料理偏好方案 CRUD 接口测试。

对应 S2 ``design/sprints/S2/api.md`` 的方案接口（创建 / 列表 / 更新 / 删除）。
"""

from app.core.database import connection


def _technique_ids(limit: int = 2) -> list[int]:
    """返回前 ``limit`` 个料理手段要素 id。"""
    with connection() as conn:
        rows = conn.execute(
            "SELECT id FROM t_element WHERE type = 'technique' "
            "ORDER BY sort_order LIMIT ?",
            (limit,),
        ).fetchall()
    return [row["id"] for row in rows]


def _time_id() -> int:
    """返回第一个时间档位要素 id。"""
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM t_element WHERE type = 'time' ORDER BY sort_order LIMIT 1"
        ).fetchone()
    return row["id"]


async def test_create_scheme_returns_object(client):
    ids = _technique_ids()

    response = await client.post(
        "/api/preference-schemes", json={"name": "家常快手", "element_ids": ids}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["name"] == "家常快手"
    assert data["is_default"] == 0
    assert data["element_ids"] == ids
    assert isinstance(data["id"], int)
    assert data["created_at"]
    assert data["updated_at"]


async def test_create_scheme_allows_empty_elements(client):
    response = await client.post(
        "/api/preference-schemes", json={"name": "空方案", "element_ids": []}
    )

    assert response.status_code == 200
    assert response.json()["data"]["element_ids"] == []


async def test_create_scheme_allows_duplicate_name(client):
    ids = _technique_ids(limit=1)

    first = await client.post(
        "/api/preference-schemes", json={"name": "重名", "element_ids": ids}
    )
    second = await client.post(
        "/api/preference-schemes", json={"name": "重名", "element_ids": ids}
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] != second.json()["data"]["id"]


async def test_create_scheme_empty_name_rejected(client):
    response = await client.post(
        "/api/preference-schemes", json={"name": "", "element_ids": []}
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_create_scheme_nonexistent_element_rejected(client):
    with connection() as conn:
        max_id = conn.execute("SELECT MAX(id) AS m FROM t_element").fetchone()["m"]

    response = await client.post(
        "/api/preference-schemes",
        json={"name": "坏要素", "element_ids": [max_id + 100]},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_list_schemes_returns_paginated_envelope(client):
    for name in ["方案甲", "方案乙"]:
        await client.post(
            "/api/preference-schemes", json={"name": name, "element_ids": []}
        )

    response = await client.get("/api/preference-schemes")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert set(data.keys()) == {
        "list",
        "has_next",
        "total",
        "page",
        "page_size",
    }
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["has_next"] is False
    assert [item["name"] for item in data["list"]] == ["方案甲", "方案乙"]


async def test_list_schemes_empty(client):
    response = await client.get("/api/preference-schemes")

    data = response.json()["data"]
    assert data["list"] == []
    assert data["total"] == 0
    assert data["has_next"] is False


async def test_list_schemes_pagination(client):
    for i in range(25):
        await client.post(
            "/api/preference-schemes", json={"name": f"方案{i}", "element_ids": []}
        )

    page1 = await client.get("/api/preference-schemes", params={"page": 1})
    page2 = await client.get("/api/preference-schemes", params={"page": 2})

    d1 = page1.json()["data"]
    d2 = page2.json()["data"]
    assert d1["has_next"] is True
    assert len(d1["list"]) == 20
    assert d2["has_next"] is False
    assert len(d2["list"]) == 5
    # 两页无重复。
    ids1 = {item["id"] for item in d1["list"]}
    ids2 = {item["id"] for item in d2["list"]}
    assert not (ids1 & ids2)


async def test_update_scheme_persists_changes(client):
    ids_a = _technique_ids(limit=2)
    created = await client.post(
        "/api/preference-schemes", json={"name": "旧名", "element_ids": ids_a}
    )
    scheme_id = created.json()["data"]["id"]
    ids_b = sorted([_time_id(), _technique_ids(limit=1)[0]])

    response = await client.put(
        "/api/preference-schemes",
        json={"id": scheme_id, "name": "新名", "element_ids": ids_b, "is_default": 0},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "新名"
    assert data["element_ids"] == ids_b
    assert data["id"] == scheme_id

    listing = await client.get("/api/preference-schemes")
    item = next(i for i in listing.json()["data"]["list"] if i["id"] == scheme_id)
    assert item["name"] == "新名"
    assert item["element_ids"] == ids_b


async def test_update_scheme_default_is_mutually_exclusive(client):
    a = (
        await client.post(
            "/api/preference-schemes", json={"name": "A", "element_ids": []}
        )
    ).json()["data"]["id"]
    b = (
        await client.post(
            "/api/preference-schemes", json={"name": "B", "element_ids": []}
        )
    ).json()["data"]["id"]

    await client.put(
        "/api/preference-schemes",
        json={"id": a, "name": "A", "element_ids": [], "is_default": 1},
    )
    await client.put(
        "/api/preference-schemes",
        json={"id": b, "name": "B", "element_ids": [], "is_default": 1},
    )

    listing = await client.get("/api/preference-schemes")
    by_id = {item["id"]: item for item in listing.json()["data"]["list"]}
    assert by_id[a]["is_default"] == 0
    assert by_id[b]["is_default"] == 1


async def test_update_scheme_cancel_default(client):
    a = (
        await client.post(
            "/api/preference-schemes", json={"name": "A", "element_ids": []}
        )
    ).json()["data"]["id"]
    await client.put(
        "/api/preference-schemes",
        json={"id": a, "name": "A", "element_ids": [], "is_default": 1},
    )
    await client.put(
        "/api/preference-schemes",
        json={"id": a, "name": "A", "element_ids": [], "is_default": 0},
    )

    listing = await client.get("/api/preference-schemes")
    item = listing.json()["data"]["list"][0]
    assert item["is_default"] == 0


async def test_update_scheme_nonexistent_rejected(client):
    response = await client.put(
        "/api/preference-schemes",
        json={"id": 9999, "name": "x", "element_ids": [], "is_default": 0},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


async def test_update_scheme_empty_name_rejected(client):
    scheme = (
        await client.post(
            "/api/preference-schemes", json={"name": "x", "element_ids": []}
        )
    ).json()["data"]

    response = await client.put(
        "/api/preference-schemes",
        json={"id": scheme["id"], "name": "", "element_ids": [], "is_default": 0},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_delete_scheme_removes_row_and_links(client):
    ids = _technique_ids(limit=2)
    scheme = (
        await client.post(
            "/api/preference-schemes", json={"name": "待删", "element_ids": ids}
        )
    ).json()["data"]

    response = await client.request(
        "DELETE", "/api/preference-schemes", json={"id": scheme["id"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] is None

    with connection() as conn:
        scheme_row = conn.execute(
            "SELECT id FROM t_preference_scheme WHERE id = ?", (scheme["id"],)
        ).fetchone()
        link_rows = conn.execute(
            "SELECT id FROM t_scheme_element WHERE scheme_id = ?", (scheme["id"],)
        ).fetchall()
    assert scheme_row is None
    assert link_rows == []


async def test_delete_scheme_nonexistent_rejected(client):
    response = await client.request(
        "DELETE", "/api/preference-schemes", json={"id": 9999}
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


async def test_delete_default_scheme_leaves_no_default(client):
    a = (
        await client.post(
            "/api/preference-schemes", json={"name": "A", "element_ids": []}
        )
    ).json()["data"]["id"]
    b = (
        await client.post(
            "/api/preference-schemes", json={"name": "B", "element_ids": []}
        )
    ).json()["data"]["id"]
    await client.put(
        "/api/preference-schemes",
        json={"id": a, "name": "A", "element_ids": [], "is_default": 1},
    )

    await client.request("DELETE", "/api/preference-schemes", json={"id": a})

    listing = await client.get("/api/preference-schemes")
    remaining = listing.json()["data"]["list"]
    assert [item["id"] for item in remaining] == [b]
    assert all(item["is_default"] == 0 for item in remaining)


async def test_get_default_scheme_returns_none_when_no_default(client):
    response = await client.get("/api/preference-schemes/default")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] is None


async def test_get_default_scheme_returns_default(client):
    # 创建 A、B 两个方案，标记 B 为默认，接口应返回 B。
    await client.post("/api/preference-schemes", json={"name": "A", "element_ids": []})
    b = (
        await client.post(
            "/api/preference-schemes", json={"name": "B", "element_ids": []}
        )
    ).json()["data"]["id"]
    ids_b = _technique_ids()
    await client.put(
        "/api/preference-schemes",
        json={"id": b, "name": "B", "element_ids": ids_b, "is_default": 1},
    )

    response = await client.get("/api/preference-schemes/default")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == b
    assert data["is_default"] == 1
    assert data["element_ids"] == ids_b


async def test_get_default_scheme_reflects_latest_default(client):
    a = (
        await client.post(
            "/api/preference-schemes", json={"name": "A", "element_ids": []}
        )
    ).json()["data"]["id"]
    b = (
        await client.post(
            "/api/preference-schemes", json={"name": "B", "element_ids": []}
        )
    ).json()["data"]["id"]
    await client.put(
        "/api/preference-schemes",
        json={"id": a, "name": "A", "element_ids": [], "is_default": 1},
    )
    await client.put(
        "/api/preference-schemes",
        json={"id": b, "name": "B", "element_ids": [], "is_default": 1},
    )

    response = await client.get("/api/preference-schemes/default")

    assert response.json()["data"]["id"] == b
