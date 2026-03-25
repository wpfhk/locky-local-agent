"""tests/test_cli_v2_commands.py — v2 CLI 명령 통합 테스트 (8개)"""
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner
from pathlib import Path

from locky_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "code.py").write_text("x = 1\n")
    return tmp_path


def test_ask_cmd_no_ollama(runner, workspace):
    with patch("tools.ollama_guard.ensure_ollama", return_value=False):
        result = runner.invoke(cli, ["ask", "x가 뭐야?", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "Ollama" in result.output


def test_ask_cmd_with_answer(runner, workspace):
    with patch("tools.ollama_guard.ensure_ollama", return_value=True), \
         patch("tools.ollama_client.OllamaClient.chat", return_value="변수입니다"):
        result = runner.invoke(cli, ["ask", "x가 뭐야?", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "변수입니다" in result.output


def test_ask_cmd_with_file(runner, workspace):
    with patch("tools.ollama_guard.ensure_ollama", return_value=True), \
         patch("tools.ollama_client.OllamaClient.chat", return_value="정수") as mock_chat:
        result = runner.invoke(cli, ["ask", "x가 뭐야?", "code.py", "--workspace", str(workspace)])
    assert result.exit_code == 0
    # 파일 컨텍스트가 프롬프트에 포함됐는지 확인
    prompt = mock_chat.call_args[0][0][0]["content"]
    assert "x = 1" in prompt


def test_edit_cmd_file_not_found(runner, workspace):
    result = runner.invoke(cli, ["edit", "수정", "nope.py", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "파일 없음" in result.output


def test_edit_cmd_dry_run(runner, workspace):
    diff = "```diff\n--- a/code.py\n+++ b/code.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n```"
    with patch("tools.ollama_guard.ensure_ollama", return_value=True), \
         patch("tools.ollama_client.OllamaClient.chat", return_value=diff):
        result = runner.invoke(cli, ["edit", "x를 2로", "code.py", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "dry_run" in result.output


def test_agent_cmd_no_ollama(runner, workspace):
    with patch("tools.ollama_guard.ensure_ollama", return_value=False):
        result = runner.invoke(cli, ["agent", "포맷해줘", "--workspace", str(workspace)])
    assert result.exit_code == 0
    # Ollama 없으면 error 반환
    assert result.output  # 출력은 있어야 함


def test_ask_repl_command(runner, workspace):
    """REPL /ask 슬래시 명령 테스트 — PromptSession 없이 단순 임포트 확인."""
    from locky_cli.repl import help_text
    assert "/ask" in help_text
    assert "/edit" in help_text


def test_cli_commands_registered():
    """ask/edit/agent 명령이 CLI에 등록됐는지 확인."""
    assert "ask" in cli.commands
    assert "edit" in cli.commands
    assert "agent" in cli.commands
