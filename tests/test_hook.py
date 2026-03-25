"""actions/hook.py 단위 테스트."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from actions.hook import _HOOK_MARKER, _build_hook_script, _is_locky_hook, run

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_hooks_dir(tmp_git_repo: Path) -> Path:
    hooks_dir = tmp_git_repo / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    return hooks_dir


# ── _is_locky_hook ────────────────────────────────────────────────────────────


def test_is_locky_hook_true(tmp_path: Path):
    hook = tmp_path / "pre-commit"
    hook.write_text(f"#!/bin/sh\n{_HOOK_MARKER}\n", encoding="utf-8")
    assert _is_locky_hook(hook) is True


def test_is_locky_hook_false_other(tmp_path: Path):
    hook = tmp_path / "pre-commit"
    hook.write_text("#!/bin/sh\necho hello\n", encoding="utf-8")
    assert _is_locky_hook(hook) is False


def test_is_locky_hook_missing(tmp_path: Path):
    assert _is_locky_hook(tmp_path / "nonexistent") is False


# ── _build_hook_script ────────────────────────────────────────────────────────


def test_build_hook_includes_format(tmp_path: Path):
    script = _build_hook_script(["format"])
    assert "locky format --check" in script


def test_build_hook_includes_marker(tmp_path: Path):
    script = _build_hook_script(["format"])
    assert _HOOK_MARKER in script


def test_build_hook_skips_commit_step(tmp_path: Path):
    # commit step은 hook에서 의미 없음 — 포함되지 않아야 함
    script = _build_hook_script(["commit"])
    assert "locky commit" not in script
    assert "# (no steps configured)" in script


def test_build_hook_multiple_steps(tmp_path: Path):
    script = _build_hook_script(["format", "test", "scan"])
    assert "locky format --check" in script
    assert "locky test" in script
    assert "locky scan --severity high" in script


# ── run — not a git repo ──────────────────────────────────────────────────────


def test_run_no_git_repo(tmp_path: Path):
    result = run(tmp_path, action="install")
    assert result["status"] == "error"
    assert ".git" in result["message"]


# ── run — install ─────────────────────────────────────────────────────────────


def test_run_install_creates_hook(tmp_git_repo: Path):
    result = run(tmp_git_repo, action="install")
    assert result["status"] == "ok"
    hook = tmp_git_repo / ".git" / "hooks" / "pre-commit"
    assert hook.exists()
    assert _HOOK_MARKER in hook.read_text(encoding="utf-8")


def test_run_install_hook_is_executable(tmp_git_repo: Path):
    run(tmp_git_repo, action="install")
    hook = tmp_git_repo / ".git" / "hooks" / "pre-commit"
    assert hook.stat().st_mode & stat.S_IEXEC


def test_run_install_backs_up_existing_hook(tmp_git_repo: Path):
    hooks_dir = _make_hooks_dir(tmp_git_repo)
    existing = hooks_dir / "pre-commit"
    existing.write_text("#!/bin/sh\necho original\n", encoding="utf-8")

    result = run(tmp_git_repo, action="install")
    assert result["status"] == "ok"

    backup = hooks_dir / "pre-commit.locky-backup"
    assert backup.exists()
    assert "original" in backup.read_text(encoding="utf-8")


def test_run_install_overwrites_existing_locky_hook(tmp_git_repo: Path):
    # 이미 locky hook이면 백업 없이 덮어쓰기
    run(tmp_git_repo, action="install", steps=["format"])
    result = run(tmp_git_repo, action="install", steps=["test"])
    assert result["status"] == "ok"

    backup = tmp_git_repo / ".git" / "hooks" / "pre-commit.locky-backup"
    assert not backup.exists()


def test_run_install_custom_steps(tmp_git_repo: Path):
    result = run(tmp_git_repo, action="install", steps=["test"])
    assert result["status"] == "ok"
    hook = tmp_git_repo / ".git" / "hooks" / "pre-commit"
    assert "locky test" in hook.read_text(encoding="utf-8")


# ── run — uninstall ───────────────────────────────────────────────────────────


def test_run_uninstall_no_hook(tmp_git_repo: Path):
    result = run(tmp_git_repo, action="uninstall")
    assert result["status"] == "ok"
    assert "존재하지 않습니다" in result["message"]


def test_run_uninstall_other_hook(tmp_git_repo: Path):
    hooks_dir = _make_hooks_dir(tmp_git_repo)
    (hooks_dir / "pre-commit").write_text("#!/bin/sh\necho other\n", encoding="utf-8")

    result = run(tmp_git_repo, action="uninstall")
    assert result["status"] == "error"
    assert "locky가 설치하지 않았습니다" in result["message"]


def test_run_uninstall_removes_locky_hook(tmp_git_repo: Path):
    run(tmp_git_repo, action="install")
    result = run(tmp_git_repo, action="uninstall")
    assert result["status"] == "ok"
    assert not (tmp_git_repo / ".git" / "hooks" / "pre-commit").exists()


def test_run_uninstall_restores_backup(tmp_git_repo: Path):
    hooks_dir = _make_hooks_dir(tmp_git_repo)
    (hooks_dir / "pre-commit").write_text(
        "#!/bin/sh\necho original\n", encoding="utf-8"
    )
    run(tmp_git_repo, action="install")

    result = run(tmp_git_repo, action="uninstall")
    assert result["status"] == "ok"
    assert "복원됨" in result["message"]
    hook = hooks_dir / "pre-commit"
    assert hook.exists()
    assert "original" in hook.read_text(encoding="utf-8")


# ── run — status ──────────────────────────────────────────────────────────────


def test_run_status_not_installed(tmp_git_repo: Path):
    result = run(tmp_git_repo, action="status")
    assert result["status"] == "ok"
    assert "설치되지 않음" in result["message"]


def test_run_status_locky_installed(tmp_git_repo: Path):
    run(tmp_git_repo, action="install")
    result = run(tmp_git_repo, action="status")
    assert result["status"] == "ok"
    assert "locky hook 설치됨" in result["message"]


def test_run_status_other_hook(tmp_git_repo: Path):
    hooks_dir = _make_hooks_dir(tmp_git_repo)
    (hooks_dir / "pre-commit").write_text("#!/bin/sh\necho other\n", encoding="utf-8")
    result = run(tmp_git_repo, action="status")
    assert result["status"] == "ok"
    assert "locky 아님" in result["message"]


# ── run — invalid action ──────────────────────────────────────────────────────


def test_run_invalid_action(tmp_git_repo: Path):
    result = run(tmp_git_repo, action="bogus")
    assert result["status"] == "error"
    assert "bogus" in result["message"]
