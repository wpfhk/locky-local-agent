"""Context Analyzer — 코드베이스 분석 서브에이전트."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from config import OLLAMA_MODEL
from states.state import LockyGlobalState
from tools.mcp_filesystem import get_file_tree, read_file, list_directory
from tools.ollama_client import OllamaClient

# 분석 대상 파일 패턴
_TARGET_PATTERNS = ("*.py", "*.toml", "*.json", "*.md", "*.txt", "*.yaml", "*.yml")
_PRIORITY_FILES = ("requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
                   "package.json", "go.mod", "Cargo.toml")
_MAX_FILE_SIZE = 8_000   # 파일당 최대 읽기 문자 수
_MAX_FILES_TO_READ = 15  # 읽을 최대 파일 수


def _collect_key_files(file_tree: str) -> List[str]:
    """파일 트리 문자열에서 주요 파일 경로를 추출합니다."""
    from pathlib import Path as _Path
    import re

    # 파일 트리에서 파일명 추출 (├── 또는 └── 뒤의 파일명)
    names = re.findall(r"[├└]── (.+?)(?:\s|$)", file_tree)

    priority: List[str] = []
    secondary: List[str] = []

    for name in names:
        name = name.strip()
        if name in _PRIORITY_FILES:
            priority.append(name)
        elif any(name.endswith(ext[1:]) for ext in _TARGET_PATTERNS if ext.startswith("*")):
            secondary.append(name)

    return priority + secondary


def _read_files_safe(root: str, filenames: List[str]) -> dict:
    """파일들을 안전하게 읽어 {경로: 내용} 딕셔너리로 반환합니다."""
    from pathlib import Path as _Path
    import os

    root_path = _Path(root)
    contents: dict = {}
    count = 0

    for filename in filenames:
        if count >= _MAX_FILES_TO_READ:
            break
        # root 아래에서 해당 파일 탐색
        for candidate in root_path.rglob(filename):
            if candidate.is_file():
                try:
                    text = candidate.read_text(encoding="utf-8", errors="replace")
                    rel = str(candidate.relative_to(root_path))
                    contents[rel] = text[:_MAX_FILE_SIZE]
                    count += 1
                except OSError:
                    pass
                break  # 같은 이름의 첫 번째 파일만

    return contents


def analyze_context(state: LockyGlobalState) -> dict:
    """
    프로젝트 코드베이스를 분석하고 요약합니다.

    Args:
        state: 전역 파이프라인 상태

    Returns:
        planner_output에 codebase_summary, file_tree, dependencies를 추가한 dict
    """
    from config import MCP_FILESYSTEM_ROOT

    # 1. 파일 트리 파악
    file_tree = get_file_tree(".", max_depth=4)

    # 2. 주요 파일 읽기
    key_filenames = _collect_key_files(file_tree)
    file_contents = _read_files_safe(MCP_FILESYSTEM_ROOT, key_filenames)

    # 추가로 *.py 파일 중 최상위 레벨 파일 읽기
    from pathlib import Path as _Path
    root_path = _Path(MCP_FILESYSTEM_ROOT)
    py_count = 0
    for py_file in sorted(root_path.rglob("*.py")):
        if py_count >= 8:
            break
        # __pycache__, .venv 등 제외
        if any(part.startswith(".") or part in ("__pycache__", "venv", ".venv", "node_modules")
               for part in py_file.parts):
            continue
        rel = str(py_file.relative_to(root_path))
        if rel not in file_contents:
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
                file_contents[rel] = text[:_MAX_FILE_SIZE]
                py_count += 1
            except OSError:
                pass

    # 3. Ollama에 코드베이스 요약 요청
    client = OllamaClient(model=OLLAMA_MODEL)

    files_text = "\n\n".join(
        f"=== {path} ===\n{content}" for path, content in file_contents.items()
    )

    prompt = f"""당신은 코드베이스 분석 전문가입니다.
아래 프로젝트 파일 트리와 주요 파일 내용을 분석하여 다음 항목을 JSON으로 출력하세요.

## 파일 트리
{file_tree}

## 주요 파일 내용
{files_text}

## 출력 형식 (반드시 JSON만 출력)
{{
  "codebase_summary": "프로젝트 목적, 아키텍처, 주요 구성 요소에 대한 2-3 문장 요약",
  "dependencies": "주요 의존성 패키지 및 버전 목록 (문자열)",
  "tech_stack": "사용 언어, 프레임워크, 도구",
  "conventions": "코드 스타일, 네이밍 컨벤션, 테스트 프레임워크",
  "entry_points": ["엔트리포인트 파일 목록"],
  "key_modules": ["핵심 모듈/디렉토리 목록"]
}}
"""

    messages = [{"role": "user", "content": prompt}]
    response = client.chat(messages)

    # JSON 파싱 시도
    summary_data = {}
    try:
        # 코드 블록 제거
        clean = response.strip()
        if "```" in clean:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", clean)
            if match:
                clean = match.group(1)
        summary_data = json.loads(clean)
    except (json.JSONDecodeError, AttributeError):
        # 파싱 실패 시 원본 텍스트를 요약으로 사용
        summary_data = {
            "codebase_summary": response[:1000],
            "dependencies": "",
            "tech_stack": "Python",
            "conventions": "snake_case",
            "entry_points": [],
            "key_modules": [],
        }

    codebase_summary = summary_data.get("codebase_summary", response[:500])
    dependencies = summary_data.get("dependencies", "")

    # 기존 planner_output 유지하면서 업데이트
    existing = state.get("planner_output") or {}
    updated_planner_output = {
        **existing,
        "codebase_summary": codebase_summary,
        "file_tree": file_tree,
        "dependencies": dependencies,
        "analysis_detail": summary_data,
        "file_contents_sample": {k: v[:500] for k, v in list(file_contents.items())[:5]},
    }

    return {"planner_output": updated_planner_output}
