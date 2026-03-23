from typing import TypedDict, Annotated, List, Optional
import operator


class PlannerState(TypedDict):
    """Planner Team 내부 상태"""
    codebase_summary: str
    file_tree: str
    dependencies: str
    task_list: List[dict]  # 원자 단위 작업 지시서


class CoderState(TypedDict):
    """Coder Team 내부 상태"""
    current_task: dict
    modified_files: List[str]
    commit_message_draft: str
    iteration: int


class TesterState(TypedDict):
    """Tester Team 내부 상태"""
    test_results: List[dict]
    security_issues: List[dict]
    verdict: str  # "pass" | "fail"
    feedback: str


class LockyGlobalState(TypedDict):
    """전체 파이프라인 전역 상태"""
    cmd: str                                               # 사용자 입력 명령
    messages: Annotated[List[str], operator.add]           # 대화 기록
    planner_output: Optional[PlannerState]
    coder_output: Optional[CoderState]
    tester_output: Optional[TesterState]
    current_stage: str                                     # "planning" | "coding" | "testing" | "complete" | "failed"
    retry_count: int
    final_report: str
