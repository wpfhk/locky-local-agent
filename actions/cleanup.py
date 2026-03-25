"""actions/cleanup.py — 불필요한 파일들을 정리합니다."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

_CLEANUP_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/.pytest_cache",
    "**/*.egg-info",
    "**/.DS_Store",
]

_EXCLUDE_DIRS = {".git", ".venv", "node_modules"}


def run(root: Path, dry_run: bool = True) -> dict:
    """
    불필요한 파일과 디렉터리를 정리합니다.

    Args:
        root: 프로젝트 루트 Path
        dry_run: True(기본)면 삭제 대상만 나열, False면 실제 삭제

    Returns:
        {"status": "ok", "removed": [...], "total_size_bytes": int, "dry_run": bool}
    """
    root = Path(root).resolve()
    targets: List[dict] = []

    for pattern in _CLEANUP_PATTERNS:
        for path in root.glob(pattern):
            if _is_excluded(path, root):
                continue
            try:
                size = _get_size(path)
                targets.append(
                    {
                        "path": str(path.relative_to(root)),
                        "abs_path": str(path),
                        "size_bytes": size,
                        "is_dir": path.is_dir(),
                    }
                )
            except Exception:
                continue

    # 중복 제거 (하위 경로가 상위에 포함되는 경우)
    targets = _deduplicate(targets)

    total_size = sum(t["size_bytes"] for t in targets)
    removed = []

    if not dry_run:
        for target in targets:
            abs_path = Path(target["abs_path"])
            try:
                if abs_path.is_dir():
                    shutil.rmtree(abs_path)
                elif abs_path.is_file():
                    abs_path.unlink()
                removed.append(target["path"])
            except Exception:
                continue
    else:
        removed = [t["path"] for t in targets]

    return {
        "status": "ok",
        "removed": removed,
        "total_size_bytes": total_size,
        "dry_run": dry_run,
    }


def _is_excluded(path: Path, root: Path) -> bool:
    """제외 디렉터리 하위인지 확인합니다."""
    try:
        parts = path.relative_to(root).parts
        return any(part in _EXCLUDE_DIRS for part in parts)
    except ValueError:
        return False


def _get_size(path: Path) -> int:
    """파일 또는 디렉터리 크기를 바이트로 반환합니다."""
    if path.is_file():
        return path.stat().st_size
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except Exception:
        pass
    return total


def _deduplicate(targets: List[dict]) -> List[dict]:
    """상위 디렉터리가 이미 포함된 경우 하위 항목 제거."""
    sorted_targets = sorted(targets, key=lambda t: len(t["path"]))
    result = []
    seen_dirs = set()

    for target in sorted_targets:
        path = target["path"]
        # 상위 디렉터리가 이미 포함되어 있으면 스킵
        if any(path.startswith(d + "/") for d in seen_dirs):
            continue
        result.append(target)
        if target["is_dir"]:
            seen_dirs.add(path)

    return result
