"""actions/shell_command.run_fix() 단위 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_run_fix_corrects_typo(tmp_path: Path):
    """오타 명령을 교정한다."""
    from actions.shell_command import run_fix

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "git status"
        mock_cls.return_value = mock_client

        result = run_fix(
            tmp_path,
            request="git 상태 보여줘",
            failed_command="gitt status",
            error_msg="gitt: command not found",
        )

    assert result["status"] == "ok"
    assert result["command"] == "git status"


def test_run_fix_adds_sudo(tmp_path: Path):
    """권한 부족 시 sudo 추가를 제안한다."""
    from actions.shell_command import run_fix

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "sudo rm -rf /tmp/cache"
        mock_cls.return_value = mock_client

        result = run_fix(
            tmp_path,
            request="캐시 삭제해줘",
            failed_command="rm -rf /tmp/cache",
            error_msg="rm: cannot remove '/tmp/cache': Permission denied",
        )

    assert result["status"] == "ok"
    assert "sudo" in result["command"]


def test_run_fix_suggests_install(tmp_path: Path):
    """미설치 도구에 대해 설치 명령을 제안한다."""
    from actions.shell_command import run_fix

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "brew install jq"
        mock_cls.return_value = mock_client

        result = run_fix(
            tmp_path,
            request="JSON 파싱해줘",
            failed_command="jq '.name' data.json",
            error_msg="jq: command not found",
        )

    assert result["status"] == "ok"
    assert "install" in result["command"]


def test_run_fix_fixes_path(tmp_path: Path):
    """잘못된 경로를 교정한다."""
    (tmp_path / "data.csv").touch()

    from actions.shell_command import run_fix

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "cat data.csv"
        mock_cls.return_value = mock_client

        result = run_fix(
            tmp_path,
            request="데이터 파일 보여줘",
            failed_command="cat data.txt",
            error_msg="cat: data.txt: No such file or directory",
        )

    assert result["status"] == "ok"
    assert result["command"] == "cat data.csv"


def test_run_fix_rejects_korean_response(tmp_path: Path):
    """LLM이 한글 설명을 반환하면 거부한다."""
    from actions.shell_command import run_fix

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "이 명령은 수정할 수 없습니다."
        mock_cls.return_value = mock_client

        result = run_fix(
            tmp_path,
            request="뭔가 해줘",
            failed_command="bad_cmd",
            error_msg="bad_cmd: not found",
        )

    assert result["status"] == "error"


def test_run_fix_handles_connection_error(tmp_path: Path):
    """Ollama 연결 실패 시 에러를 반환한다."""
    from actions.shell_command import run_fix

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("Connection refused")
        mock_cls.return_value = mock_client

        result = run_fix(
            tmp_path,
            request="ls 해줘",
            failed_command="lss",
            error_msg="lss: not found",
        )

    assert result["status"] == "error"
    assert "교정 실패" in result["message"]


def test_run_fix_accepts_echo_cannot_fix(tmp_path: Path):
    """복구 불가능한 에러에 echo 메시지를 반환하면 유효하다."""
    from actions.shell_command import run_fix

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "echo 'Cannot fix: hardware failure'"
        mock_cls.return_value = mock_client

        result = run_fix(
            tmp_path,
            request="디스크 복구",
            failed_command="fsck /dev/sda1",
            error_msg="fsck: /dev/sda1: Device or resource busy",
        )

    assert result["status"] == "ok"
    assert "Cannot fix" in result["command"]
