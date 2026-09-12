import math
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message
from app.schemas.message import MessagePagination, MessageRead
from app.services.conversation import check_user_is_participant


async def create_message(
    db: AsyncSession, conversation_id: int, sender_id: int, content: str
) -> Message:
    is_member = await check_user_is_participant(db, conversation_id, sender_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to send messages to this conversation.",
        )

    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content.strip(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: int,
    user_id: int,
    page: int = 1,
    page_size: int = 50,
) -> MessagePagination:
    is_member = await check_user_is_participant(db, conversation_id, user_id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a participant in this conversation.",
        )

    count_stmt = (
        select(func.count(Message.id))
        .where(Message.conversation_id == conversation_id)
    )
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one() or 0

    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    res = await db.execute(query)
    messages = res.scalars().all()

    items = [
        MessageRead(
            message_id=m.id,
            conversation_id=m.conversation_id,
            sender_id=m.sender_id,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]

    return MessagePagination(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
