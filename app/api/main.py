"""
FastAPI REST API for the RAG chatbot with human handoff.

Endpoints:
    POST /chat                 - send a user message, get AI answer (or note that a human will respond)
    POST /handoff              - transfer a conversation to a human agent
    POST /handoff/resume       - switch a conversation back to AI mode
    GET  /status/{conversation_id} - get current status (ai/human) of a conversation
    GET  /messages/{conversation_id} - get full message history
    GET  /conversations        - list all conversations (for the agent dashboard)
    POST /agent/reply          - human agent sends a reply to the user
    POST /ingest                - upload and ingest PDF documents into the knowledge base
    GET  /kb/stats              - knowledge base stats (chunk count, sources)
    DELETE /kb                  - clear the knowledge base
    GET  /health                - health check
"""

import os
import shutil
import tempfile
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import database as db
from app.core import rag_pipeline
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    HandoffRequest,
    StatusResponse,
    AgentReplyRequest,
    MessageOut,
    ConversationOut,
    IngestResult,
    KBStats,
)

app = FastAPI(
    title="RAG Chatbot with Human Handoff API",
    description="Simple RAG chatbot backend with PDF ingestion and human handoff support.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Submit a user message.
    - If the conversation is in 'ai' mode, the RAG pipeline generates and returns an answer.
    - If the conversation is in 'human' mode, the message is stored for the agent and
      no AI answer is generated; the caller should poll /messages for the agent's reply.
    """
    db.create_conversation(req.conversation_id)
    conv = db.get_conversation(req.conversation_id)

    db.add_message(req.conversation_id, "user", req.message)

    if conv["status"] == "human":
        return ChatResponse(
            conversation_id=req.conversation_id,
            responder="human_pending",
            answer=None,
            sources=[],
            status="human",
        )

    try:
        result = rag_pipeline.answer_query(req.message)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    db.add_message(req.conversation_id, "ai", result["answer"])

    return ChatResponse(
        conversation_id=req.conversation_id,
        responder="ai",
        answer=result["answer"],
        sources=result["sources"],
        status="ai",
    )


@app.post("/handoff", response_model=StatusResponse)
def handoff(req: HandoffRequest):
    """Transfer a conversation from AI to a human agent."""
    db.create_conversation(req.conversation_id)
    db.set_conversation_status(req.conversation_id, "human")
    return StatusResponse(conversation_id=req.conversation_id, status="human")


@app.post("/handoff/resume", response_model=StatusResponse)
def resume_ai(req: HandoffRequest):
    """Switch a conversation back to AI mode."""
    db.create_conversation(req.conversation_id)
    db.set_conversation_status(req.conversation_id, "ai")
    return StatusResponse(conversation_id=req.conversation_id, status="ai")


@app.get("/status/{conversation_id}", response_model=StatusResponse)
def get_status(conversation_id: str):
    conv = db.get_conversation(conversation_id)
    if not conv:
        db.create_conversation(conversation_id)
        conv = db.get_conversation(conversation_id)
    return StatusResponse(conversation_id=conversation_id, status=conv["status"])


@app.get("/messages/{conversation_id}", response_model=List[MessageOut])
def get_messages(conversation_id: str):
    db.create_conversation(conversation_id)
    msgs = db.get_messages(conversation_id)
    return [MessageOut(**m) for m in msgs]


@app.get("/conversations", response_model=List[ConversationOut])
def list_conversations():
    return [ConversationOut(**c) for c in db.list_conversations()]


@app.post("/agent/reply", response_model=MessageOut)
def agent_reply(req: AgentReplyRequest):
    """Human agent sends a message directly to the user."""
    conv = db.get_conversation(req.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv["status"] != "human":
        raise HTTPException(
            status_code=400,
            detail="Conversation is not in human handoff mode. Call /handoff first.",
        )
    db.add_message(req.conversation_id, "agent", req.message)
    msgs = db.get_messages(req.conversation_id)
    return MessageOut(**msgs[-1])


@app.post("/ingest", response_model=IngestResult)
async def ingest_documents(files: List[UploadFile] = File(...)):
    """Upload one or more PDF files to be ingested into the RAG knowledge base."""
    tmp_dir = tempfile.mkdtemp()
    saved_paths = []
    try:
        for f in files:
            if not f.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail=f"{f.filename} is not a PDF file."
                )
            dest = os.path.join(tmp_dir, f.filename)
            with open(dest, "wb") as out:
                shutil.copyfileobj(f.file, out)
            saved_paths.append(dest)

        results = rag_pipeline.ingest_pdfs(saved_paths)
        return IngestResult(files_processed=results)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.get("/kb/stats", response_model=KBStats)
def kb_stats():
    stats = rag_pipeline.vector_store_stats()
    return KBStats(**stats)


@app.delete("/kb")
def clear_kb():
    rag_pipeline.clear_knowledge_base()
    return {"status": "cleared"}
