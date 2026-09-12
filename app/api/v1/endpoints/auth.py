from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import Token, UserLogin, UserRegister
from app.schemas.user import UserDetail
from app.services.auth import (
    authenticate_user,
    get_current_user,
    register_user,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> User:
    return await register_user(db=db, user_in=user_in)


@router.post(
    "/login",
    response_model=Token,
    summary="Login and obtain JWT token",
)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Token:
    email: str = ""
    password: str = ""

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username", "")
            password = body.get("password", "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )
    else:
        form_data = await request.form()
        email = str(form_data.get("username") or form_data.get("email") or "")
        password = str(form_data.get("password") or "")

    user = await authenticate_user(db=db, email=email, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
        extra_claims={"username": user.username},
    )

    return Token(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )


@router.get(
    "/me",
    response_model=UserDetail,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user
