import logging
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.auth import get_user_from_token_ws
from app.services.conversation import (
    check_user_is_participant,
    get_other_participant_id,
)
from app.services.message import create_message
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/conversations/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: Optional[str] = Query(None),
) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_from_token_ws(token=token, db=session)
        if not user:
            logger.warning("WebSocket rejected: Invalid or missing JWT token.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        is_participant = await check_user_is_participant(
            db=session,
            conversation_id=conversation_id,
            user_id=user.id,
        )
        if not is_participant:
            logger.warning(
                f"WebSocket rejected: User {user.id} is not authorized for conversation {conversation_id}."
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await manager.connect(websocket, conversation_id, user.id)

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content")
            if not content or not isinstance(content, str) or not content.strip():
                await manager.send_personal_message(
                    {
                        "event": "error",
                        "detail": "Message 'content' must be a non-empty string.",
                    },
                    websocket,
                )
                continue

            content = content.strip()

            async with AsyncSessionLocal() as session:
                db_message = await create_message(
                    db=session,
                    conversation_id=conversation_id,
                    sender_id=user.id,
                    content=content,
                )
                recipient_id = await get_other_participant_id(
                    db=session,
                    conversation_id=conversation_id,
                    current_user_id=user.id,
                )

            message_payload = {
                "message_id": db_message.id,
                "conversation_id": db_message.conversation_id,
                "sender_id": db_message.sender_id,
                "content": db_message.content,
                "created_at": db_message.created_at.isoformat(),
            }

            if recipient_id is not None:
                await manager.send_to_user(recipient_id, message_payload)

            ack_payload = {
                "event": "ack",
                "message_id": db_message.id,
                "conversation_id": db_message.conversation_id,
                "status": "delivered",
                "created_at": db_message.created_at.isoformat(),
            }
            await manager.send_personal_message(ack_payload, websocket)

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as exc:
        logger.error(f"WebSocket session terminated with error: {exc}")
        await manager.disconnect(websocket)
