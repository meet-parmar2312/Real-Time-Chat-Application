from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Conversation, ConversationParticipant, Message, User
from app.schemas.conversation import ConversationParticipantRead, ConversationRead
from app.schemas.message import MessageRead


async def get_or_create_conversation(
    db: AsyncSession, current_user_id: int, target_user_id: int
) -> Conversation:
    if current_user_id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start a conversation with yourself.",
        )

    user_stmt = select(User).where(User.id == target_user_id)
    user_res = await db.execute(user_stmt)
    target_user = user_res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {target_user_id} not found.",
        )

    stmt = (
        select(ConversationParticipant.conversation_id)
        .where(ConversationParticipant.user_id.in_([current_user_id, target_user_id]))
        .group_by(ConversationParticipant.conversation_id)
        .having(func.count(ConversationParticipant.user_id) == 2)
    )
    res = await db.execute(stmt)
    existing_conv_id = res.scalars().first()

    if existing_conv_id:
        conv_stmt = (
            select(Conversation)
            .where(Conversation.id == existing_conv_id)
            .options(
                selectinload(Conversation.participants).selectinload(ConversationParticipant.user),
                selectinload(Conversation.messages),
            )
        )
        conv_res = await db.execute(conv_stmt)
        return conv_res.scalar_one()

    new_conv = Conversation(created_at=datetime.now(timezone.utc))
    db.add(new_conv)
    await db.flush()

    p1 = ConversationParticipant(conversation_id=new_conv.id, user_id=current_user_id)
    p2 = ConversationParticipant(conversation_id=new_conv.id, user_id=target_user_id)
    db.add_all([p1, p2])
    await db.commit()

    conv_stmt = (
        select(Conversation)
        .where(Conversation.id == new_conv.id)
        .options(
            selectinload(Conversation.participants).selectinload(ConversationParticipant.user),
            selectinload(Conversation.messages),
        )
    )
    conv_res = await db.execute(conv_stmt)
    return conv_res.scalar_one()


async def check_user_is_participant(
    db: AsyncSession, conversation_id: int, user_id: int
) -> bool:
    stmt = select(ConversationParticipant).where(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_conversation_authorized(
    db: AsyncSession, conversation_id: int, user_id: int
) -> Conversation:
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.participants).selectinload(ConversationParticipant.user),
            selectinload(Conversation.messages),
        )
    )
    res = await db.execute(stmt)
    conversation = res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    is_participant = any(p.user_id == user_id for p in conversation.participants)
    if not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a participant in this conversation.",
        )

    return conversation


async def get_user_conversations(
    db: AsyncSession, user_id: int
) -> List[ConversationRead]:
    part_stmt = select(ConversationParticipant.conversation_id).where(
        ConversationParticipant.user_id == user_id
    )
    part_res = await db.execute(part_stmt)
    conv_ids = part_res.scalars().all()

    if not conv_ids:
        return []

    stmt = (
        select(Conversation)
        .where(Conversation.id.in_(conv_ids))
        .options(
            selectinload(Conversation.participants).selectinload(ConversationParticipant.user),
            selectinload(Conversation.messages),
        )
        .order_by(Conversation.created_at.desc())
    )
    res = await db.execute(stmt)
    conversations = res.scalars().all()

    result: List[ConversationRead] = []
    for conv in conversations:
        parts = [
            ConversationParticipantRead(
                user_id=p.user.id,
                username=p.user.username,
            )
            for p in conv.participants
        ]
        last_msg = None
        if conv.messages:
            lm = max(conv.messages, key=lambda m: m.created_at)
            last_msg = MessageRead(
                message_id=lm.id,
                conversation_id=lm.conversation_id,
                sender_id=lm.sender_id,
                content=lm.content,
                created_at=lm.created_at,
            )

        result.append(
            ConversationRead(
                id=conv.id,
                created_at=conv.created_at,
                participants=parts,
                last_message=last_msg,
            )
        )
    return result


async def get_other_participant_id(
    db: AsyncSession, conversation_id: int, current_user_id: int
) -> Optional[int]:
    stmt = select(ConversationParticipant.user_id).where(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id != current_user_id,
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
