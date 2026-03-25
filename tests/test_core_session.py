"""tests/test_core_session.py — LockySession 테스트 (6개)"""
import pytest
from pathlib import Path
from locky.core.session import LockySession


def test_session_new(tmp_path):
    session = LockySession(workspace=tmp_path)
    assert session.session_id != ""
    assert session.history == []
    assert session.profile == "default"


def test_session_save_load(tmp_path):
    session = LockySession(workspace=tmp_path)
    session.add_history({"type": "test", "result": "ok"})

    loaded = LockySession.load(tmp_path)
    assert len(loaded.history) == 1
    assert loaded.history[0]["type"] == "test"


def test_session_history_limit(tmp_path):
    session = LockySession(workspace=tmp_path)
    for i in range(60):
        session.add_history({"type": "test", "i": i})

    loaded = LockySession.load(tmp_path)
    assert len(loaded.history) <= 50  # 최근 50개만 보존


def test_session_context_summary(tmp_path):
    session = LockySession(workspace=tmp_path)
    session.add_history({"type": "ask", "result": "ok"})
    session.add_history({"type": "edit", "result": "applied"})
    summary = session.context_summary()
    assert "ask" in summary
    assert "edit" in summary


def test_session_clear(tmp_path):
    session = LockySession(workspace=tmp_path)
    session.add_history({"type": "test", "result": "ok"})
    session.clear()
    assert session.history == []

    loaded = LockySession.load(tmp_path)
    assert loaded.history == []


def test_session_load_no_file(tmp_path):
    session = LockySession.load(tmp_path)
    assert session.session_id != ""
    assert session.history == []
