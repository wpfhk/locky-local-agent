"""tools/editor.py -- 안전한 파일 편집 도구 (backup + diff + Rich markup)."""

from __future__ import annotations

import difflib
import shutil
from pathlib import Path


_MAX_CHARS = 5000  # 부분 읽기 최대 문자 수


def create_backup(path: Path) -> Path:
    """파일을 <path>.bak으로 백업합니다."""
    bak = Path(str(path) + ".bak")
    shutil.copy2(path, bak)
    return bak


def read_file_range(
    path: Path, start: int = 1, end: int | None = None, max_chars: int = _MAX_CHARS
) -> str:
    """파일의 특정 라인 범위를 읽습니다 (1-indexed). max_chars로 크기 제한."""
    try:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"[read error: {exc}]"

    lines = content.splitlines(keepends=True)
    start_idx = max(0, start - 1)
    end_idx = len(lines) if end is None else min(end, len(lines))
    chunk = "".join(lines[start_idx:end_idx])

    if len(chunk) > max_chars:
        chunk = chunk[:max_chars] + f"\n... (truncated at {max_chars} chars)"
    return chunk


def replace_in_file(
    path: Path, old_text: str, new_text: str, backup: bool = True
) -> tuple[bool, str]:
    """파일에서 old_text를 new_text로 교체합니다.

    Returns:
        (success: bool, unified_diff: str)
        success=False if old_text not found in file.
    """
    p = Path(path)
    try:
        original = p.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"[read error: {exc}]"

    if old_text not in original:
        return False, ""

    updated = original.replace(old_text, new_text, 1)

    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{p.name}",
            tofile=f"b/{p.name}",
            lineterm="",
        )
    )
    diff_text = "".join(diff_lines)

    if backup:
        create_backup(p)

    p.write_text(updated, encoding="utf-8")
    return True, diff_text


def diff_markup(diff_text: str) -> str:
    """unified diff 문자열을 Rich 마크업 문자열로 변환합니다."""
    out = []
    for line in diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            out.append(f"[dim]{line}[/dim]")
        elif line.startswith("@@"):
            out.append(f"[cyan]{line}[/cyan]")
        elif line.startswith("+"):
            out.append(f"[green]{line}[/green]")
        elif line.startswith("-"):
            out.append(f"[red]{line}[/red]")
        else:
            out.append(line)
    return "\n".join(out)
