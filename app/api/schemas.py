from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    responder: str  # "ai" or "human_pending"
    answer: Optional[str] = None
    sources: List[str] = []
    status: str  # "ai" or "human"


class HandoffRequest(BaseModel):
    conversation_id: str


class StatusResponse(BaseModel):
    conversation_id: str
    status: str


class AgentReplyRequest(BaseModel):
    conversation_id: str
    message: str


class MessageOut(BaseModel):
    id: int
    sender: str
    content: str
    created_at: str


class ConversationOut(BaseModel):
    id: str
    status: str
    created_at: str
    updated_at: str


class IngestResult(BaseModel):
    files_processed: dict


class KBStats(BaseModel):
    total_chunks: int
    sources: List[str]
