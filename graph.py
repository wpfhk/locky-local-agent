"""LangGraph 메인 그래프 — Locky 개발 파이프라인."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langgraph.graph import END, START, StateGraph

from agents.coder.lead import coder_lead
from agents.planner.lead import planner_lead
from agents.tester.lead import tester_lead
from config import MAX_RETRY_ITERATIONS
from states.state import LockyGlobalState


def should_continue(state: LockyGlobalState) -> str:
    """
    Tester 결과에 따른 조건부 엣지 라우터.

    Returns:
        "end"   — verdict == "pass" 또는 retry_count >= MAX_RETRY_ITERATIONS
        "retry" — verdict == "fail" (Coder로 피드백 루프)
    """
    tester_output = state.get("tester_output") or {}
    verdict = tester_output.get("verdict", "pass")
    retry_count = state.get("retry_count", 0)

    if verdict == "pass" or retry_count >= MAX_RETRY_ITERATIONS:
        return "end"
    return "retry"


def build_graph() -> StateGraph:
    """
    LangGraph 그래프를 빌드하고 컴파일하여 반환합니다.

    Pipeline:
        START → planner_lead → coder_lead → tester_lead
                                    ↑              |
                                    └── (fail) ────┘
                                    END ← (pass or max retry)
    """
    graph = StateGraph(LockyGlobalState)

    # 노드 등록
    graph.add_node("planner_lead", planner_lead)
    graph.add_node("coder_lead", coder_lead)
    graph.add_node("tester_lead", tester_lead)

    # 고정 엣지
    graph.add_edge(START, "planner_lead")
    graph.add_edge("planner_lead", "coder_lead")
    graph.add_edge("coder_lead", "tester_lead")

    # 조건부 엣지: tester_lead → END 또는 coder_lead (피드백 루프)
    graph.add_conditional_edges(
        "tester_lead",
        should_continue,
        {
            "end": END,
            "retry": "coder_lead",
        },
    )

    return graph.compile()


def run(cmd: str) -> dict:
    """
    초기 상태를 생성하고 그래프를 실행합니다.

    Args:
        cmd: 사용자 입력 요구사항 문자열

    Returns:
        최종 LockyGlobalState 딕셔너리
    """
    initial_state: LockyGlobalState = {
        "cmd": cmd,
        "messages": [],
        "planner_output": None,
        "coder_output": None,
        "tester_output": None,
        "current_stage": "planning",
        "retry_count": 0,
        "final_report": "",
    }

    compiled = build_graph()
    result = compiled.invoke(initial_state)
    return result


def run_with_root(cmd: str, root: Optional[Path | str] = None) -> dict:
    """
    지정한 MCP 파일시스템 루트에서 파이프라인을 실행합니다.
    executor 스레드 등에서도 동일 루트가 적용되도록 컨텍스트로 고정합니다.

    Args:
        cmd: 사용자 요구사항
        root: None이면 현재 환경/기본 루트 사용
    """
    from locky_cli.fs_context import filesystem_root_context

    if root is None:
        return run(cmd)
    with filesystem_root_context(Path(root)):
        return run(cmd)
