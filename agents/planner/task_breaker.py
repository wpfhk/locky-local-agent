"""Task Breaker — 작업 분할 서브에이전트."""

from __future__ import annotations

import json
import re
import time
from typing import List, Optional

from config import OLLAMA_MODEL, OLLAMA_TASK_TIMEOUT
from states.state import LockyGlobalState
from tools.ollama_client import OllamaClient

_MAX_RETRIES = 3

# 간단한 생성 요청으로 간주하는 최대 cmd 길이
_SIMPLE_CMD_THRESHOLD = 150

# 한글→영어 명사 매핑 (파일명 생성용)
_NOUN_MAP = {
    "덧셈": "addition", "뺄셈": "subtraction", "곱셈": "multiplication",
    "나눗셈": "division", "계산기": "calculator", "계산": "calculator",
    "정렬": "sorter", "검색": "search", "파서": "parser",
    "크롤러": "crawler", "스크래퍼": "scraper", "게임": "game",
    "채팅": "chat", "서버": "server", "클라이언트": "client",
    "변환": "converter", "분석": "analyzer", "생성": "generator",
    "다운로드": "downloader", "업로드": "uploader", "파일": "file_tool",
    "텍스트": "text_tool", "숫자": "number_tool", "문자열": "string_tool",
}


def _derive_filename(cmd: str) -> str:
    """cmd 문자열에서 적절한 파일명을 추출합니다."""
    lang = "py"
    if any(kw in cmd.lower() for kw in ("javascript", "자바스크립트", " js ")):
        lang = "js"
    elif any(kw in cmd.lower() for kw in ("typescript", "타입스크립트")):
        lang = "ts"

    for korean, english in _NOUN_MAP.items():
        if korean in cmd:
            return f"{english}.{lang}"

    # 영어 단어 추출 시도
    english_words = re.findall(r"[a-zA-Z]{4,}", cmd)
    skip = {
        "with", "that", "this", "from", "have", "python", "java",
        "make", "create", "write", "simple", "basic", "using", "given",
        "your", "just", "only", "also", "into", "some", "very",
    }
    for word in english_words:
        if word.lower() not in skip:
            return f"{word.lower()}.{lang}"

    return f"solution.{lang}"


def _is_simple_request(cmd: str) -> bool:
    """단순 파일 생성 요청인지 판단합니다."""
    if len(cmd) > _SIMPLE_CMD_THRESHOLD:
        return False
    complex_keywords = ("리팩토링", "마이그레이션", "기존", "수정해", "변경해", "refactor", "migrate", "existing")
    return not any(kw in cmd for kw in complex_keywords)


def _extract_json(text: str) -> Optional[dict]:
    """응답 텍스트에서 JSON 객체를 추출합니다."""
    # 코드 블록 제거
    clean = text.strip()
    if "```" in clean:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", clean)
        if match:
            clean = match.group(1).strip()

    # 직접 파싱 시도
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # { ... } 블록 추출 시도
    brace_match = re.search(r"(\{[\s\S]+\})", clean)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def _build_prompt(cmd: str, codebase_summary: str, file_tree: str, dependencies: str) -> str:
    return f"""당신은 소프트웨어 개발 작업 분할 전문가입니다.
아래 요구사항과 코드베이스 분석 결과를 바탕으로 원자 단위 작업 지시서를 JSON으로 생성하세요.

## 요구사항 (사용자 명령)
{cmd}

## 코드베이스 요약
{codebase_summary}

## 파일 트리
{file_tree[:3000]}

## 의존성
{dependencies}

## 규칙
- 각 태스크는 단일 책임 (한 파일 또는 한 기능 단위)
- 너무 크면 분할, 너무 작으면 합치기
- 각 태스크는 완료 여부를 명확히 판단 가능해야 함
- files_to_modify와 files_to_create에 구체적 파일 경로 포함

## 출력 형식 (반드시 JSON만 출력, 다른 텍스트 없이)
{{
  "tasks": [
    {{
      "id": "T001",
      "title": "태스크 제목",
      "description": "상세 구현 지침 — 무엇을, 어떻게",
      "files_to_modify": ["수정할 파일 경로"],
      "files_to_create": ["생성할 파일 경로"],
      "code_hints": "구현 힌트 또는 예시 코드 스니펫",
      "dependencies": [],
      "priority": "high|medium|low",
      "estimated_complexity": "simple|moderate|complex"
    }}
  ],
  "execution_order": [
    ["T001"],
    ["T002", "T003"]
  ]
}}
"""


def break_tasks(state: LockyGlobalState) -> dict:
    """
    사용자 명령과 코드베이스 요약을 바탕으로 원자 단위 태스크 목록을 생성합니다.

    Args:
        state: 전역 파이프라인 상태 (cmd, planner_output 포함)

    Returns:
        planner_output에 task_list를 추가한 dict
    """
    cmd = state.get("cmd", "")
    planner_output = state.get("planner_output") or {}
    codebase_summary = planner_output.get("codebase_summary", "정보 없음")
    file_tree = planner_output.get("file_tree", "")
    dependencies = planner_output.get("dependencies", "")

    # 단순 요청은 짧은 타임아웃으로 빠르게 처리
    is_simple = _is_simple_request(cmd)
    timeout = OLLAMA_TASK_TIMEOUT if is_simple else OLLAMA_TASK_TIMEOUT * 4
    client = OllamaClient(model=OLLAMA_MODEL, timeout=timeout)

    if is_simple:
        # 단순 요청: 파일트리/의존성 없이 최소 프롬프트 사용
        prompt = _build_prompt(cmd, codebase_summary[:300], "", "")
    else:
        prompt = _build_prompt(cmd, codebase_summary, file_tree, dependencies)
    messages = [{"role": "user", "content": prompt}]

    task_data: Optional[dict] = None
    last_response = ""

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.chat(messages)
            last_response = response
            task_data = _extract_json(response)
            if task_data and "tasks" in task_data:
                break
        except Exception as e:
            print(f"[TaskBreaker] 시도 {attempt} 실패: {e}")

        if attempt < _MAX_RETRIES:
            # 재시도 프롬프트 — 이전 응답을 포함하여 JSON 수정 요청
            retry_prompt = (
                f"이전 응답에서 유효한 JSON을 추출할 수 없었습니다.\n"
                f"이전 응답:\n{last_response[:500]}\n\n"
                f"반드시 순수한 JSON만 출력하세요. 설명 텍스트 없이."
            )
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": last_response},
                {"role": "user", "content": retry_prompt},
            ]
            time.sleep(1)

    # 파싱에 완전히 실패한 경우 기본 태스크 생성
    if not task_data or "tasks" not in task_data:
        print(f"[TaskBreaker] JSON 파싱 {_MAX_RETRIES}회 실패. 기본 태스크로 대체합니다.")
        fallback_filename = _derive_filename(cmd)
        task_data = {
            "tasks": [
                {
                    "id": "T001",
                    "title": "요구사항 구현",
                    "description": cmd,
                    "files_to_modify": [],
                    "files_to_create": [fallback_filename],
                    "code_hints": f"파일 {fallback_filename}에 요구사항을 구현하세요.",
                    "dependencies": [],
                    "priority": "high",
                    "estimated_complexity": "simple" if is_simple else "moderate",
                }
            ],
            "execution_order": [["T001"]],
            "_parse_failed": True,
            "_raw_response": last_response[:1000],
        }

    task_list: List[dict] = task_data.get("tasks", [])

    updated_planner_output = {
        **planner_output,
        "task_list": task_list,
        "execution_order": task_data.get("execution_order", []),
    }

    return {"planner_output": updated_planner_output}
