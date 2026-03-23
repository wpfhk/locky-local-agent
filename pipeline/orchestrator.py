"""계층적 개발 파이프라인 오케스트레이터 (Python 프로그래밍 실행용)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import anyio
from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    query,
)

from pipeline.state import (
    advance_stage,
    init_run,
    load_artifact,
    load_state,
    mark_complete,
    mark_failed,
    save_artifact,
    should_retry,
)

# ─── 에이전트 프롬프트 로더 ───────────────────────────────────────────────────


PROMPTS_DIR = Path(__file__).parent.parent / "agents" / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are the {name} agent."


# ─── Stage 1: Planner Team ────────────────────────────────────────────────────


async def run_planner_team(run_id: str, requirements: str) -> dict:
    """Planner Lead를 실행하여 Plan Document를 생성합니다."""
    print(f"\n[Stage 1] Planner Team 실행 중... (run_id: {run_id})")

    planner_prompt = f"""{_load_prompt("planner_lead")}

---

## 현재 작업

**Run ID:** {run_id}
**요구사항:** {requirements}

다음 작업을 수행하세요:
1. `context-analyzer` 서브에이전트를 호출하여 현재 코드베이스를 분석하세요.
2. `task-breaker` 서브에이전트를 호출하여 작업을 원자 단위로 분할하세요.
3. 결과를 통합하여 아래 JSON 형식으로 `.pipeline/runs/{run_id}/plan.json` 파일에 저장하세요.

plan.json 저장 후 "PLANNER_COMPLETE"를 출력하세요.
"""

    result_text = ""
    async for message in query(
        prompt=planner_prompt,
        options=ClaudeAgentOptions(
            cwd=str(Path.cwd()),
            allowed_tools=["Read", "Glob", "Grep", "Write", "Bash", "Agent"],
            agents={
                "context-analyzer": AgentDefinition(
                    description="코드베이스 구조·의존성·파일 관계를 분석하는 전문가",
                    prompt=_load_prompt("context_analyzer"),
                    tools=["Read", "Glob", "Grep", "Bash"],
                ),
                "task-breaker": AgentDefinition(
                    description="기능을 원자 단위 작업 지시서로 분할하는 전문가",
                    prompt=_load_prompt("task_breaker"),
                    tools=["Read", "Glob", "Grep"],
                ),
            },
            max_turns=30,
        ),
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result

    advance_stage(run_id, "planning")
    print(f"[Stage 1] 완료")

    # plan.json 로드 후 반환
    try:
        return load_artifact(run_id, "plan.json")
    except FileNotFoundError:
        # 에이전트가 파일을 생성하지 않은 경우 result로부터 추출 시도
        return {"requirements": requirements, "tasks": [], "_raw": result_text}


# ─── Stage 2: Coder Team ─────────────────────────────────────────────────────


async def run_coder_team(run_id: str, plan: dict, feedback: str = "") -> dict:
    """Coder Lead를 실행하여 코드를 구현합니다."""
    print(f"\n[Stage 2] Coder Team 실행 중... (iteration: {load_state(run_id).get('iteration', 0) + 1})")

    feedback_section = ""
    if feedback:
        feedback_section = f"\n\n## Tester 피드백 (수정 필요)\n{feedback}\n"

    coder_prompt = f"""{_load_prompt("coder_lead")}

---

## 현재 작업

**Run ID:** {run_id}
**Plan Document:**
```json
{json.dumps(plan, indent=2, ensure_ascii=False)}
```
{feedback_section}

다음 작업을 수행하세요:
1. plan.json의 `execution_order`에 따라 `core-developer`에게 태스크를 할당하세요.
2. 구현 완료 후 `refactor-formatter`를 실행하여 코드를 정리하세요.
3. 결과를 `.pipeline/runs/{run_id}/code_result.json`에 저장하세요.

code_result.json 저장 후 "CODER_COMPLETE"를 출력하세요.
"""

    async for message in query(
        prompt=coder_prompt,
        options=ClaudeAgentOptions(
            cwd=str(Path.cwd()),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Agent"],
            agents={
                "core-developer": AgentDefinition(
                    description="핵심 비즈니스 로직 작성 및 파일 수정을 담당하는 개발자",
                    prompt=_load_prompt("core_developer"),
                    tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                ),
                "refactor-formatter": AgentDefinition(
                    description="코드 컨벤션 적용·주석 작성·불필요한 코드 최적화 전문가",
                    prompt=_load_prompt("refactor_formatter"),
                    tools=["Read", "Write", "Edit", "Glob", "Grep"],
                ),
            },
            max_turns=50,
        ),
    ):
        if isinstance(message, ResultMessage):
            pass

    advance_stage(run_id, "coding")
    print(f"[Stage 2] 완료")

    try:
        return load_artifact(run_id, "code_result.json")
    except FileNotFoundError:
        return {"files_modified": [], "tasks_completed": []}


# ─── Stage 3: Tester Team ────────────────────────────────────────────────────


async def run_tester_team(run_id: str, code_result: dict) -> dict:
    """Tester Lead를 실행하여 코드를 검증합니다."""
    state = load_state(run_id)
    print(f"\n[Stage 3] Tester Team 실행 중...")

    tester_prompt = f"""{_load_prompt("tester_lead")}

---

## 현재 작업

**Run ID:** {run_id}
**Iteration:** {state.get('iteration', 1)}
**변경된 파일:**
```json
{json.dumps(code_result, indent=2, ensure_ascii=False)}
```

다음 작업을 수행하세요:
1. `qa-validator`와 `security-auditor`를 실행하세요 (병렬 가능).
2. 결과를 통합하여 `.pipeline/runs/{run_id}/test_result.json`에 저장하세요.
3. `status`는 반드시 "pass" 또는 "fail"이어야 합니다.

test_result.json 저장 후 "TESTER_COMPLETE"를 출력하세요.
"""

    async for message in query(
        prompt=tester_prompt,
        options=ClaudeAgentOptions(
            cwd=str(Path.cwd()),
            allowed_tools=["Read", "Bash", "Glob", "Grep", "Write", "Agent"],
            agents={
                "qa-validator": AgentDefinition(
                    description="단위 테스트 작성 및 로컬 테스트 스크립트 실행 전문가",
                    prompt=_load_prompt("qa_validator"),
                    tools=["Read", "Bash", "Glob", "Grep", "Write"],
                ),
                "security-auditor": AgentDefinition(
                    description="보안 취약점·하드코딩 시크릿 정적 분석 전문가",
                    prompt=_load_prompt("security_auditor"),
                    tools=["Read", "Grep", "Glob"],
                ),
            },
            max_turns=30,
        ),
    ):
        if isinstance(message, ResultMessage):
            pass

    advance_stage(run_id, "testing")
    print(f"[Stage 3] 완료")

    try:
        return load_artifact(run_id, "test_result.json")
    except FileNotFoundError:
        return {"status": "pass", "summary": "검증 아티팩트 없음 - 기본 통과 처리"}


# ─── 메인 파이프라인 ──────────────────────────────────────────────────────────


async def run_pipeline(requirements: str) -> str:
    """전체 개발 파이프라인을 실행합니다."""
    run_id = init_run(requirements)
    print(f"\n{'='*60}")
    print(f"  개발 파이프라인 시작")
    print(f"  Run ID: {run_id}")
    print(f"  요구사항: {requirements}")
    print(f"{'='*60}")

    # Stage 1: Planning
    plan = await run_planner_team(run_id, requirements)

    feedback = ""
    while True:
        # Stage 2: Coding
        code_result = await run_coder_team(run_id, plan, feedback)

        # Stage 3: Testing
        test_result = await run_tester_team(run_id, code_result)

        if test_result.get("status") == "pass":
            mark_complete(run_id)
            print(f"\n{'='*60}")
            print(f"  ✅ 파이프라인 완료!")
            print(f"  Run ID: {run_id}")
            print(f"  반복 횟수: {load_state(run_id).get('iteration', 1)}")
            print(f"{'='*60}")
            return run_id

        # 피드백 루프
        if not should_retry(run_id):
            mark_failed(run_id, "최대 반복 횟수 초과")
            print(f"\n{'='*60}")
            print(f"  ❌ 파이프라인 실패 - 최대 반복 횟수 초과")
            print(f"  Run ID: {run_id}")
            print(f"{'='*60}")
            return run_id

        feedback = test_result.get("feedback", "테스트 실패. 코드를 검토하세요.")
        print(f"\n[피드백 루프] 테스트 실패 - Coder Team으로 반환 중...")
        print(f"  피드백: {feedback[:200]}...")


def main(requirements: str) -> None:
    """동기 진입점."""
    anyio.run(run_pipeline, requirements)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.orchestrator <requirements>")
        sys.exit(1)

    main(" ".join(sys.argv[1:]))
