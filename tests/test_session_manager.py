"""Tests for tools/session/manager.py -- SessionManager."""

from __future__ import annotations

import pytest

from tools.session.manager import SessionManager


@pytest.fixture
def mgr(tmp_path):
    """Provide a SessionManager with a temp root."""
    return SessionManager(tmp_path)


# ---------------------------------------------------------------------------
# Create & List tests
# ---------------------------------------------------------------------------


class TestCreateAndList:
    def test_create_returns_id(self, mgr):
        sid = mgr.create(title="Test")
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_list_recent_empty(self, mgr):
        assert mgr.list_recent() == []

    def test_list_recent_with_sessions(self, mgr):
        mgr.create(title="First")
        mgr.create(title="Second")
        sessions = mgr.list_recent()
        assert len(sessions) == 2
        # Each should have message_count
        for s in sessions:
            assert "message_count" in s

    def test_list_recent_limit(self, mgr):
        for i in range(5):
            mgr.create(title=f"S{i}")
        sessions = mgr.list_recent(limit=3)
        assert len(sessions) == 3


# ---------------------------------------------------------------------------
# Resume tests
# ---------------------------------------------------------------------------


class TestResume:
    def test_resume_existing(self, mgr):
        sid = mgr.create(title="Resumable")
        mgr.store.add_message(sid, "user", "Hello")
        mgr.store.add_message(sid, "assistant", "Hi")
        data = mgr.resume(sid)
        assert "session" in data
        assert "messages" in data
        assert data["session"]["id"] == sid
        assert len(data["messages"]) == 2

    def test_resume_not_found(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.resume("nonexistent")


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_markdown(self, mgr):
        sid = mgr.create(title="Export Test")
        mgr.store.add_message(sid, "user", "What is Python?")
        mgr.store.add_message(
            sid, "assistant", "A programming language.",
            provider="openai", model="gpt-4o",
            tokens_in=10, tokens_out=5,
        )
        md = mgr.export_markdown(sid)
        assert "# Session: Export Test" in md
        assert "### User" in md
        assert "### Assistant" in md
        assert "What is Python?" in md
        assert "openai" in md
        assert "gpt-4o" in md

    def test_export_not_found(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.export_markdown("nope")

    def test_export_empty_session(self, mgr):
        sid = mgr.create(title="Empty")
        md = mgr.export_markdown(sid)
        assert "Messages**: 0" in md


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_existing(self, mgr):
        sid = mgr.create(title="Deletable")
        mgr.store.add_message(sid, "user", "hi")
        assert mgr.delete(sid) is True
        assert mgr.store.get_session(sid) is None

    def test_delete_nonexistent(self, mgr):
        assert mgr.delete("nope") is False


# ---------------------------------------------------------------------------
# DB location tests
# ---------------------------------------------------------------------------


class TestDBLocation:
    def test_locky_dir_created(self, tmp_path):
        mgr = SessionManager(tmp_path)
        locky_dir = tmp_path / ".locky"
        assert locky_dir.exists()
        assert (locky_dir / "sessions.db").exists()
