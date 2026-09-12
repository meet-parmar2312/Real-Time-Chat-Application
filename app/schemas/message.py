from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Message text content")


class MessageRead(BaseModel):
    message_id: str
    conversation_id: int
    sender_id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MessagePagination(BaseModel):
    items: List[MessageRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class WSAck(BaseModel):
    event: str = "ack"
    message_id: str
    conversation_id: int
    status: str = "delivered"
    created_at: datetime


class WSError(BaseModel):
    event: str = "error"
    detail: str
