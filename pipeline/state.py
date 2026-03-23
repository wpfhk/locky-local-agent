"""파이프라인 실행 상태 관리 모듈."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

PIPELINE_DIR = Path(".pipeline/runs")

PipelineStatus = Literal["initialized", "planning", "coding", "testing", "complete", "failed"]


def _run_dir(run_id: str) -> Path:
    return PIPELINE_DIR / run_id


def init_run(requirements: str) -> str:
    """새로운 파이프라인 실행을 초기화하고 run_id를 반환합니다."""
    run_id = datetime.now(tz=timezone.utc).strftime("run_%Y%m%d_%H%M%S")
    run_path = _run_dir(run_id)
    run_path.mkdir(parents=True, exist_ok=True)

    state: dict[str, Any] = {
        "run_id": run_id,
        "requirements": requirements,
        "status": "initialized",
        "iteration": 0,
        "max_iterations": 3,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    _write_state(run_id, state)
    return run_id


def advance_stage(run_id: str, completed_stage: PipelineStatus) -> None:
    """완료된 단계를 기록하고 다음 단계로 상태를 전환합니다."""
    state = load_state(run_id)

    next_status_map: dict[str, PipelineStatus] = {
        "initialized": "planning",
        "planning": "coding",
        "coding": "testing",
        "testing": "complete",
    }

    state["status"] = next_status_map.get(completed_stage, completed_stage)
    state["updated_at"] = datetime.now(tz=timezone.utc).isoformat()

    if completed_stage == "coding":
        state["iteration"] = state.get("iteration", 0) + 1

    _write_state(run_id, state)


def mark_failed(run_id: str, reason: str = "") -> None:
    """파이프라인을 실패 상태로 표시합니다."""
    state = load_state(run_id)
    state["status"] = "failed"
    state["failure_reason"] = reason
    state["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    _write_state(run_id, state)


def mark_complete(run_id: str) -> None:
    """파이프라인을 완료 상태로 표시합니다."""
    state = load_state(run_id)
    state["status"] = "complete"
    state["completed_at"] = datetime.now(tz=timezone.utc).isoformat()
    state["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    _write_state(run_id, state)


def load_state(run_id: str) -> dict[str, Any]:
    """현재 파이프라인 상태를 로드합니다."""
    path = _run_dir(run_id) / "state.json"
    if not path.exists():
        raise FileNotFoundError(f"State file not found: {path}")
    with open(path) as f:
        return json.load(f)


def load_artifact(run_id: str, artifact: str) -> dict[str, Any]:
    """파이프라인 아티팩트(plan, code_result, test_result)를 로드합니다."""
    path = _run_dir(run_id) / artifact
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {path}")
    with open(path) as f:
        return json.load(f)


def save_artifact(run_id: str, artifact: str, data: dict[str, Any]) -> None:
    """파이프라인 아티팩트를 저장합니다."""
    path = _run_dir(run_id) / artifact
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _write_state(run_id: str, state: dict[str, Any]) -> None:
    path = _run_dir(run_id) / "state.json"
    with open(path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def should_retry(run_id: str) -> bool:
    """최대 반복 횟수 내에 재시도 가능한지 확인합니다."""
    state = load_state(run_id)
    return state.get("iteration", 0) < state.get("max_iterations", 3)


def list_runs() -> list[dict[str, Any]]:
    """모든 파이프라인 실행 목록을 반환합니다."""
    if not PIPELINE_DIR.exists():
        return []

    runs = []
    for run_dir in sorted(PIPELINE_DIR.iterdir(), reverse=True):
        state_file = run_dir / "state.json"
        if state_file.exists():
            with open(state_file) as f:
                runs.append(json.load(f))
    return runs
