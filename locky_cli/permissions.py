"""권한 모드 — workspace(시작 디렉터리 이하) vs full(로컬 전역)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class PermissionMode(str, Enum):
    WORKSPACE = "workspace"
    FULL = "full"


def resolve_workspace_root(start_dir: Path | str | None) -> Path:
    """세션 시작 디렉터리를 절대 경로로 고정합니다."""
    if start_dir is None:
        return Path.cwd().resolve()
    return Path(start_dir).resolve()
