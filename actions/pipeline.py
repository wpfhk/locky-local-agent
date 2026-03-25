"""actions/pipeline.py — 여러 locky 명령을 순서대로 실행합니다. (v0.5.0)"""

from __future__ import annotations

from pathlib import Path

# 지원되는 파이프라인 단계 → actions 함수 매핑
_STEP_RUNNERS: dict[str, str] = {
    "format": "format_code",
    "test": "test_runner",
    "scan": "security_scan",
    "commit": "commit",
    "clean": "cleanup",
    "deps": "deps_check",
    "env": "env_template",
    "todo": "todo_collector",
}


def run(
    root: Path,
    steps: str = "",
    fail_fast: bool = True,
    **opts,
) -> dict:
    """여러 locky 명령을 순서대로 실행합니다.

    Args:
        root: 프로젝트 루트 Path
        steps: 공백 구분 명령어 문자열 (예: "format test commit")
        fail_fast: True면 하나라도 실패 시 즉시 중단 (기본: True)

    Returns:
        {
            "status": "ok"|"partial"|"error",
            "results": [{"step": str, "status": str, ...}, ...],
            "failed_at": str | None,
            "executed": int,
            "total": int,
        }
    """
    root = Path(root).resolve()
    step_list = [s.strip() for s in steps.split() if s.strip()]

    if not step_list:
        return {
            "status": "error",
            "message": "실행할 단계가 없습니다. 예: 'format test commit'",
            "results": [],
            "failed_at": None,
            "executed": 0,
            "total": 0,
        }

    # 유효하지 않은 단계 사전 검증
    unknown = [s for s in step_list if s not in _STEP_RUNNERS]
    if unknown:
        return {
            "status": "error",
            "message": f"알 수 없는 단계: {', '.join(unknown)}. 사용 가능: {', '.join(_STEP_RUNNERS)}",
            "results": [],
            "failed_at": None,
            "executed": 0,
            "total": len(step_list),
        }

    results: list[dict] = []
    failed_at: str | None = None

    for step in step_list:
        runner_name = _STEP_RUNNERS[step]
        try:
            import actions

            runner = getattr(actions, runner_name)
            result = runner(root)
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}

        step_result = {"step": step, **result}
        results.append(step_result)

        step_status = result.get("status", "error")
        if step_status not in ("ok", "pass", "clean", "nothing_to_commit"):
            failed_at = step
            if fail_fast:
                break

    executed = len(results)
    total = len(step_list)

    if failed_at is not None:
        overall = "partial" if executed > 1 else "error"
    else:
        overall = "ok"

    return {
        "status": overall,
        "results": results,
        "failed_at": failed_at,
        "executed": executed,
        "total": total,
    }
