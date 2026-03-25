"""tests/test_update.py — actions/update.py 단위 테스트 (v1.1.0)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from actions.update import (_find_locky_repo, _get_version, _git_pull,
                            _reinstall, run)

# ── _get_version ───────────────────────────────────────────────────────────────


def test_get_version_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "locky-agent"\nversion = "1.1.0"\n'
    )
    assert _get_version(tmp_path) == "1.1.0"


def test_get_version_no_file(tmp_path):
    # 파일 없으면 "unknown" 반환
    assert _get_version(tmp_path) == "unknown"


def test_get_version_malformed(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
    assert _get_version(tmp_path) == "unknown"


# ── _git_pull ──────────────────────────────────────────────────────────────────


def test_git_pull_already_up_to_date(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Already up to date."
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        changed, output = _git_pull(tmp_path)
    assert changed is False
    assert "Already up to date." in output


def test_git_pull_with_changes(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "3 files changed, 42 insertions(+)"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result):
        changed, output = _git_pull(tmp_path)
    assert changed is True


def test_git_pull_failure(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "fatal: not a git repository"
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="git pull 실패"):
            _git_pull(tmp_path)


# ── _reinstall ─────────────────────────────────────────────────────────────────


def test_reinstall_pip_success(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("shutil.which", return_value=None):  # pipx 없음
        with patch("subprocess.run", return_value=mock_result):
            assert _reinstall(tmp_path) is True


def test_reinstall_pip_failure(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 1
    with patch("shutil.which", return_value=None):
        with patch("subprocess.run", return_value=mock_result):
            assert _reinstall(tmp_path) is False


# ── run() ──────────────────────────────────────────────────────────────────────


def test_run_no_repo(tmp_path):
    with patch("actions.update._find_locky_repo", return_value=None):
        result = run(tmp_path)
    assert result["status"] == "error"
    assert result["updated"] is False
    assert "git" in result["message"]


def test_run_up_to_date(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.1.0"\n')
    with patch("actions.update._find_locky_repo", return_value=tmp_path):
        with patch(
            "actions.update._git_pull", return_value=(False, "Already up to date.")
        ):
            result = run(tmp_path)
    assert result["status"] == "up_to_date"
    assert result["updated"] is False


def test_run_update_success(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.1.0"\n')
    with patch("actions.update._find_locky_repo", return_value=tmp_path):
        with patch("actions.update._git_pull", return_value=(True, "3 files changed")):
            with patch("actions.update._reinstall", return_value=True):
                result = run(tmp_path)
    assert result["status"] == "ok"
    assert result["updated"] is True


def test_run_reinstall_failure(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.1.0"\n')
    with patch("actions.update._find_locky_repo", return_value=tmp_path):
        with patch("actions.update._git_pull", return_value=(True, "files changed")):
            with patch("actions.update._reinstall", return_value=False):
                result = run(tmp_path)
    assert result["status"] == "error"
    assert result["updated"] is False


def test_run_check_only(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.1.0"\n')
    with patch("actions.update._find_locky_repo", return_value=tmp_path):
        with patch("actions.update._get_latest_remote_commit", return_value="abc123"):
            with patch("actions.update._get_current_commit", return_value="abc123"):
                result = run(tmp_path, check_only=True)
    assert result["status"] == "check"
    assert result["updated"] is False
    assert "최신 버전" in result["message"]
