"""Planner Lead — Planner Team LangGraph 노드."""

from __future__ import annotations

from states.state import LockyGlobalState
from agents.planner.context_analyzer import analyze_context
from agents.planner.task_breaker import break_tasks


def planner_lead(state: LockyGlobalState) -> dict:
    """
    Planner Lead LangGraph 노드.

    context_analyzer → task_breaker 순으로 실행하여 작업 계획을 수립하고
    current_stage를 "coding"으로 전환합니다.

    Args:
        state: 전역 파이프라인 상태

    Returns:
        통합된 planner_output과 current_stage("coding")을 포함한 dict
    """
    print("[Planner] 코드베이스 분석 시작...")

    # Step 1: 코드베이스 분석
    context_result = analyze_context(state)

    # 분석 결과를 state에 병합하여 task_breaker에 전달
    intermediate_state: LockyGlobalState = {
        **state,
        **context_result,
    }

    # Step 2: 태스크 분할
    print("[Planner] 태스크 분할 중...")
    task_result = break_tasks(intermediate_state)

    # 최종 planner_output 통합
    final_planner_output = {
        **(context_result.get("planner_output") or {}),
        **(task_result.get("planner_output") or {}),
    }

    task_list = final_planner_output.get("task_list", [])
    task_count = len(task_list)

    print(f"[Planner] 분석 완료: {task_count}개 태스크 도출")

    return {
        "planner_output": final_planner_output,
        "current_stage": "coding",
        "messages": [
            f"[Planner] 코드베이스 분석 및 {task_count}개 태스크 도출 완료"
        ],
    }
