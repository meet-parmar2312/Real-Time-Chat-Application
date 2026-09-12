import pytest
from fastapi.testclient import TestClient
from app.db.session import AsyncSessionLocal
from app.services.message import create_message


def test_paginated_message_history(client: TestClient, create_test_user):
    alice = create_test_user("alice", "alice@example.com")
    bob = create_test_user("bob", "bob@example.com")

    conv_res = client.post(
        "/api/v1/conversations",
        json={"user_id": bob["id"]},
        headers=alice["headers"],
    )
    conv_id = conv_res.json()["id"]

    import asyncio
    async def seed_messages():
        async with AsyncSessionLocal() as session:
            for i in range(15):
                sender = alice["id"] if i % 2 == 0 else bob["id"]
                await create_message(
                    db=session,
                    conversation_id=conv_id,
                    sender_id=sender,
                    content=f"Message {i + 1}",
                )

    asyncio.run(seed_messages())

    page1_res = client.get(
        f"/api/v1/conversations/{conv_id}/messages?page=1&page_size=10",
        headers=alice["headers"],
    )
    assert page1_res.status_code == 200
    p1_data = page1_res.json()
    assert p1_data["total"] == 15
    assert p1_data["page"] == 1
    assert p1_data["page_size"] == 10
    assert p1_data["total_pages"] == 2
    assert len(p1_data["items"]) == 10
    assert p1_data["items"][0]["content"] == "Message 1"
    assert p1_data["items"][9]["content"] == "Message 10"

    page2_res = client.get(
        f"/api/v1/conversations/{conv_id}/messages?page=2&page_size=10",
        headers=bob["headers"],
    )
    assert page2_res.status_code == 200
    p2_data = page2_res.json()
    assert len(p2_data["items"]) == 5
    assert p2_data["items"][0]["content"] == "Message 11"
    assert p2_data["items"][4]["content"] == "Message 15"
