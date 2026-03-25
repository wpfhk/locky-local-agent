"""tests/test_agents_ask.py — AskAgent 테스트 (4개)"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from locky.agents.ask_agent import AskAgent
from locky.core.session import LockySession


@pytest.fixture
def session(tmp_path):
    return LockySession(workspace=tmp_path)


def test_ask_agent_no_ollama(session):
    with patch("tools.ollama_guard.ensure_ollama", return_value=False):
        agent = AskAgent(session)
        answer = agent.run("이 코드가 뭐야?")
    assert "Ollama" in answer


def test_ask_agent_run_ok(session):
    with (
        patch("tools.ollama_guard.ensure_ollama", return_value=True),
        patch("tools.ollama_client.OllamaClient.chat", return_value="함수입니다"),
    ):
        agent = AskAgent(session)
        answer = agent.run("이 코드가 뭐야?")
    assert answer == "함수입니다"


def test_ask_agent_with_files(tmp_path):
    (tmp_path / "foo.py").write_text("def bar(): pass\n")
    session = LockySession(workspace=tmp_path)
    with (
        patch("tools.ollama_guard.ensure_ollama", return_value=True),
        patch(
            "tools.ollama_client.OllamaClient.chat", return_value="bar 함수"
        ) as mock_chat,
    ):
        agent = AskAgent(session)
        answer = agent.run("bar가 뭐야?", files=["foo.py"])
    # 파일 컨텍스트가 프롬프트에 포함됐는지 확인
    call_args = mock_chat.call_args
    assert "bar" in call_args[0][0][0]["content"]
    assert answer == "bar 함수"


def test_ask_agent_records_history(session):
    with (
        patch("tools.ollama_guard.ensure_ollama", return_value=True),
        patch("tools.ollama_client.OllamaClient.chat", return_value="답변"),
    ):
        agent = AskAgent(session)
        agent.run("질문입니다")
    assert len(session.history) == 1
    assert session.history[0]["type"] == "ask"


def test_ask_agent_stream_no_ollama(session):
    with patch("tools.ollama_guard.ensure_ollama", return_value=False):
        agent = AskAgent(session)
        tokens = list(agent.stream("질문"))
    assert any("Ollama" in t for t in tokens)


def test_ask_agent_stream_yields_tokens(session):
    def fake_stream(self, messages, system=""):
        yield "토큰1"
        yield "토큰2"

    with (
        patch("tools.ollama_guard.ensure_ollama", return_value=True),
        patch("tools.ollama_client.OllamaClient.stream", fake_stream),
    ):
        agent = AskAgent(session)
        tokens = list(agent.stream("질문"))
    assert tokens == ["토큰1", "토큰2"]
