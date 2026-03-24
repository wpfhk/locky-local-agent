"""locky_cli/lang_detect.py — git-tracked 파일 확장자 기반 언어 자동 감지. (v0.5.0)"""
from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path


_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
}


def detect(root: Path) -> dict[str, object]:
    """git ls-files 결과의 확장자를 집계하여 언어 정보를 반환합니다.

    Returns:
        {"primary": "python", "all": ["python", "javascript"]}
    """
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root, capture_output=True, text=True, timeout=10,
        )
        files = result.stdout.splitlines()
    except Exception:
        # git 미사용 프로젝트 fallback
        files = [str(f.relative_to(root)) for f in root.rglob("*") if f.is_file()]

    counts: Counter[str] = Counter()
    for f in files:
        ext = Path(f).suffix.lower()
        lang = _EXT_TO_LANG.get(ext)
        if lang:
            counts[lang] += 1

    if not counts:
        return {"primary": "unknown", "all": []}

    ordered = [lang for lang, _ in counts.most_common()]
    return {"primary": ordered[0], "all": ordered}
