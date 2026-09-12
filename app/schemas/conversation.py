from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserPublic
from app.schemas.message import MessageRead


class ConversationCreate(BaseModel):
    user_id: int = Field(..., description="Target user ID to start a 1-to-1 conversation with")


class ConversationParticipantRead(BaseModel):
    user_id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    id: int
    created_at: datetime
    participants: List[ConversationParticipantRead]
    last_message: Optional[MessageRead] = None

    model_config = ConfigDict(from_attributes=True)
