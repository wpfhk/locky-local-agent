"""actions/hook.py — git pre-commit hook 설치·제거·상태 확인."""

from __future__ import annotations

import shutil
import stat
from pathlib import Path

_HOOK_FILENAME = "pre-commit"
_BACKUP_SUFFIX = ".locky-backup"
_HOOK_MARKER = "# locky pre-commit hook"

_HOOK_TEMPLATE = """\
#!/bin/sh
{marker}
# 자동 설치됨. 제거하려면: locky hook uninstall
set -e

{steps}
"""

_STEP_COMMANDS: dict[str, str] = {
    "format": "locky format --check",
    "test": "locky test",
    "scan": "locky scan --severity high",
    "commit": "",  # hook에서 commit은 의미 없음 — 무시
}


def _git_hooks_dir(root: Path) -> Path | None:
    """`.git/hooks` 경로를 반환합니다. git 레포가 아니면 None."""
    git_dir = root / ".git"
    if not git_dir.is_dir():
        return None
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    return hooks_dir


def _hook_path(hooks_dir: Path) -> Path:
    return hooks_dir / _HOOK_FILENAME


def _backup_path(hooks_dir: Path) -> Path:
    return hooks_dir / (_HOOK_FILENAME + _BACKUP_SUFFIX)


def _is_locky_hook(path: Path) -> bool:
    try:
        return _HOOK_MARKER in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _build_hook_script(steps: list[str]) -> str:
    lines = []
    for step in steps:
        cmd = _STEP_COMMANDS.get(step)
        if cmd:  # empty string (commit) 무시
            lines.append(cmd)
    return _HOOK_TEMPLATE.format(
        marker=_HOOK_MARKER,
        steps="\n".join(lines) if lines else "# (no steps configured)",
    )


def run(
    root: Path,
    action: str = "install",
    steps: list[str] | None = None,
    **opts,
) -> dict:
    """pre-commit hook을 설치·제거·상태 확인합니다.

    Args:
        root: 프로젝트 루트 (git 레포 루트여야 함)
        action: "install" | "uninstall" | "status"
        steps: hook 실행 단계 목록 (기본: ["format", "test", "scan"])

    Returns:
        {"status": "ok"|"error", "message": str, "hook_path": str}
    """
    root = Path(root).resolve()
    if steps is None:
        steps = ["format", "test", "scan"]

    hooks_dir = _git_hooks_dir(root)
    if hooks_dir is None:
        return {
            "status": "error",
            "message": f".git 디렉토리를 찾을 수 없습니다: {root}",
            "hook_path": "",
        }

    hook = _hook_path(hooks_dir)
    backup = _backup_path(hooks_dir)

    if action == "install":
        return _install(hook, backup, steps)
    elif action == "uninstall":
        return _uninstall(hook, backup)
    elif action == "status":
        return _status(hook)
    else:
        return {
            "status": "error",
            "message": f"알 수 없는 action: {action}. install | uninstall | status 중 하나여야 합니다.",
            "hook_path": str(hook),
        }


def _install(hook: Path, backup: Path, steps: list[str]) -> dict:
    # 이미 locky hook인 경우 덮어쓰기
    if hook.exists() and not _is_locky_hook(hook):
        shutil.copy2(hook, backup)

    script = _build_hook_script(steps)
    hook.write_text(script, encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    backed_up = f" (기존 hook → {backup.name})" if backup.exists() else ""
    return {
        "status": "ok",
        "message": f"pre-commit hook 설치 완료{backed_up}\n실행 순서: {' → '.join(s for s in steps if s in _STEP_COMMANDS and _STEP_COMMANDS[s])}",
        "hook_path": str(hook),
    }


def _uninstall(hook: Path, backup: Path) -> dict:
    if not hook.exists():
        return {
            "status": "ok",
            "message": "pre-commit hook이 존재하지 않습니다.",
            "hook_path": str(hook),
        }

    if not _is_locky_hook(hook):
        return {
            "status": "error",
            "message": "이 hook은 locky가 설치하지 않았습니다. 수동으로 확인하세요.",
            "hook_path": str(hook),
        }

    hook.unlink()

    if backup.exists():
        shutil.move(str(backup), str(hook))
        return {
            "status": "ok",
            "message": "hook 제거 완료 (기존 hook 복원됨)",
            "hook_path": str(hook),
        }

    return {
        "status": "ok",
        "message": "pre-commit hook 제거 완료",
        "hook_path": str(hook),
    }


def _status(hook: Path) -> dict:
    if not hook.exists():
        return {"status": "ok", "message": "설치되지 않음", "hook_path": str(hook)}

    if _is_locky_hook(hook):
        return {"status": "ok", "message": "locky hook 설치됨", "hook_path": str(hook)}

    return {
        "status": "ok",
        "message": "다른 hook이 설치됨 (locky 아님)",
        "hook_path": str(hook),
    }
