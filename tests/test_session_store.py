"""Tests for tools/session/store.py -- SQLite session storage."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tools.session.store import SessionStore


@pytest.fixture
def store(tmp_path):
    """Provide a fresh SessionStore backed by a temp SQLite DB."""
    return SessionStore(tmp_path / "test.db")


# ---------------------------------------------------------------------------
# Session CRUD tests
# ---------------------------------------------------------------------------


class TestSessionCRUD:
    def test_create_session(self, store):
        sid = store.create_session(title="Test Session")
        assert isinstance(sid, str)
        assert len(sid) == 12

    def test_get_session(self, store):
        sid = store.create_session(title="My Session")
        session = store.get_session(sid)
        assert session is not None
        assert session["id"] == sid
        assert session["title"] == "My Session"
        assert "created_at" in session
        assert "updated_at" in session

    def test_get_session_not_found(self, store):
        assert store.get_session("nonexistent") is None

    def test_list_sessions_empty(self, store):
        assert store.list_sessions() == []

    def test_list_sessions_ordering(self, store):
        s1 = store.create_session(title="First")
        s2 = store.create_session(title="Second")
        s3 = store.create_session(title="Third")
        sessions = store.list_sessions()
        # Most recent first (by updated_at)
        assert len(sessions) == 3
        ids = [s["id"] for s in sessions]
        assert ids[0] == s3  # newest first

    def test_list_sessions_limit(self, store):
        for i in range(5):
            store.create_session(title=f"Session {i}")
        sessions = store.list_sessions(limit=3)
        assert len(sessions) == 3

    def test_update_session_title(self, store):
        sid = store.create_session(title="Old")
        result = store.update_session(sid, title="New")
        assert result is True
        session = store.get_session(sid)
        assert session["title"] == "New"

    def test_update_session_metadata(self, store):
        sid = store.create_session(title="Test", metadata={"key": "val"})
        result = store.update_session(sid, metadata={"key": "updated"})
        assert result is True

    def test_update_nonexistent(self, store):
        result = store.update_session("nope", title="X")
        assert result is False

    def test_update_no_fields(self, store):
        sid = store.create_session()
        result = store.update_session(sid, invalid_field="X")
        assert result is False

    def test_delete_session(self, store):
        sid = store.create_session(title="To Delete")
        store.add_message(sid, "user", "hello")
        result = store.delete_session(sid)
        assert result is True
        assert store.get_session(sid) is None
        assert store.get_messages(sid) == []

    def test_delete_nonexistent(self, store):
        result = store.delete_session("nope")
        assert result is False

    def test_create_with_metadata(self, store):
        sid = store.create_session(title="Meta", metadata={"lang": "python"})
        session = store.get_session(sid)
        assert session is not None
        # metadata is stored as JSON string
        assert "python" in session["metadata"]


# ---------------------------------------------------------------------------
# Message CRUD tests
# ---------------------------------------------------------------------------


class TestMessageCRUD:
    def test_add_message(self, store):
        sid = store.create_session()
        mid = store.add_message(sid, "user", "Hello!")
        assert isinstance(mid, int)
        assert mid > 0

    def test_get_messages(self, store):
        sid = store.create_session()
        store.add_message(sid, "user", "Hello")
        store.add_message(sid, "assistant", "Hi there", provider="openai", model="gpt-4o")
        messages = store.get_messages(sid)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["provider"] == "openai"

    def test_get_messages_empty(self, store):
        sid = store.create_session()
        assert store.get_messages(sid) == []

    def test_count_messages(self, store):
        sid = store.create_session()
        assert store.count_messages(sid) == 0
        store.add_message(sid, "user", "one")
        store.add_message(sid, "user", "two")
        assert store.count_messages(sid) == 2

    def test_message_with_tokens(self, store):
        sid = store.create_session()
        store.add_message(
            sid, "assistant", "response",
            provider="openai", model="gpt-4o",
            tokens_in=100, tokens_out=50, cost=0.001,
        )
        msgs = store.get_messages(sid)
        assert msgs[0]["tokens_in"] == 100
        assert msgs[0]["tokens_out"] == 50
        assert msgs[0]["cost"] == pytest.approx(0.001)

    def test_message_ordering(self, store):
        sid = store.create_session()
        store.add_message(sid, "user", "first")
        store.add_message(sid, "assistant", "second")
        store.add_message(sid, "user", "third")
        msgs = store.get_messages(sid)
        contents = [m["content"] for m in msgs]
        assert contents == ["first", "second", "third"]

    def test_add_message_touches_session(self, store):
        sid = store.create_session()
        before = store.get_session(sid)["updated_at"]
        import time
        time.sleep(0.01)
        store.add_message(sid, "user", "update me")
        after = store.get_session(sid)["updated_at"]
        assert after >= before


# ---------------------------------------------------------------------------
# DB init / idempotency tests
# ---------------------------------------------------------------------------


class TestDBInit:
    def test_db_created(self, tmp_path):
        db_path = tmp_path / "new.db"
        assert not db_path.exists()
        store = SessionStore(db_path)
        assert db_path.exists()

    def test_init_idempotent(self, tmp_path):
        db_path = tmp_path / "idem.db"
        store1 = SessionStore(db_path)
        sid = store1.create_session(title="test")
        # Re-init same DB
        store2 = SessionStore(db_path)
        session = store2.get_session(sid)
        assert session is not None
        assert session["title"] == "test"
