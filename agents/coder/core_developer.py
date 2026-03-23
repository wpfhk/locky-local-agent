"""Core Developer — 태스크 기반 코드 구현 서브에이전트."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from config import OLLAMA_MODEL
from states.state import LockyGlobalState
from tools.mcp_filesystem import read_file, write_file, get_file_tree
from tools.ollama_client import OllamaClient

_MAX_FILE_PREVIEW = 4000  # 기존 파일 읽기 최대 문자 수


def _read_existing_files(task: dict) -> dict:
    """태스크에서 수정 대상 파일들을 읽어 {경로: 내용} 반환합니다."""
    contents: dict = {}
    files_to_modify = task.get("files_to_modify", [])
    for fpath in files_to_modify:
        try:
            content = read_file(fpath)
            contents[fpath] = content[:_MAX_FILE_PREVIEW]
        except (FileNotFoundError, IsADirectoryError, ValueError):
            contents[fpath] = ""  # 파일이 없으면 새로 생성
    return contents


def _parse_file_blocks(response: str) -> List[dict]:
    """
    LLM 응답에서 [파일경로]\\n코드내용 형식의 블록을 파싱합니다.

    지원 형식:
      1. [파일경로]\\n코드
      2. === 파일경로 ===\\n코드
      3. ```language (파일경로)\\n코드\\n```
    """
    results: List[dict] = []

    # 형식 1: [파일경로]\n코드
    pattern1 = re.compile(r"\[([^\[\]]+\.(?:py|js|ts|json|yaml|yml|toml|txt|md|sh|cfg|ini))\]\n([\s\S]+?)(?=\[[^\[\]]+\.\w+\]|\Z)", re.MULTILINE)
    for match in pattern1.finditer(response):
        path = match.group(1).strip()
        code = match.group(2).strip()
        if code:
            results.append({"path": path, "content": code})

    if results:
        return results

    # 형식 2: === 파일경로 ===\n코드
    pattern2 = re.compile(r"={3,}\s*([^\n]+?)\s*={3,}\n([\s\S]+?)(?====|\Z)", re.MULTILINE)
    for match in pattern2.finditer(response):
        path = match.group(1).strip()
        code = match.group(2).strip()
        if path and code:
            results.append({"path": path, "content": code})

    if results:
        return results

    # 형식 3: 코드 블록 내 파일 경로
    pattern3 = re.compile(
        r"(?:#\s*(?:File:|파일:)\s*)?([^\s`]+\.(?:py|js|ts|json|yaml|yml|toml|txt|sh))\n"
        r"```(?:\w+)?\n([\s\S]+?)\n```",
        re.MULTILINE
    )
    for match in pattern3.finditer(response):
        path = match.group(1).strip()
        code = match.group(2).strip()
        if code:
            results.append({"path": path, "content": code})

    return results


def _build_task_prompt(task: dict, existing_contents: dict, codebase_summary: str, feedback: str) -> str:
    """태스크 구현 요청 프롬프트를 생성합니다."""
    files_info = ""
    if existing_contents:
        parts = []
        for path, content in existing_contents.items():
            if content:
                parts.append(f"=== {path} (현재 내용) ===\n{content}")
            else:
                parts.append(f"=== {path} (신규 파일 — 아직 존재하지 않음) ===")
        files_info = "\n\n".join(parts)

    feedback_section = f"\n## 수정 피드백 (반드시 반영)\n{feedback}\n" if feedback else ""

    files_to_create = task.get("files_to_create", [])
    create_note = ""
    if files_to_create:
        create_note = f"\n생성할 파일: {', '.join(files_to_create)}"

    return f"""당신은 숙련된 소프트웨어 개발자입니다. 다음 태스크를 구현하세요.

## 코드베이스 컨텍스트
{codebase_summary}

## 태스크
ID: {task.get('id', 'T001')}
제목: {task.get('title', '구현')}
설명: {task.get('description', '')}
수정할 파일: {', '.join(task.get('files_to_modify', []))}
{create_note}
구현 힌트: {task.get('code_hints', '')}
{feedback_section}

## 현재 파일 내용
{files_info if files_info else '(파일 없음)'}

## 출력 규칙
- 각 파일을 다음 형식으로 출력하세요:
  [파일경로]
  코드내용 전체

- 여러 파일인 경우 같은 형식을 반복합니다.
- 코드만 출력하세요. 설명은 파일 앞 [경로] 헤더로 충분합니다.
- 기존 코드 패턴과 스타일을 따르세요.
- 보안 취약점 없이 구현하세요 (하드코딩 시크릿 금지, 파라미터화된 쿼리 사용).
"""


def develop_code(state: LockyGlobalState) -> dict:
    """
    태스크 목록의 각 태스크를 Ollama를 통해 구현하고 파일로 저장합니다.

    Args:
        state: 전역 파이프라인 상태 (planner_output.task_list 포함)

    Returns:
        coder_output에 modified_files 목록을 포함한 dict
    """
    planner_output = state.get("planner_output") or {}
    task_list = planner_output.get("task_list", [])
    codebase_summary = planner_output.get("codebase_summary", "")

    # Tester 피드백
    tester_output = state.get("tester_output") or {}
    feedback = tester_output.get("feedback", "") if state.get("retry_count", 0) > 0 else ""

    client = OllamaClient(model=OLLAMA_MODEL)
    all_modified_files: List[str] = []
    task_results: List[dict] = []

    if not task_list:
        print("[CoreDeveloper] 태스크 목록이 비어 있습니다.")
        return {
            "coder_output": {
                "current_task": {},
                "modified_files": [],
                "commit_message_draft": f"feat: {state.get('cmd', '')[:60]}",
                "iteration": state.get("retry_count", 0) + 1,
            }
        }

    for task in task_list:
        task_id = task.get("id", "T???")
        task_title = task.get("title", "")
        print(f"[CoreDeveloper] 태스크 {task_id} 구현 중: {task_title}")

        # 기존 파일 읽기
        existing_contents = _read_existing_files(task)

        # 프롬프트 생성 및 Ollama 호출
        prompt = _build_task_prompt(task, existing_contents, codebase_summary, feedback)
        messages = [{"role": "user", "content": prompt}]

        try:
            response = client.chat(messages)
        except Exception as e:
            print(f"[CoreDeveloper] 태스크 {task_id} Ollama 호출 실패: {e}")
            task_results.append({"task_id": task_id, "status": "error", "error": str(e)})
            continue

        # 파일 블록 파싱 및 저장
        file_blocks = _parse_file_blocks(response)

        if not file_blocks:
            # 파싱 실패 시 — files_to_create가 있으면 응답 전체를 첫 번째 파일로 저장
            targets = task.get("files_to_create", []) or task.get("files_to_modify", [])
            if targets:
                # 코드 블록만 추출 시도
                code_match = re.search(r"```(?:\w+)?\n([\s\S]+?)\n```", response)
                code = code_match.group(1) if code_match else response
                file_blocks = [{"path": targets[0], "content": code}]
            else:
                print(f"[CoreDeveloper] 태스크 {task_id}: 파일 블록 파싱 실패, 파일 저장 건너뜀")
                task_results.append({"task_id": task_id, "status": "parse_failed"})
                continue

        saved_files: List[str] = []
        for block in file_blocks:
            file_path = block["path"]
            content = block["content"]
            try:
                abs_path = write_file(file_path, content)
                saved_files.append(file_path)
                all_modified_files.append(file_path)
                print(f"[CoreDeveloper]   저장: {file_path}")
            except Exception as e:
                print(f"[CoreDeveloper]   저장 실패 {file_path}: {e}")

        task_results.append({
            "task_id": task_id,
            "title": task_title,
            "status": "done",
            "files": saved_files,
        })

    # 중복 제거
    unique_files = list(dict.fromkeys(all_modified_files))

    # 커밋 메시지 초안 생성 (간단한 규칙 기반)
    cmd = state.get("cmd", "")
    if unique_files:
        commit_msg = f"feat: {cmd[:60]}" if cmd else f"feat: implement {len(unique_files)} file(s)"
    else:
        commit_msg = f"chore: attempt implementation for '{cmd[:50]}'"

    existing_coder = state.get("coder_output") or {}

    return {
        "coder_output": {
            **existing_coder,
            "current_task": task_list[-1] if task_list else {},
            "modified_files": unique_files,
            "commit_message_draft": commit_msg,
            "iteration": state.get("retry_count", 0) + 1,
            "task_results": task_results,
        }
    }
