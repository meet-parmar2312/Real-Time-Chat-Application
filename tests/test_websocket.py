import pytest
from fastapi.testclient import TestClient


def test_websocket_authentication_rejected(client: TestClient, create_test_user):
    alice = create_test_user("alice", "alice@example.com")
    bob = create_test_user("bob", "bob@example.com")

    conv_res = client.post(
        "/api/v1/conversations",
        json={"user_id": bob["id"]},
        headers=alice["headers"],
    )
    conv_id = conv_res.json()["id"]

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/conversations/{conv_id}") as ws:
            pass

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/conversations/{conv_id}?token=invalid_jwt") as ws:
            pass


def test_websocket_authorization_forbidden(client: TestClient, create_test_user):
    alice = create_test_user("alice", "alice@example.com")
    bob = create_test_user("bob", "bob@example.com")
    eve = create_test_user("eve", "eve@example.com")

    conv_res = client.post(
        "/api/v1/conversations",
        json={"user_id": bob["id"]},
        headers=alice["headers"],
    )
    conv_id = conv_res.json()["id"]

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/conversations/{conv_id}?token={eve['token']}") as ws:
            pass


def test_websocket_messaging_and_presence(client: TestClient, create_test_user):
    alice = create_test_user("alice", "alice@example.com")
    bob = create_test_user("bob", "bob@example.com")

    conv_res = client.post(
        "/api/v1/conversations",
        json={"user_id": bob["id"]},
        headers=alice["headers"],
    )
    conv_id = conv_res.json()["id"]

    status_a = client.get(f"/api/v1/users/{alice['id']}/status", headers=alice["headers"]).json()
    status_b = client.get(f"/api/v1/users/{bob['id']}/status", headers=bob["headers"]).json()
    assert status_a["online"] is False
    assert status_b["online"] is False

    with client.websocket_connect(f"/ws/conversations/{conv_id}?token={alice['token']}") as ws_alice:
        status_a = client.get(f"/api/v1/users/{alice['id']}/status", headers=alice["headers"]).json()
        assert status_a["online"] is True

        with client.websocket_connect(f"/ws/conversations/{conv_id}?token={bob['token']}") as ws_bob:
            status_b = client.get(f"/api/v1/users/{bob['id']}/status", headers=bob["headers"]).json()
            assert status_b["online"] is True

            ws_alice.send_json({"content": "Hello Bob, this is real-time!"})

            ack = ws_alice.receive_json()
            assert ack["event"] == "ack"
            assert ack["status"] == "delivered"
            assert "message_id" in ack
            msg_id = ack["message_id"]

            received_msg = ws_bob.receive_json()
            assert received_msg["message_id"] == msg_id
            assert received_msg["conversation_id"] == conv_id
            assert received_msg["sender_id"] == alice["id"]
            assert received_msg["content"] == "Hello Bob, this is real-time!"
            assert "created_at" in received_msg

        status_b = client.get(f"/api/v1/users/{bob['id']}/status", headers=alice["headers"]).json()
        assert status_b["online"] is False

    status_a = client.get(f"/api/v1/users/{alice['id']}/status", headers=alice["headers"]).json()
    assert status_a["online"] is False

    history_res = client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=alice["headers"],
    )
    assert history_res.status_code == 200
    history = history_res.json()
    assert history["total"] == 1
    assert history["items"][0]["message_id"] == msg_id
    assert history["items"][0]["content"] == "Hello Bob, this is real-time!"
