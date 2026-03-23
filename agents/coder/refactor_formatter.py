"""Refactor Formatter — 코드 정리 및 커밋 메시지 초안 생성 서브에이전트."""

from __future__ import annotations

import re
from typing import List

from config import OLLAMA_MODEL
from states.state import LockyGlobalState
from tools.mcp_filesystem import read_file, write_file
from tools.ollama_client import OllamaClient

_MAX_FILE_SIZE = 6000  # 리팩토링 대상 파일 최대 읽기 문자 수


def _build_refactor_prompt(file_path: str, content: str) -> str:
    """리팩토링 요청 프롬프트를 생성합니다."""
    return f"""당신은 코드 품질 전문가입니다. 아래 파일을 PEP8 및 클린 코드 원칙에 따라 정리하세요.

## 파일: {file_path}
```
{content}
```

## 정리 규칙
- PEP8 스타일 준수 (들여쓰기, 공백, 빈 줄)
- import 순서 정리: 표준 라이브러리 → 서드파티 → 로컬
- 불필요한 디버그 print 제거 (의미 있는 로그는 유지)
- 주석 처리된 코드 제거 (의도적 보존이 아닌 경우)
- 미사용 import 제거
- 복잡한 로직에 간결한 주석 추가
- 공개 함수에 docstring 추가/보완
- 기능은 절대 변경하지 마세요

## 출력 규칙
- 정리된 코드 전체를 아래 형식으로 출력하세요:
  [파일경로]
  정리된코드 전체

- 코드 블록 마커(```) 없이 출력하세요.
"""


def _build_commit_message_prompt(cmd: str, modified_files: List[str], refactor_summary: str) -> str:
    """Conventional Commits 규격 커밋 메시지 생성 프롬프트."""
    files_str = "\n".join(f"- {f}" for f in modified_files)
    return f"""Conventional Commits 규격으로 커밋 메시지를 작성하세요.

## 작업 내용
사용자 요구사항: {cmd}

수정된 파일:
{files_str}

리팩토링 요약:
{refactor_summary}

## Conventional Commits 형식
<type>(<scope>): <subject>

[body — 선택사항]

[footer — 선택사항]

## type 선택 기준
- feat: 새 기능
- fix: 버그 수정
- refactor: 기능 변경 없이 코드 개선
- chore: 빌드, 설정, 패키지 등 기타 작업
- docs: 문서 변경
- test: 테스트 추가/수정
- style: 포매팅, 세미콜론 누락 등 기능 무관 변경

## 출력 규칙
- 커밋 메시지만 출력 (설명 없이)
- subject는 50자 이내, 소문자, 마침표 없이
- body는 72자 줄바꿈
"""


def _extract_refactored_code(response: str, file_path: str) -> str:
    """응답에서 리팩토링된 코드를 추출합니다."""
    # [파일경로]\n코드 형식 파싱
    pattern = re.compile(
        r"\[" + re.escape(file_path) + r"\]\n([\s\S]+?)(?=\[[\w./]+\]|\Z)",
        re.MULTILINE
    )
    match = pattern.search(response)
    if match:
        return match.group(1).strip()

    # 코드 블록 추출 시도
    code_match = re.search(r"```(?:\w+)?\n([\s\S]+?)\n```", response)
    if code_match:
        return code_match.group(1)

    # 응답 전체가 코드인 경우
    stripped = response.strip()
    # 응답이 설명 텍스트만인 경우는 원본 유지
    if len(stripped) > 50 and not stripped.startswith("#") and "\n" in stripped:
        return stripped

    return ""  # 추출 실패 → 원본 유지


def refactor_and_format(state: LockyGlobalState) -> dict:
    """
    modified_files 각각을 읽어 리팩토링하고 Conventional Commits 커밋 메시지 초안을 생성합니다.

    Args:
        state: 전역 파이프라인 상태 (coder_output.modified_files 포함)

    Returns:
        coder_output에 commit_message_draft와 refactor_notes를 업데이트한 dict
    """
    coder_output = state.get("coder_output") or {}
    modified_files: List[str] = coder_output.get("modified_files", [])
    cmd = state.get("cmd", "")

    client = OllamaClient(model=OLLAMA_MODEL)
    refactor_notes: List[str] = []
    successfully_refactored: List[str] = []

    # Python 파일만 리팩토링 (바이너리나 설정 파일은 건너뜀)
    py_files = [f for f in modified_files if f.endswith(".py")]

    for file_path in py_files:
        print(f"[RefactorFormatter] 리팩토링 중: {file_path}")
        try:
            content = read_file(file_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"[RefactorFormatter] 읽기 실패 {file_path}: {e}")
            refactor_notes.append(f"{file_path}: 읽기 실패 — {e}")
            continue

        if not content.strip():
            refactor_notes.append(f"{file_path}: 빈 파일 건너뜀")
            continue

        prompt = _build_refactor_prompt(file_path, content[:_MAX_FILE_SIZE])
        messages = [{"role": "user", "content": prompt}]

        try:
            response = client.chat(messages)
        except Exception as e:
            print(f"[RefactorFormatter] Ollama 호출 실패 {file_path}: {e}")
            refactor_notes.append(f"{file_path}: 리팩토링 실패 — {e}")
            continue

        refactored = _extract_refactored_code(response, file_path)

        if refactored and refactored != content.strip():
            try:
                write_file(file_path, refactored)
                successfully_refactored.append(file_path)
                refactor_notes.append(f"{file_path}: 리팩토링 완료")
                print(f"[RefactorFormatter]   완료: {file_path}")
            except Exception as e:
                print(f"[RefactorFormatter] 저장 실패 {file_path}: {e}")
                refactor_notes.append(f"{file_path}: 저장 실패 — {e}")
        else:
            refactor_notes.append(f"{file_path}: 변경 없음 (이미 정리됨)")

    # 커밋 메시지 초안 생성
    refactor_summary = "\n".join(refactor_notes) if refactor_notes else "리팩토링 없음"
    commit_prompt = _build_commit_message_prompt(cmd, modified_files, refactor_summary)
    commit_messages_list = [{"role": "user", "content": commit_prompt}]

    try:
        commit_response = client.chat(commit_messages_list)
        # 코드 블록 제거
        commit_message = commit_response.strip()
        if commit_message.startswith("```"):
            lines = commit_message.split("\n")
            commit_message = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            ).strip()
    except Exception as e:
        print(f"[RefactorFormatter] 커밋 메시지 생성 실패: {e}")
        commit_message = f"feat: {cmd[:60]}" if cmd else "feat: implement changes"

    # 커밋 메시지 최대 길이 보정
    if len(commit_message.split("\n")[0]) > 72:
        first_line = commit_message.split("\n")[0][:72]
        rest = "\n".join(commit_message.split("\n")[1:])
        commit_message = first_line + ("\n" + rest if rest else "")

    updated_coder_output = {
        **coder_output,
        "commit_message_draft": commit_message,
        "refactor_notes": refactor_notes,
        "refactored_files": successfully_refactored,
    }

    return {"coder_output": updated_coder_output}
