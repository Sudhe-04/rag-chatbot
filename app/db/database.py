"""
SQLite-backed storage for conversations and messages.

Schema:
    conversations(id, status, created_at, updated_at)
        status: 'ai' or 'human'  -> who is currently responsible for replying
    messages(id, conversation_id, sender, content, created_at)
        sender: 'user' | 'ai' | 'agent'
"""

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("CHATBOT_DB_PATH", "/app/data/conversations.db")

_lock = threading.Lock()


def _init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'ai',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def create_conversation(conversation_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO conversations (id, status, created_at, updated_at) VALUES (?, 'ai', ?, ?)",
            (conversation_id, now_iso(), now_iso()),
        )


def get_conversation(conversation_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return dict(row) if row else None


def list_conversations():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def set_conversation_status(conversation_id: str, status: str):
    assert status in ("ai", "human")
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_iso(), conversation_id),
        )


def add_message(conversation_id: str, sender: str, content: str):
    assert sender in ("user", "ai", "agent")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, sender, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, sender, content, now_iso()),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now_iso(), conversation_id),
        )


def get_messages(conversation_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]


_init_db()
