"""成员 CRUD 接口测试。

对应 S3 ``design/sprints/S3/api.md`` 的成员接口（查询 / 创建 / 更新 / 删除），
覆盖要素 ``resolve-or-create`` 与增量 ``operate`` 语义。
"""

from app.core.database import connection


def _element_id(element_type: str, name: str) -> int | None:
    """按类型 + 名称查询要素 id，不存在返回 None。"""
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM t_element WHERE type = ? AND name = ?",
            (element_type, name),
        ).fetchone()
    return row["id"] if row else None


def _element_count() -> int:
    with connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM t_element").fetchone()["n"]


def _technique_id(name: str = "炖") -> int:
    element_id = _element_id("technique", name)
    assert element_id is not None
    return element_id


# ---------------------------------------------------------------------------
# 创建成员
# ---------------------------------------------------------------------------


async def test_create_member_persists_preferences_and_taboos(client):
    response = await client.post(
        "/api/members",
        json={
            "name": "爸爸",
            "preferences": [
                {"name": "牛肉", "type": "ingredient"},
                {"name": "微辣", "type": "taste"},
            ],
            "taboos": [{"name": "香菜", "type": "ingredient"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["name"] == "爸爸"
    assert isinstance(data["id"], int)
    assert {item["name"] for item in data["preferences"]} == {"牛肉", "微辣"}
    assert {item["name"] for item in data["taboos"]} == {"香菜"}
    assert data["created_at"]
    assert data["updated_at"]

    # 落库校验。
    listing = await client.get("/api/members")
    stored = listing.json()["data"]
    assert len(stored) == 1
    assert stored[0]["name"] == "爸爸"


async def test_create_member_resolves_existing_element_without_duplicate(client):
    before = _element_count()
    technique_id = _technique_id("炖")

    response = await client.post(
        "/api/members",
        json={
            "name": "妈妈",
            "preferences": [{"name": "炖", "type": "technique"}],
            "taboos": [],
        },
    )

    data = response.json()["data"]
    assert data["preferences"][0]["id"] == technique_id
    # 复用既有要素，未新增行。
    assert _element_count() == before


async def test_create_member_allows_empty_elements(client):
    response = await client.post(
        "/api/members", json={"name": "孩子", "preferences": [], "taboos": []}
    )

    data = response.json()["data"]
    assert data["preferences"] == []
    assert data["taboos"] == []


async def test_create_member_allows_duplicate_name(client):
    first = await client.post("/api/members", json={"name": "重名", "preferences": []})
    second = await client.post("/api/members", json={"name": "重名", "preferences": []})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] != second.json()["data"]["id"]


async def test_create_member_allows_same_element_both_sides(client):
    response = await client.post(
        "/api/members",
        json={
            "name": "爷爷",
            "preferences": [{"name": "花生", "type": "ingredient"}],
            "taboos": [{"name": "花生", "type": "ingredient"}],
        },
    )

    data = response.json()["data"]
    assert {item["name"] for item in data["preferences"]} == {"花生"}
    assert {item["name"] for item in data["taboos"]} == {"花生"}


async def test_create_member_empty_name_rejected(client):
    response = await client.post(
        "/api/members", json={"name": "   ", "preferences": []}
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_create_member_invalid_element_type_rejected(client):
    response = await client.post(
        "/api/members",
        json={"name": "A", "preferences": [{"name": "牛肉", "type": "unknown"}]},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_create_member_empty_element_name_rejected(client):
    response = await client.post(
        "/api/members",
        json={"name": "A", "preferences": [{"name": "  ", "type": "ingredient"}]},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_create_member_non_numeric_time_rejected(client):
    response = await client.post(
        "/api/members",
        json={"name": "A", "preferences": [{"name": "半小时", "type": "time"}]},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


# ---------------------------------------------------------------------------
# 查询成员列表
# ---------------------------------------------------------------------------


async def test_list_members_empty(client):
    response = await client.get("/api/members")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] == []


async def test_list_members_returns_nested_elements(client):
    await client.post(
        "/api/members",
        json={
            "name": "爸爸",
            "preferences": [{"name": "牛肉", "type": "ingredient"}],
            "taboos": [{"name": "香菜", "type": "ingredient"}],
        },
    )

    response = await client.get("/api/members")

    data = response.json()["data"]
    assert len(data) == 1
    item = data[0]
    assert set(item.keys()) == {
        "id",
        "name",
        "preferences",
        "taboos",
        "created_at",
        "updated_at",
    }
    for element in item["preferences"] + item["taboos"]:
        assert set(element.keys()) == {"id", "name", "type"}


# ---------------------------------------------------------------------------
# 更新成员（增量 operate）
# ---------------------------------------------------------------------------


async def test_update_member_name_persists(client):
    created = (
        await client.post("/api/members", json={"name": "旧名", "preferences": []})
    ).json()["data"]

    response = await client.put(
        "/api/members",
        json={"id": created["id"], "name": "新名", "preferences": [], "taboos": []},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "新名"

    listing = await client.get("/api/members")
    assert listing.json()["data"][0]["name"] == "新名"


async def test_update_member_adds_element(client):
    created = (
        await client.post("/api/members", json={"name": "爸爸", "preferences": []})
    ).json()["data"]

    response = await client.put(
        "/api/members",
        json={
            "id": created["id"],
            "name": "爸爸",
            "preferences": [{"name": "牛肉", "type": "ingredient", "operate": "add"}],
            "taboos": [],
        },
    )

    names = {item["name"] for item in response.json()["data"]["preferences"]}
    assert names == {"牛肉"}


async def test_update_member_add_existing_relation_is_idempotent(client):
    created = (
        await client.post(
            "/api/members",
            json={
                "name": "爸爸",
                "preferences": [{"name": "牛肉", "type": "ingredient"}],
            },
        )
    ).json()["data"]
    element_id = created["preferences"][0]["id"]

    response = await client.put(
        "/api/members",
        json={
            "id": created["id"],
            "name": "爸爸",
            "preferences": [
                {
                    "id": element_id,
                    "name": "牛肉",
                    "type": "ingredient",
                    "operate": "add",
                }
            ],
            "taboos": [],
        },
    )

    assert len(response.json()["data"]["preferences"]) == 1


async def test_update_member_removes_element(client):
    created = (
        await client.post(
            "/api/members",
            json={
                "name": "爸爸",
                "preferences": [
                    {"name": "牛肉", "type": "ingredient"},
                    {"name": "微辣", "type": "taste"},
                ],
            },
        )
    ).json()["data"]
    beef_id = next(
        item["id"] for item in created["preferences"] if item["name"] == "牛肉"
    )

    response = await client.put(
        "/api/members",
        json={
            "id": created["id"],
            "name": "爸爸",
            "preferences": [
                {
                    "id": beef_id,
                    "name": "牛肉",
                    "type": "ingredient",
                    "operate": "remove",
                }
            ],
            "taboos": [],
        },
    )

    names = {item["name"] for item in response.json()["data"]["preferences"]}
    assert names == {"微辣"}


async def test_update_member_edits_element_keeps_old_element_row(client):
    created = (
        await client.post(
            "/api/members",
            json={
                "name": "爸爸",
                "preferences": [{"name": "牛肉", "type": "ingredient"}],
            },
        )
    ).json()["data"]
    beef_id = created["preferences"][0]["id"]

    response = await client.put(
        "/api/members",
        json={
            "id": created["id"],
            "name": "爸爸",
            "preferences": [
                {"id": beef_id, "name": "羊肉", "type": "ingredient", "operate": "edit"}
            ],
            "taboos": [],
        },
    )

    names = {item["name"] for item in response.json()["data"]["preferences"]}
    assert names == {"羊肉"}
    # 要素只增不删：旧要素行仍在。
    assert _element_id("ingredient", "牛肉") == beef_id


async def test_update_member_empty_arrays_keep_existing(client):
    created = (
        await client.post(
            "/api/members",
            json={
                "name": "爸爸",
                "preferences": [{"name": "牛肉", "type": "ingredient"}],
                "taboos": [{"name": "香菜", "type": "ingredient"}],
            },
        )
    ).json()["data"]

    response = await client.put(
        "/api/members",
        json={"id": created["id"], "name": "爸爸", "preferences": [], "taboos": []},
    )

    data = response.json()["data"]
    assert {item["name"] for item in data["preferences"]} == {"牛肉"}
    assert {item["name"] for item in data["taboos"]} == {"香菜"}


async def test_update_member_nonexistent_rejected(client):
    response = await client.put(
        "/api/members",
        json={"id": 9999, "name": "x", "preferences": [], "taboos": []},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 404


async def test_update_member_empty_name_rejected(client):
    created = (
        await client.post("/api/members", json={"name": "爸爸", "preferences": []})
    ).json()["data"]

    response = await client.put(
        "/api/members",
        json={"id": created["id"], "name": "", "preferences": [], "taboos": []},
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_update_member_invalid_operate_rejected(client):
    created = (
        await client.post("/api/members", json={"name": "爸爸", "preferences": []})
    ).json()["data"]

    response = await client.put(
        "/api/members",
        json={
            "id": created["id"],
            "name": "爸爸",
            "preferences": [
                {"id": 1, "name": "牛肉", "type": "ingredient", "operate": "boom"}
            ],
            "taboos": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


async def test_update_member_remove_without_id_rejected(client):
    created = (
        await client.post("/api/members", json={"name": "爸爸", "preferences": []})
    ).json()["data"]

    response = await client.put(
        "/api/members",
        json={
            "id": created["id"],
            "name": "爸爸",
            "preferences": [
                {"name": "牛肉", "type": "ingredient", "operate": "remove"}
            ],
            "taboos": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["code"] == 422


# ---------------------------------------------------------------------------
# 删除成员
# ---------------------------------------------------------------------------


async def test_delete_member_removes_links_but_keeps_elements(client):
    created = (
        await client.post(
            "/api/members",
            json={
                "name": "爸爸",
                "preferences": [{"name": "牛肉", "type": "ingredient"}],
                "taboos": [{"name": "香菜", "type": "ingredient"}],
            },
        )
    ).json()["data"]
    beef_id = created["preferences"][0]["id"]

    response = await client.request(
        "DELETE", "/api/members", json={"id": created["id"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"] is None

    listing = await client.get("/api/members")
    assert listing.json()["data"] == []

    with connection() as conn:
        member_rows = conn.execute(
            "SELECT id FROM t_member WHERE id = ?", (created["id"],)
        ).fetchall()
        link_rows = conn.execute(
            "SELECT id FROM t_member_element WHERE member_id = ?", (created["id"],)
        ).fetchall()
    assert member_rows == []
    assert link_rows == []
    # 要素只增不删。
    assert _element_id("ingredient", "牛肉") == beef_id


async def test_delete_member_nonexistent_rejected(client):
    response = await client.request("DELETE", "/api/members", json={"id": 9999})

    assert response.status_code == 200
    assert response.json()["code"] == 404
