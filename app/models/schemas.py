from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class SessionStartRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)


class SessionResponse(BaseModel):
    session_id: UUID
    expires_at: datetime


class ChatRequest(BaseModel):
    session_id: UUID
    message: str = Field(min_length=1, max_length=8000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("message cannot be empty")
        return value


class ActionResponse(BaseModel):
    message: str
    action: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(ActionResponse):
    session_id: UUID
    correlation_id: str


class ActionPlan(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    action: Literal["OPEN_HOTEL_MODULE", "OPEN_PET_PROFILE", "CONTACT_SUPPORT"] | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class MarkdownDocument(BaseModel):
    document_name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=2_000_000)


class IngestResponse(BaseModel):
    document_name: str
    chunks: int
