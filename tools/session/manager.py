"""tools/session/manager.py -- High-level session lifecycle management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .store import SessionStore


class SessionManager:
    """Manages session lifecycle on top of SessionStore.

    DB file lives at ``{root}/.locky/sessions.db``.
    """

    def __init__(self, root: Path):
        self._root = Path(root).resolve()
        locky_dir = self._root / ".locky"
        locky_dir.mkdir(exist_ok=True)
        self._store = SessionStore(locky_dir / "sessions.db")

    @property
    def store(self) -> SessionStore:
        return self._store

    # -- public API --------------------------------------------------------

    def create(self, title: str = "") -> str:
        """Create a new session and return its id."""
        return self._store.create_session(title=title)

    def resume(self, session_id: str) -> dict[str, Any]:
        """Load session + messages for resumption.

        Returns:
            {"session": dict, "messages": list[dict]}

        Raises:
            ValueError if session not found.
        """
        session = self._store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        messages = self._store.get_messages(session_id)
        return {"session": session, "messages": messages}

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent sessions with message counts."""
        sessions = self._store.list_sessions(limit=limit)
        for s in sessions:
            s["message_count"] = self._store.count_messages(s["id"])
        return sessions

    def export_markdown(self, session_id: str) -> str:
        """Export a session as a markdown document."""
        session = self._store.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        messages = self._store.get_messages(session_id)

        lines = [
            f"# Session: {session.get('title') or session['id']}",
            "",
            f"- **ID**: {session['id']}",
            f"- **Created**: {session['created_at']}",
            f"- **Updated**: {session['updated_at']}",
            f"- **Messages**: {len(messages)}",
            "",
            "---",
            "",
        ]

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            provider = msg.get("provider", "")
            model = msg.get("model", "")
            tokens_in = msg.get("tokens_in", 0)
            tokens_out = msg.get("tokens_out", 0)

            role_label = {"user": "User", "assistant": "Assistant", "system": "System"}.get(
                role, role.capitalize()
            )
            lines.append(f"### {role_label}")
            if provider:
                meta_parts = [f"{provider}/{model}" if model else provider]
                if tokens_in or tokens_out:
                    meta_parts.append(f"{tokens_in} in / {tokens_out} out")
                lines.append(f"*{' | '.join(meta_parts)}*")
            lines.append("")
            lines.append(content)
            lines.append("")

        return "\n".join(lines)

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        return self._store.delete_session(session_id)
