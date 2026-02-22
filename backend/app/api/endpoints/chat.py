from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from ...db.chat_store import (
    ChatMessage,
    ChatSession,
    create_session,
    get_memory_facts,
    get_session,
    list_messages,
    list_sessions,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    seller_id: Optional[str] = Field(default=None)
    seller_name: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)


class ChatSessionResponse(BaseModel):
    session_id: str
    seller_id: Optional[str] = None
    seller_name: Optional[str] = None
    title: str
    created_at: str
    updated_at: str


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: str
    request_id: Optional[str] = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ChatMessagesResponse(BaseModel):
    session: ChatSessionResponse
    memory_facts: dict[str, str] = Field(default_factory=dict)
    messages: List[ChatMessageResponse] = Field(default_factory=list)


def _session_to_response(session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse(
        session_id=session.session_id,
        seller_id=session.seller_id,
        seller_name=session.seller_name,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _message_to_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        request_id=message.request_id,
        metadata=message.metadata,
    )


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    payload: ChatSessionCreateRequest,
) -> ChatSessionResponse:
    session = create_session(
        seller_id=payload.seller_id,
        seller_name=payload.seller_name,
        title=payload.title,
    )
    return _session_to_response(session)


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    seller_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[ChatSessionResponse]:
    sessions = list_sessions(seller_id=seller_id, limit=limit)
    return [_session_to_response(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatMessagesResponse)
async def get_chat_session_messages(
    session_id: str,
    limit: int = Query(default=200, ge=1, le=500),
) -> ChatMessagesResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = list_messages(session_id=session_id, limit=limit)
    return ChatMessagesResponse(
        session=_session_to_response(session),
        memory_facts=get_memory_facts(session_id),
        messages=[_message_to_response(m) for m in messages],
    )
