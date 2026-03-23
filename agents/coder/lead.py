"""Coder Lead — Coder Team LangGraph 노드."""

from __future__ import annotations

from states.state import LockyGlobalState
from agents.coder.core_developer import develop_code
from agents.coder.refactor_formatter import refactor_and_format


def coder_lead(state: LockyGlobalState) -> dict:
    """
    Coder Lead LangGraph 노드.

    core_developer → refactor_formatter 순으로 실행하여 코드를 구현 및 정리하고
    current_stage를 "testing"으로 전환합니다.

    Args:
        state: 전역 파이프라인 상태

    Returns:
        통합된 coder_output과 current_stage("testing")을 포함한 dict
    """
    print("[Coder] 코드 구현 시작...")

    # Step 1: 핵심 코드 구현
    dev_result = develop_code(state)

    # 중간 상태 병합
    intermediate_state: LockyGlobalState = {
        **state,
        **dev_result,
    }

    # Step 2: 리팩토링 및 포매팅
    print("[Coder] 리팩토링 및 포매팅 중...")
    refactor_result = refactor_and_format(intermediate_state)

    # 최종 coder_output 통합
    final_coder_output = {
        **(dev_result.get("coder_output") or {}),
        **(refactor_result.get("coder_output") or {}),
    }

    modified_files = final_coder_output.get("modified_files", [])
    file_count = len(modified_files)

    print(f"[Coder] 구현 완료: {file_count}개 파일 수정")

    return {
        "coder_output": final_coder_output,
        "current_stage": "testing",
        "messages": [
            f"[Coder] 코드 구현 및 리팩토링 완료 — {file_count}개 파일 수정"
        ],
    }
