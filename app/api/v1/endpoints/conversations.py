from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationParticipantRead,
    ConversationRead,
)
from app.schemas.message import MessagePagination, MessageRead
from app.services.auth import get_current_user
from app.services.conversation import (
    get_conversation_authorized,
    get_or_create_conversation,
    get_user_conversations,
)
from app.services.message import get_conversation_messages

router = APIRouter()


@router.post(
    "",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or retrieve a one-to-one conversation",
)
async def create_conversation(
    conv_in: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationRead:
    conv = await get_or_create_conversation(
        db=db,
        current_user_id=current_user.id,
        target_user_id=conv_in.user_id,
    )
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

    return ConversationRead(
        id=conv.id,
        created_at=conv.created_at,
        participants=parts,
        last_message=last_msg,
    )


@router.get(
    "",
    response_model=List[ConversationRead],
    summary="List all conversations for the authenticated user",
)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ConversationRead]:
    return await get_user_conversations(db=db, user_id=current_user.id)


@router.get(
    "/{conversation_id}",
    response_model=ConversationRead,
    summary="Get conversation details by ID",
)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationRead:
    conv = await get_conversation_authorized(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
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

    return ConversationRead(
        id=conv.id,
        created_at=conv.created_at,
        participants=parts,
        last_message=last_msg,
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=MessagePagination,
    summary="Get paginated, chronologically ordered message history",
)
async def get_messages(
    conversation_id: int,
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(50, ge=1, le=100, description="Number of messages per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessagePagination:
    return await get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
