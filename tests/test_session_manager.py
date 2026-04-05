"""tools/session_manager.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path

from tools.session_manager import SessionManager


def test_record_and_get_recent(tmp_path: Path):
    mgr = SessionManager(tmp_path)
    mgr.record("파일 목록", "ls -la", 0, stdout="file1.py\nfile2.py")

    recent = mgr.get_recent(5)
    assert len(recent) == 1
    assert recent[0]["request"] == "파일 목록"
    assert recent[0]["command"] == "ls -la"
    assert recent[0]["exit_code"] == 0


def test_persistence(tmp_path: Path):
    """세션 파일이 영속화되고 재로드된다."""
    mgr1 = SessionManager(tmp_path)
    mgr1.record("git status", "git status", 0, stdout="clean")

    # 새 인스턴스로 재로드
    mgr2 = SessionManager(tmp_path)
    assert len(mgr2.entries) == 1
    assert mgr2.entries[0]["command"] == "git status"


def test_max_entries_limit(tmp_path: Path):
    mgr = SessionManager(tmp_path, max_entries=3)
    for i in range(5):
        mgr.record(f"req{i}", f"cmd{i}", 0)

    assert len(mgr.entries) == 3
    assert mgr.entries[0]["request"] == "req2"
    assert mgr.entries[-1]["request"] == "req4"


def test_clear(tmp_path: Path):
    mgr = SessionManager(tmp_path)
    mgr.record("test", "echo test", 0)
    assert len(mgr.entries) == 1

    mgr.clear()
    assert len(mgr.entries) == 0

    # 파일도 비워졌는지 확인
    reloaded = SessionManager(tmp_path)
    assert len(reloaded.entries) == 0


def test_format_context_empty(tmp_path: Path):
    mgr = SessionManager(tmp_path)
    assert mgr.format_context() == ""


def test_format_context_with_entries(tmp_path: Path):
    mgr = SessionManager(tmp_path)
    mgr.record("파일 만들기", "touch test.txt", 0)
    mgr.record("파일 삭제", "rm test.txt", 0)

    ctx = mgr.format_context()
    assert "Previous actions:" in ctx
    assert "touch test.txt" in ctx
    assert "rm test.txt" in ctx
    assert "[ok]" in ctx


def test_format_context_shows_error(tmp_path: Path):
    mgr = SessionManager(tmp_path)
    mgr.record("잘못된 명령", "gitt status", 127, stderr="command not found")

    ctx = mgr.format_context()
    assert "[error]" in ctx
    assert "gitt status" in ctx
    assert "command not found" in ctx


def test_format_context_limits_to_n(tmp_path: Path):
    mgr = SessionManager(tmp_path)
    for i in range(10):
        mgr.record(f"req{i}", f"cmd{i}", 0)

    ctx = mgr.format_context(n=3)
    assert "cmd7" in ctx
    assert "cmd8" in ctx
    assert "cmd9" in ctx
    assert "cmd0" not in ctx


def test_output_truncation(tmp_path: Path):
    mgr = SessionManager(tmp_path)
    long_output = "x" * 500
    mgr.record("test", "echo x", 0, stdout=long_output)

    assert len(mgr.entries[0]["output"]) == 200


def test_stderr_recorded_when_no_stdout(tmp_path: Path):
    mgr = SessionManager(tmp_path)
    mgr.record("bad cmd", "bad", 1, stdout="", stderr="not found")

    assert mgr.entries[0]["output"] == "not found"
