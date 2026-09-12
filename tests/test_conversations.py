from fastapi.testclient import TestClient


def test_create_and_get_conversation(client: TestClient, create_test_user):
    alice = create_test_user("alice", "alice@example.com")
    bob = create_test_user("bob", "bob@example.com")

    res = client.post(
        "/api/v1/conversations",
        json={"user_id": bob["id"]},
        headers=alice["headers"],
    )
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    conv_id = data["id"]
    part_ids = {p["user_id"] for p in data["participants"]}
    assert part_ids == {alice["id"], bob["id"]}

    res_repeat = client.post(
        "/api/v1/conversations",
        json={"user_id": bob["id"]},
        headers=alice["headers"],
    )
    assert res_repeat.status_code == 201
    assert res_repeat.json()["id"] == conv_id

    bob_list = client.get("/api/v1/conversations", headers=bob["headers"])
    assert bob_list.status_code == 200
    assert any(c["id"] == conv_id for c in bob_list.json())


def test_conversation_authorization_forbidden(client: TestClient, create_test_user):
    alice = create_test_user("alice", "alice@example.com")
    bob = create_test_user("bob", "bob@example.com")
    eve = create_test_user("eve", "eve@example.com")

    res = client.post(
        "/api/v1/conversations",
        json={"user_id": bob["id"]},
        headers=alice["headers"],
    )
    conv_id = res.json()["id"]

    eve_access = client.get(f"/api/v1/conversations/{conv_id}", headers=eve["headers"])
    assert eve_access.status_code == 403
    assert "Access denied" in eve_access.json()["detail"]

    eve_msgs = client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=eve["headers"],
    )
    assert eve_msgs.status_code == 403
    assert "Access denied" in eve_msgs.json()["detail"]


def test_cannot_create_conversation_with_self(client: TestClient, create_test_user):
    alice = create_test_user("alice", "alice@example.com")
    res = client.post(
        "/api/v1/conversations",
        json={"user_id": alice["id"]},
        headers=alice["headers"],
    )
    assert res.status_code == 400
    assert "Cannot start a conversation with yourself" in res.json()["detail"]
