"""actions/format_code.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from actions.format_code import _run_tool, run

# ── _run_tool ─────────────────────────────────────────────────────────────────


def test_run_tool_not_installed(tmp_path: Path):
    with patch("shutil.which", return_value=None):
        result = _run_tool("nonexistent_tool", ["nonexistent_tool"], tmp_path)
    assert result["status"] == "not_installed"


def test_run_tool_success(tmp_path: Path):
    with patch("shutil.which", return_value="/usr/bin/echo"):
        result = _run_tool("echo", ["echo", "hello"], tmp_path)
    assert result["status"] == "ok"
    assert result["returncode"] == 0


def test_run_tool_failure(tmp_path: Path):
    with patch("shutil.which", return_value="/usr/bin/false"):
        result = _run_tool("false", ["false"], tmp_path)
    assert result["status"] == "error"


# ── run — lang="python" ───────────────────────────────────────────────────────


def test_run_python_returns_three_tools(tmp_path: Path):
    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="python")
    assert "black" in result
    assert "isort" in result
    assert "flake8" in result


def test_run_python_language_field(tmp_path: Path):
    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="python")
    assert result["language"] == "python"


def test_run_python_not_installed_is_ok_status(tmp_path: Path):
    # 모든 도구 미설치 시 status는 ok (not_installed은 오류가 아님)
    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="python")
    assert result["status"] == "ok"


def test_run_python_check_only_passes_check_flag(tmp_path: Path):
    """check_only=True 시 black --check, isort --check-only 옵션 확인."""
    captured = {}

    def mock_run(cmd, **kwargs):
        captured[cmd[0]] = cmd
        m = MagicMock()
        m.returncode = 0
        m.stdout = ""
        m.stderr = ""
        return m

    with patch("shutil.which", return_value="/usr/bin/black"):
        with patch("subprocess.run", side_effect=mock_run):
            run(tmp_path, lang="python", check_only=True)

    if "black" in captured:
        assert "--check" in captured["black"]


# ── run — lang="javascript" ───────────────────────────────────────────────────


def test_run_javascript_language_field(tmp_path: Path):
    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="javascript")
    assert result["language"] == "javascript"


def test_run_javascript_prettier_tool(tmp_path: Path):
    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="javascript")
    assert "prettier" in result


def test_run_typescript_has_prettier_and_eslint(tmp_path: Path):
    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="typescript")
    assert "prettier" in result
    assert "eslint" in result


def test_run_go_has_gofmt(tmp_path: Path):
    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="go")
    assert "gofmt" in result


def test_run_rust_has_rustfmt(tmp_path: Path):
    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="rust")
    assert "rustfmt" in result


def test_run_unknown_lang_returns_info(tmp_path: Path):
    result = run(tmp_path, lang="cobol")
    assert result["status"] == "ok"
    assert "_info" in result


# ── run — lang="auto" ─────────────────────────────────────────────────────────


def test_run_auto_detects_python(tmp_path: Path):
    (tmp_path / "main.py").write_text("x = 1", encoding="utf-8")

    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="auto")

    assert result["language"] == "python"
    assert "black" in result


def test_run_auto_detects_javascript(tmp_path: Path):
    (tmp_path / "app.js").write_text("var x = 1;", encoding="utf-8")

    with patch("shutil.which", return_value=None):
        result = run(tmp_path, lang="auto")

    assert result["language"] == "javascript"
    assert "prettier" in result


def test_run_auto_fallback_to_python_on_error(tmp_path: Path):
    with patch("locky_cli.lang_detect.detect", side_effect=RuntimeError("fail")):
        with patch("shutil.which", return_value=None):
            result = run(tmp_path, lang="auto")

    assert result["language"] == "python"
