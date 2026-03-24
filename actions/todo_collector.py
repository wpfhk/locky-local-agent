"""actions/todo_collector.py — 프로젝트에서 TODO/FIXME/HACK/XXX를 수집합니다."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

_EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".mypy_cache", ".pytest_cache"}
_INCLUDE_EXTS = {".py", ".js", ".ts", ".md"}
_TAG_PATTERN = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)[:\s]*(.*)", re.IGNORECASE)


def run(
    root: Path,
    output_file: Optional[str] = None,
) -> dict:
    """
    프로젝트에서 TODO/FIXME/HACK/XXX를 수집합니다.

    Args:
        root: 프로젝트 루트 Path
        output_file: 결과를 저장할 마크다운 파일 경로 (None이면 저장 안 함)

    Returns:
        {"status": "ok", "total": int, "items": [{"file": str, "line": int, "tag": str, "text": str}]}
    """
    root = Path(root).resolve()
    items: List[dict] = []

    for file_path in _iter_files(root):
        try:
            rel_path = str(file_path.relative_to(root))
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(content.splitlines(), start=1):
                match = _TAG_PATTERN.search(line)
                if match:
                    tag = match.group(1).upper()
                    text = match.group(2).strip()
                    items.append({
                        "file": rel_path,
                        "line": lineno,
                        "tag": tag,
                        "text": text,
                    })
        except Exception:
            continue

    if output_file:
        try:
            _write_markdown(items, Path(output_file), root)
        except Exception:
            pass

    return {
        "status": "ok",
        "total": len(items),
        "items": items,
    }


def _iter_files(root: Path):
    """대상 파일을 순회합니다 (제외 디렉터리 스킵)."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        # 제외 디렉터리 확인
        parts = path.relative_to(root).parts
        if any(part in _EXCLUDE_DIRS for part in parts):
            continue
        if path.suffix in _INCLUDE_EXTS:
            yield path


def _write_markdown(items: List[dict], output_path: Path, root: Path) -> None:
    """수집된 TODO 항목을 마크다운 파일로 저장합니다."""
    lines = [
        "# TODO / FIXME 목록\n",
        f"총 {len(items)}개 항목\n\n",
        "| 태그 | 파일 | 줄 | 내용 |",
        "|------|------|-----|------|",
    ]
    for item in items:
        file_link = f"`{item['file']}:{item['line']}`"
        text = item["text"].replace("|", "\\|")
        lines.append(f"| {item['tag']} | {file_link} | {item['line']} | {text} |")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
