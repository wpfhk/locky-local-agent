"""파이프라인 CLI 실행기 — Claude Code 스킬에서 호출됩니다."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _ensure_pipeline_dir() -> None:
    Path(".pipeline/runs").mkdir(parents=True, exist_ok=True)


def cmd_init(requirements: str) -> None:
    """`init` 명령: 새 파이프라인 실행을 초기화합니다."""
    _ensure_pipeline_dir()

    # state.py 임포트 (파이프라인 디렉토리에서 실행 가정)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.state import init_run

    run_id = init_run(requirements)
    print(run_id)  # Claude Code 스킬이 run_id를 캡처합니다


def cmd_advance(run_id: str, completed_stage: str) -> None:
    """`advance` 명령: 파이프라인 단계를 전진시킵니다."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.state import advance_stage

    advance_stage(run_id, completed_stage)  # type: ignore[arg-type]
    state_file = Path(f".pipeline/runs/{run_id}/state.json")
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
        print(f"Status: {state['status']} | Iteration: {state.get('iteration', 0)}")


def cmd_complete(run_id: str) -> None:
    """`complete` 명령: 파이프라인을 완료 처리합니다."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.state import mark_complete

    mark_complete(run_id)
    print(f"Pipeline {run_id} marked as COMPLETE")


def cmd_fail(run_id: str) -> None:
    """`fail` 명령: 파이프라인을 실패 처리합니다."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.state import mark_failed

    mark_failed(run_id, "최대 반복 횟수 초과")
    print(f"Pipeline {run_id} marked as FAILED")


def cmd_status(run_id: str) -> None:
    """`status` 명령: 현재 파이프라인 상태를 출력합니다."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.state import load_state

    state = load_state(run_id)
    print(json.dumps(state, indent=2, ensure_ascii=False))


def cmd_list() -> None:
    """`list` 명령: 모든 파이프라인 실행 목록을 출력합니다."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.state import list_runs

    runs = list_runs()
    if not runs:
        print("실행된 파이프라인이 없습니다.")
        return

    print(f"{'Run ID':<25} {'Status':<12} {'Iteration':<10} {'Requirements'}")
    print("-" * 80)
    for run in runs:
        req = run.get("requirements", "")[:40]
        print(
            f"{run['run_id']:<25} {run['status']:<12} "
            f"{run.get('iteration', 0):<10} {req}"
        )


def cmd_run(requirements: str) -> None:
    """`run` 명령: Python 오케스트레이터로 전체 파이프라인을 실행합니다."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.orchestrator import main

    main(requirements)


def main_cli() -> None:
    """CLI 진입점."""
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python pipeline/runner.py init <requirements>   # 파이프라인 초기화\n"
            "  python pipeline/runner.py advance <run_id> <stage>  # 단계 전진\n"
            "  python pipeline/runner.py complete <run_id>    # 완료 처리\n"
            "  python pipeline/runner.py fail <run_id>        # 실패 처리\n"
            "  python pipeline/runner.py status <run_id>      # 상태 조회\n"
            "  python pipeline/runner.py list                  # 목록 조회\n"
            "  python pipeline/runner.py run <requirements>   # 전체 실행 (Python SDK)"
        )
        sys.exit(1)

    command = sys.argv[1]

    if command == "init":
        if len(sys.argv) < 3:
            print("Error: requirements 인자가 필요합니다.")
            sys.exit(1)
        cmd_init(" ".join(sys.argv[2:]))

    elif command == "advance":
        if len(sys.argv) < 4:
            print("Error: run_id와 stage 인자가 필요합니다.")
            sys.exit(1)
        cmd_advance(sys.argv[2], sys.argv[3])

    elif command == "complete":
        if len(sys.argv) < 3:
            print("Error: run_id 인자가 필요합니다.")
            sys.exit(1)
        cmd_complete(sys.argv[2])

    elif command == "fail":
        if len(sys.argv) < 3:
            print("Error: run_id 인자가 필요합니다.")
            sys.exit(1)
        cmd_fail(sys.argv[2])

    elif command == "status":
        if len(sys.argv) < 3:
            print("Error: run_id 인자가 필요합니다.")
            sys.exit(1)
        cmd_status(sys.argv[2])

    elif command == "list":
        cmd_list()

    elif command == "run":
        if len(sys.argv) < 3:
            print("Error: requirements 인자가 필요합니다.")
            sys.exit(1)
        cmd_run(" ".join(sys.argv[2:]))

    else:
        print(f"Error: 알 수 없는 명령어 '{command}'")
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
