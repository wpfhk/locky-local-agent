"""tests/test_agents_edit.py — EditAgent 테스트 (6개)"""

from pathlib import Path
from unittest.mock import patch

import pytest

from locky.agents.edit_agent import EditAgent
from locky.core.session import LockySession


@pytest.fixture
def session(tmp_path):
    return LockySession(workspace=tmp_path)


def test_edit_agent_file_not_found(session):
    agent = EditAgent(session)
    result = agent.run("수정해줘", file_path="nonexistent.py")
    assert result["status"] == "error"
    assert "파일 없음" in result["message"]


def test_edit_agent_path_traversal(session):
    agent = EditAgent(session)
    result = agent.run("수정해줘", file_path="../etc/passwd")
    assert result["status"] == "error"
    assert "경로 접근 거부" in result["message"]


def test_edit_agent_no_ollama(tmp_path):
    (tmp_path / "code.py").write_text("x = 1\n")
    session = LockySession(workspace=tmp_path)
    with patch("tools.ollama_guard.ensure_ollama", return_value=False):
        agent = EditAgent(session)
        result = agent.run("x를 2로 바꿔", file_path="code.py")
    assert result["status"] == "error"
    assert "Ollama" in result["message"]


def test_edit_agent_dry_run(tmp_path):
    (tmp_path / "code.py").write_text("x = 1\n")
    session = LockySession(workspace=tmp_path)
    diff_block = (
        "```diff\n--- a/code.py\n+++ b/code.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n```"
    )
    with (
        patch("tools.ollama_guard.ensure_ollama", return_value=True),
        patch("tools.ollama_client.OllamaClient.stream", return_value=[diff_block]),
    ):
        agent = EditAgent(session)
        result = agent.run("x를 2로 바꿔", file_path="code.py", dry_run=True)
    assert result["status"] == "dry_run"
    assert result["applied"] is False
    assert "--- a/code.py" in result["diff"]


def test_edit_agent_extract_diff_fallback(tmp_path):
    (tmp_path / "code.py").write_text("x = 1\n")
    session = LockySession(workspace=tmp_path)
    # diff 파싱 불가능한 응답
    with (
        patch("tools.ollama_guard.ensure_ollama", return_value=True),
        patch("tools.ollama_client.OllamaClient.stream", return_value=["그냥 텍스트 응답"]),
    ):
        agent = EditAgent(session)
        result = agent.run("수정해줘", file_path="code.py", dry_run=True)
    assert result["status"] == "dry_run"
    assert "파싱 실패" in result["message"]


def test_edit_agent_extract_diff_patterns(tmp_path):
    session = LockySession(workspace=tmp_path)
    agent = EditAgent(session)

    # ```diff 블록 패턴
    response1 = "설명\n```diff\n--- a/foo\n+++ b/foo\n@@ -1 +1 @@\n-old\n+new\n```"
    assert "--- a/foo" in agent._extract_diff(response1)

    # diff 없는 응답
    assert agent._extract_diff("그냥 텍스트") == ""
