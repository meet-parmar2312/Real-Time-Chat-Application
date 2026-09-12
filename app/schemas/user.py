from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPublic(UserBase):
    pass


class UserDetail(UserBase):
    email: EmailStr


class UserStatus(BaseModel):
    user_id: int
    online: bool
