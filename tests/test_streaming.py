"""스트리밍 on_token 콜백 단위 테스트."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from actions.shell_command import run, run_fix


def _mock_stream(tokens: list[str]):
    """token 리스트를 반환하는 generator."""
    return iter(tokens)


def test_run_on_token_called():
    """on_token 콜백이 스트리밍 토큰마다 호출됩니다."""
    tokens = ["ls", " -la"]
    mock_client = MagicMock()
    mock_client.stream.return_value = _mock_stream(tokens)

    received: list[str] = []

    with patch("tools.ollama_client.OllamaClient", return_value=mock_client):
        with patch("actions.shell_command._get_code_map", return_value=""):
            run(
                Path("/tmp"),
                request="list files",
                on_token=lambda t: received.append(t),
            )

    assert received == tokens
    mock_client.stream.assert_called_once()
    mock_client.chat.assert_not_called()


def test_run_without_on_token_uses_chat():
    """on_token 없이 호출하면 chat()만 사용합니다 (기존 동작 유지)."""
    mock_client = MagicMock()
    mock_client.chat.return_value = "git status"

    with patch("tools.ollama_client.OllamaClient", return_value=mock_client):
        with patch("actions.shell_command._get_code_map", return_value=""):
            result = run(Path("/tmp"), request="show git status")

    mock_client.chat.assert_called_once()
    mock_client.stream.assert_not_called()
    assert result["status"] == "ok"


def test_run_streaming_accumulates_correctly():
    """스트리밍 토큰이 올바르게 합쳐져 유효한 명령이 추출됩니다."""
    tokens = ["gi", "t ", "sta", "tus"]
    mock_client = MagicMock()
    mock_client.stream.return_value = _mock_stream(tokens)

    with patch("tools.ollama_client.OllamaClient", return_value=mock_client):
        with patch("actions.shell_command._get_code_map", return_value=""):
            result = run(Path("/tmp"), request="git status", on_token=lambda t: None)

    assert result["status"] == "ok"
    assert result["command"] == "git status"


def test_run_keyboard_interrupt_during_stream_propagates():
    """스트리밍 중 KeyboardInterrupt가 호출자에게 전파됩니다."""

    def gen_interrupt():
        yield "git"
        raise KeyboardInterrupt

    mock_client = MagicMock()
    mock_client.stream.return_value = gen_interrupt()

    received: list[str] = []
    with patch("tools.ollama_client.OllamaClient", return_value=mock_client):
        with patch("actions.shell_command._get_code_map", return_value=""):
            with pytest.raises(KeyboardInterrupt):
                run(
                    Path("/tmp"),
                    request="git status",
                    on_token=lambda t: received.append(t),
                )

    assert "git" in received


def test_run_fix_on_token_called():
    """run_fix도 on_token 콜백을 지원합니다."""
    tokens = ["git", " status"]
    mock_client = MagicMock()
    mock_client.stream.return_value = _mock_stream(tokens)

    received: list[str] = []

    with patch("tools.ollama_client.OllamaClient", return_value=mock_client):
        with patch("actions.shell_command._get_code_map", return_value=""):
            run_fix(
                Path("/tmp"),
                request="show git status",
                failed_command="gitt status",
                error_msg="command not found",
                on_token=lambda t: received.append(t),
            )

    assert received == tokens
    mock_client.stream.assert_called_once()
    mock_client.chat.assert_not_called()
