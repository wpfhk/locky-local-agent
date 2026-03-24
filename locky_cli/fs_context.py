"""세션/스레드별 MCP 파일시스템 루트 — ContextVar + 환경변수 동기화."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator, Optional

_root_var: ContextVar[Optional[Path]] = ContextVar("locky_fs_root", default=None)

_ENV_KEY = "MCP_FILESYSTEM_ROOT"


def _default_root_from_env() -> Path:
    return Path(os.environ.get(_ENV_KEY, os.getcwd())).resolve()


def get_filesystem_root() -> Path:
    """현재 컨텍스트의 MCP 루트(절대 경로). 설정 없으면 환경변수/ cwd."""
    override = _root_var.get()
    if override is not None:
        return override.resolve()
    return _default_root_from_env()


def set_filesystem_root(path: Path | str) -> None:
    """테스트 또는 단일 스레드에서 루트를 고정할 때 사용."""
    p = Path(path).resolve()
    _root_var.set(p)
    os.environ[_ENV_KEY] = str(p)


@contextmanager
def filesystem_root_context(root: Optional[Path | str]) -> Iterator[None]:
    """
    그래프 실행·executor 작업 단위로 루트를 고정합니다.
    None이면 기존 환경/컨텍스트를 건드리지 않습니다.
    """
    if root is None:
        yield
        return

    p = Path(root).resolve()
    token = _root_var.set(p)
    old_env = os.environ.get(_ENV_KEY)
    os.environ[_ENV_KEY] = str(p)
    try:
        yield
    finally:
        _root_var.reset(token)
        if old_env is not None:
            os.environ[_ENV_KEY] = old_env
        else:
            os.environ.pop(_ENV_KEY, None)


def default_full_access_root() -> Path:
    """full 권한 모드용 시스템 루트 (Unix: /, Windows: 드라이브 루트)."""
    if os.name == "nt":
        return Path(Path.cwd().anchor).resolve()
    return Path("/")
