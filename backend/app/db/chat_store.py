from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional


CHAT_DB_PATH = Path("app_storage/chat_sessions.sqlite3")


@dataclass
class ChatSession:
    session_id: str
    seller_id: Optional[str]
    seller_name: Optional[str]
    title: str
    created_at: str
    updated_at: str


@dataclass
class ChatMessage:
    id: int
    session_id: str
    role: str
    content: str
    created_at: str
    request_id: Optional[str]
    metadata: Dict[str, object]


def _ensure_parent_dir() -> None:
    CHAT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    _ensure_parent_dir()
    conn = sqlite3.connect(str(CHAT_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_chat_store() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                seller_id TEXT,
                seller_name TEXT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                request_id TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS chat_memory_facts (
                session_id TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(session_id, fact_key),
                FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
            );
            """
        )
        cols = {
            str(r["name"])
            for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
        }
        if "metadata_json" not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN metadata_json TEXT")
        conn.commit()


def create_session(
    seller_id: Optional[str] = None,
    seller_name: Optional[str] = None,
    title: Optional[str] = None,
) -> ChatSession:
    init_chat_store()
    session_id = uuid.uuid4().hex
    session_title = title or "Seller chat"
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions(session_id, seller_id, seller_name, title)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, seller_id, seller_name, session_title),
        )
        conn.commit()
    return get_session(session_id)


def ensure_session(
    session_id: str,
    seller_id: Optional[str] = None,
    seller_name: Optional[str] = None,
) -> ChatSession:
    init_chat_store()
    existing = get_session(session_id)
    if existing is not None:
        if seller_name and seller_name != existing.seller_name:
            update_session_seller_name(session_id, seller_name)
            existing = get_session(session_id)
        return existing

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions(session_id, seller_id, seller_name, title)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, seller_id, seller_name, "Seller chat"),
        )
        conn.commit()
    return get_session(session_id)


def update_session_seller_name(session_id: str, seller_name: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE chat_sessions
            SET seller_name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (seller_name, session_id),
        )
        conn.commit()


def get_session(session_id: str) -> Optional[ChatSession]:
    init_chat_store()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT session_id, seller_id, seller_name, title, created_at, updated_at
            FROM chat_sessions
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
    if row is None:
        return None
    return ChatSession(
        session_id=row["session_id"],
        seller_id=row["seller_id"],
        seller_name=row["seller_name"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_sessions(seller_id: Optional[str] = None, limit: int = 50) -> List[ChatSession]:
    init_chat_store()
    with _connect() as conn:
        if seller_id:
            rows = conn.execute(
                """
                SELECT session_id, seller_id, seller_name, title, created_at, updated_at
                FROM chat_sessions
                WHERE seller_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (seller_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT session_id, seller_id, seller_name, title, created_at, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [
        ChatSession(
            session_id=row["session_id"],
            seller_id=row["seller_id"],
            seller_name=row["seller_name"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


def add_message(
    session_id: str,
    role: str,
    content: str,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, object]] = None,
) -> ChatMessage:
    init_chat_store()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO chat_messages(session_id, role, content, request_id, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                content,
                request_id,
                json.dumps(metadata or {}, ensure_ascii=True),
            ),
        )
        conn.execute(
            """
            UPDATE chat_sessions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (session_id,),
        )
        conn.commit()
        message_id = int(cur.lastrowid)

    return get_message(message_id)


def get_message(message_id: int) -> ChatMessage:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, session_id, role, content, created_at, request_id, metadata_json
            FROM chat_messages
            WHERE id = ?
            """,
            (message_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"Message not found: {message_id}")
    return ChatMessage(
        id=int(row["id"]),
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"],
        request_id=row["request_id"],
        metadata=(
            json.loads(row["metadata_json"])
            if row["metadata_json"]
            else {}
        ),
    )


def list_messages(session_id: str, limit: int = 100) -> List[ChatMessage]:
    init_chat_store()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, created_at, request_id, metadata_json
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    return [
        ChatMessage(
            id=int(row["id"]),
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
            request_id=row["request_id"],
            metadata=(
                json.loads(row["metadata_json"])
                if row["metadata_json"]
                else {}
            ),
        )
        for row in rows
    ]


def get_recent_turns(session_id: str, limit_pairs: int = 3) -> List[str]:
    messages = list_messages(session_id, limit=limit_pairs * 2 + 2)
    if not messages:
        return []
    turns: List[str] = []
    for msg in messages[-(limit_pairs * 2) :]:
        turns.append(f"{msg.role}: {msg.content}")
    return turns


def upsert_memory_fact(session_id: str, fact_key: str, fact_value: str) -> None:
    init_chat_store()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_memory_facts(session_id, fact_key, fact_value)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, fact_key)
            DO UPDATE SET
                fact_value = excluded.fact_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session_id, fact_key, fact_value),
        )
        conn.execute(
            """
            UPDATE chat_sessions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (session_id,),
        )
        conn.commit()


def get_memory_facts(session_id: str) -> Dict[str, str]:
    init_chat_store()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT fact_key, fact_value
            FROM chat_memory_facts
            WHERE session_id = ?
            ORDER BY fact_key ASC
            """,
            (session_id,),
        ).fetchall()
    return {str(row["fact_key"]): str(row["fact_value"]) for row in rows}
