"""Planner Lead — Planner Team LangGraph 노드."""

from __future__ import annotations

import time

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
    stage_start = time.time()
    print("\n[Planner] ─── Stage 1: Planning ───────────────────")
    print("[Planner] 코드베이스 분석 시작...")

    # Step 1: 코드베이스 분석
    t0 = time.time()
    context_result = analyze_context(state)
    print(f"[Planner] 컨텍스트 분석 완료 ({time.time() - t0:.1f}s)")

    # 분석 결과를 state에 병합하여 task_breaker에 전달
    intermediate_state: LockyGlobalState = {
        **state,
        **context_result,
    }

    # Step 2: 태스크 분할
    print("[Planner] 태스크 분할 중...")
    t0 = time.time()
    task_result = break_tasks(intermediate_state)
    print(f"[Planner] 태스크 분할 완료 ({time.time() - t0:.1f}s)")

    # 최종 planner_output 통합
    final_planner_output = {
        **(context_result.get("planner_output") or {}),
        **(task_result.get("planner_output") or {}),
    }

    task_list = final_planner_output.get("task_list", [])
    task_count = len(task_list)

    elapsed = time.time() - stage_start
    print(f"[Planner] 분석 완료: {task_count}개 태스크 도출 — 총 {elapsed:.1f}s")

    return {
        "planner_output": final_planner_output,
        "current_stage": "coding",
        "messages": [
            f"[Planner] 코드베이스 분석 및 {task_count}개 태스크 도출 완료 ({elapsed:.1f}s)"
        ],
    }
