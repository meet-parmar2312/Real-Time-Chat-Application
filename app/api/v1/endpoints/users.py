from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.schemas.user import UserPublic, UserStatus
from app.services.auth import get_current_user
from app.websocket.manager import manager

router = APIRouter()


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    summary="Get basic public information of a user",
)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )
    return user


@router.get(
    "/{user_id}/status",
    response_model=UserStatus,
    summary="Check real-time online/offline presence of a user",
)
async def get_user_online_status(
    user_id: int,
    current_user: User = Depends(get_current_user),
) -> UserStatus:
    online = manager.is_user_online(user_id)
    return UserStatus(user_id=user_id, online=online)
