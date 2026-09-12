from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["alice"])
    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., min_length=6, max_length=128, examples=["secretpassword123"])


class UserLogin(BaseModel):
    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., min_length=1, examples=["secretpassword123"])


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class TokenPayload(BaseModel):
    sub: str | None = None
    exp: int | None = None
    iat: int | None = None
