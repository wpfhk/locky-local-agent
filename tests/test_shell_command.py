"""actions/shell_command.py 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from actions.shell_command import _extract_command, _is_valid_command, _scan_directory


# ── _extract_command ────────────────────────────────────────────────────────


def test_extract_plain_command():
    assert _extract_command("adb install app.aab") == "adb install app.aab"


def test_extract_strips_backtick_block():
    raw = "```bash\nadb install app.aab\n```"
    assert _extract_command(raw) == "adb install app.aab"


def test_extract_strips_inline_backtick():
    assert _extract_command("`ls -la`") == "ls -la"


def test_extract_skips_comment_lines():
    raw = "# 설치 명령\nadb install app.aab"
    assert _extract_command(raw) == "adb install app.aab"


def test_extract_first_non_empty_line():
    raw = "\n\nls -la\npwd"
    assert _extract_command(raw) == "ls -la"


# ── _is_valid_command ────────────────────────────────────────────────────────


def test_valid_adb_command():
    assert _is_valid_command("adb install app.aab") is True


def test_valid_ls_command():
    assert _is_valid_command("ls -la") is True


def test_valid_path_command():
    assert _is_valid_command("./gradlew build") is True


def test_invalid_korean_response():
    assert _is_valid_command("죄송합니다, 더 자세한 정보가 필요합니다.") is False


def test_invalid_empty_string():
    assert _is_valid_command("") is False


def test_invalid_starts_with_number():
    assert _is_valid_command("1password login") is False


# ── _scan_directory ──────────────────────────────────────────────────────────


def test_scan_directory_finds_aab(tmp_path: Path):
    (tmp_path / "app-release.aab").touch()
    (tmp_path / "README.md").touch()
    result = _scan_directory(tmp_path)
    assert "app-release.aab" in result


def test_scan_directory_empty(tmp_path: Path):
    result = _scan_directory(tmp_path)
    assert result == "(empty)"


def test_scan_directory_priority_ext_first(tmp_path: Path):
    (tmp_path / "main.py").touch()
    (tmp_path / "README.md").touch()
    result = _scan_directory(tmp_path)
    # .py 파일이 우선 표시되어야 함
    assert result.index("main.py") < result.index("README.md")


# ── run() 통합 (Ollama mock) ─────────────────────────────────────────────────


def test_run_empty_request(tmp_path: Path):
    from actions.shell_command import run
    result = run(tmp_path, request="")
    assert result["status"] == "error"
    assert result["command"] == ""


def test_run_returns_ok_with_mock(tmp_path: Path):
    from actions.shell_command import run

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "adb install app.aab"}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = run(tmp_path, request="aab 파일 설치해줘")

    assert result["status"] == "ok"
    assert result["command"] == "adb install app.aab"


def test_run_rejects_korean_response(tmp_path: Path):
    from actions.shell_command import run

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "죄송합니다, 어떤 명령인지 모르겠습니다."}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = run(tmp_path, request="뭔가 해줘")

    assert result["status"] == "error"
    assert result["command"] == ""
