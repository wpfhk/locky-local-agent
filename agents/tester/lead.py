"""Tester Lead — Tester Team LangGraph 노드."""

from __future__ import annotations

import time
from typing import List

from states.state import LockyGlobalState, TesterState
from agents.tester.qa_validator import validate_quality
from agents.tester.security_auditor import audit_security


def _build_feedback(
    test_results: List[dict],
    security_issues: List[dict],
    modified_files: List[str],
) -> str:
    """Coder에게 전달할 구체적인 피드백 문자열을 생성합니다."""
    lines: List[str] = ["## 검증 실패 — 수정 가이드라인\n"]

    # 테스트 실패 피드백
    test_failures = [
        detail
        for r in test_results
        for detail in r.get("failed_details", [])
    ]
    if test_failures:
        lines.append("### 실패한 테스트")
        for detail in test_failures:
            lines.append(f"- **{detail.get('test_name', '알 수 없음')}**")
            lines.append(f"  - 파일: {detail.get('file', '')}")
            lines.append(f"  - 오류: {detail.get('error', '')}")
            lines.append(f"  - 수정 방향: {detail.get('suggestion', '')}")
        lines.append("")

    # 보안 이슈 피드백
    critical_high = [i for i in security_issues if i.get("severity") in ("critical", "high")]
    if critical_high:
        lines.append("### Critical/High 보안 이슈 (즉시 수정 필요)")
        for issue in critical_high:
            lines.append(
                f"- **[{issue.get('severity', '').upper()}] {issue.get('category', '')}**"
            )
            lines.append(f"  - 파일: {issue.get('file', '')} (라인 {issue.get('line', 0)})")
            lines.append(f"  - 코드: `{issue.get('code_snippet', '')}`")
            lines.append(f"  - 설명: {issue.get('description', '')}")
            lines.append(f"  - 권고: {issue.get('recommendation', '')}")
        lines.append("")

    if not test_failures and not critical_high:
        lines.append("검증 실패 원인을 확인하고 코드를 재검토하세요.")

    return "\n".join(lines)


def tester_lead(state: LockyGlobalState) -> dict:
    """
    Tester Lead LangGraph 노드.

    qa_validator와 security_auditor를 순차 실행하여 검증 결과를 통합하고
    pass/fail 판정 및 피드백을 생성합니다.

    Args:
        state: 전역 파이프라인 상태

    Returns:
        tester_output과 current_stage를 포함한 dict
    """
    stage_start = time.time()
    print("\n[Tester] ─── Stage 3: Testing ───────────────────────")
    print("[Tester] 품질 검증 시작...")

    # Step 1: QA 검증 (단위 테스트 생성 및 실행)
    t0 = time.time()
    qa_result = validate_quality(state)
    print(f"[Tester] QA 검증 완료 ({time.time() - t0:.1f}s)")

    # 중간 상태 병합
    intermediate_state: LockyGlobalState = {
        **state,
        **qa_result,
    }

    # Step 2: 보안 감사
    print("[Tester] 보안 감사 중...")
    t0 = time.time()
    security_result = audit_security(intermediate_state)
    print(f"[Tester] 보안 감사 완료 ({time.time() - t0:.1f}s)")

    # 최종 tester_output 통합
    final_tester_output = {
        **(qa_result.get("tester_output") or {}),
        **(security_result.get("tester_output") or {}),
    }

    test_results: List[dict] = final_tester_output.get("test_results", [])
    security_issues: List[dict] = final_tester_output.get("security_issues", [])
    coder_output = state.get("coder_output") or {}
    modified_files: List[str] = coder_output.get("modified_files", [])

    # Verdict 결정
    # Fail 조건: critical/high 보안 이슈 OR 테스트 실패
    has_critical_high = any(
        i.get("severity") in ("critical", "high") for i in security_issues
    )
    has_test_failure = any(
        r.get("status") == "fail" or r.get("failed", 0) > 0 or r.get("error", 0) > 0
        for r in test_results
    )

    verdict = "fail" if (has_critical_high or has_test_failure) else "pass"

    # 피드백 생성 (fail인 경우)
    feedback = ""
    if verdict == "fail":
        feedback = _build_feedback(test_results, security_issues, modified_files)

    # 통계
    pytest_summary = final_tester_output.get("pytest_summary", {})
    total_passed = pytest_summary.get("passed", 0)
    total_failed = pytest_summary.get("failed", 0) + pytest_summary.get("error", 0)
    security_summary = final_tester_output.get("security_summary", {})

    # 최종 tester_output 완성
    final_tester_output.update({
        "verdict": verdict,
        "feedback": feedback,
    })

    elapsed = time.time() - stage_start
    verdict_icon = "✓" if verdict == "pass" else "✗"
    print(f"[Tester] 검증 완료: {verdict_icon} {verdict.upper()} — 총 {elapsed:.1f}s")

    return {
        "tester_output": final_tester_output,
        "current_stage": "complete" if verdict == "pass" else "coding",
        "retry_count": state.get("retry_count", 0) + (1 if verdict == "fail" else 0),
        "final_report": (
            f"검증 완료 — verdict: {verdict} | "
            f"테스트 pass={total_passed}, fail={total_failed} | "
            f"보안 critical={security_summary.get('critical', 0)}, "
            f"high={security_summary.get('high', 0)}"
        ),
        "messages": [
            f"[Tester] 검증 완료: {verdict.upper()} "
            f"(테스트 통과={total_passed}, 실패={total_failed}, "
            f"보안이슈={len(security_issues)}개, {elapsed:.1f}s)"
        ],
    }
