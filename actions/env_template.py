"""actions/env_template.py — .env 파일을 읽어 값을 제거한 .env.example을 생성합니다."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional


_ENV_KEY_PATTERN = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*=", re.MULTILINE)
_GETENV_PATTERN = re.compile(
    r'os\.environ(?:\.get)?\(["\']([A-Z_][A-Z0-9_]*)["\']|'
    r'os\.getenv\(["\']([A-Z_][A-Z0-9_]*)["\']',
)
_DOTENV_KEY_PATTERN = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*=", re.MULTILINE)


def run(
    root: Path,
    output: str = ".env.example",
) -> dict:
    """
    .env 파일을 읽어 값을 제거한 .env.example을 생성합니다.
    .env 파일이 없으면 소스 코드에서 환경변수 키를 수집합니다.

    Args:
        root: 프로젝트 루트 Path
        output: 출력 파일명 (기본: .env.example)

    Returns:
        {"status": "ok"|"no_env_file", "output_file": str, "keys": [...]}
    """
    root = Path(root).resolve()
    env_file = root / ".env"
    output_path = root / output

    if env_file.exists():
        keys, example_content = _parse_env_file(env_file)
        output_path.write_text(example_content, encoding="utf-8")
        return {
            "status": "ok",
            "output_file": str(output_path),
            "keys": keys,
        }

    # .env 없으면 소스 코드에서 키 수집
    keys = _collect_env_keys_from_source(root)
    if not keys:
        return {
            "status": "no_env_file",
            "output_file": str(output_path),
            "keys": [],
        }

    lines = [
        "# .env.example — 환경변수 템플릿",
        "# 이 파일을 .env로 복사하고 값을 채우세요.",
        "",
    ]
    for key in sorted(set(keys)):
        lines.append(f"{key}=")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "status": "ok",
        "output_file": str(output_path),
        "keys": sorted(set(keys)),
    }


def _parse_env_file(env_file: Path) -> tuple[List[str], str]:
    """
    .env 파일을 파싱하여 (키 목록, example 내용) 을 반환합니다.
    값을 빈 문자열로 대체합니다.
    """
    content = env_file.read_text(encoding="utf-8", errors="ignore")
    keys = []
    output_lines = [
        "# .env.example — 환경변수 템플릿",
        "# 이 파일을 .env로 복사하고 값을 채우세요.",
        "",
    ]

    for line in content.splitlines():
        stripped = line.strip()
        # 주석이나 빈 줄은 그대로
        if not stripped or stripped.startswith("#"):
            output_lines.append(line)
            continue
        # KEY=VALUE 형태
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
        if match:
            key = match.group(1)
            keys.append(key)
            output_lines.append(f"{key}=")
        else:
            output_lines.append(line)

    return keys, "\n".join(output_lines) + "\n"


def _collect_env_keys_from_source(root: Path) -> List[str]:
    """소스 코드에서 os.environ.get / os.getenv 패턴으로 환경변수 키를 수집합니다."""
    keys = []
    exclude_dirs = {".venv", "__pycache__", ".git", "node_modules"}

    for py_file in root.rglob("*.py"):
        try:
            parts = py_file.relative_to(root).parts
            if any(part in exclude_dirs for part in parts):
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for match in _GETENV_PATTERN.finditer(content):
                key = match.group(1) or match.group(2)
                if key:
                    keys.append(key)
        except Exception:
            continue

    return keys
