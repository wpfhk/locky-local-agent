"""tools/session/store.py -- SQLite DAL for session & message storage."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    provider    TEXT DEFAULT '',
    model       TEXT DEFAULT '',
    tokens_in   INTEGER DEFAULT 0,
    tokens_out  INTEGER DEFAULT 0,
    cost        REAL DEFAULT 0.0,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


class SessionStore:
    """Low-level SQLite operations for sessions and messages."""

    def __init__(self, db_path: Path | str):
        self._db_path = str(db_path)
        self._init_db()

    # -- lifecycle ---------------------------------------------------------

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # -- sessions ----------------------------------------------------------

    def create_session(
        self,
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new session. Returns session id."""
        sid = uuid.uuid4().hex[:12]
        now = _now_iso()
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (sid, title, now, now, meta_json),
            )
        return sid

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a single session by id."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List sessions, most recent first."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def update_session(self, session_id: str, **kwargs: Any) -> bool:
        """Update session fields (title, metadata)."""
        allowed = {"title", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "metadata" in updates and isinstance(updates["metadata"], dict):
            updates["metadata"] = json.dumps(updates["metadata"], ensure_ascii=False)

        sets = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [_now_iso(), session_id]

        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE sessions SET {sets}, updated_at = ? WHERE id = ?",
                values,
            )
        return cur.rowcount > 0

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        with self._conn() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0

    # -- messages ----------------------------------------------------------

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        provider: str = "",
        model: str = "",
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
    ) -> int:
        """Add a message to a session. Returns message id."""
        now = _now_iso()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO messages "
                "(session_id, role, content, provider, model, tokens_in, tokens_out, cost, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, role, content, provider, model, tokens_in, tokens_out, cost, now),
            )
            # Touch session updated_at.
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
        return cur.lastrowid  # type: ignore[return-value]

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Get all messages for a session, oldest first."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def count_messages(self, session_id: str) -> int:
        """Count messages in a session."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row["cnt"] if row else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)
