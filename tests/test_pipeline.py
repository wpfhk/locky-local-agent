"""actions/pipeline.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from actions.pipeline import _STEP_RUNNERS, run

# ── 입력 검증 ─────────────────────────────────────────────────────────────────


def test_run_empty_steps_returns_error(tmp_path: Path):
    result = run(tmp_path, steps="")
    assert result["status"] == "error"
    assert result["executed"] == 0


def test_run_whitespace_only_steps_returns_error(tmp_path: Path):
    result = run(tmp_path, steps="   ")
    assert result["status"] == "error"


def test_run_unknown_step_returns_error(tmp_path: Path):
    result = run(tmp_path, steps="format bogus_step")
    assert result["status"] == "error"
    assert "bogus_step" in result["message"]
    assert result["executed"] == 0


def test_run_step_runners_covers_known_steps(tmp_path: Path):
    """모든 _STEP_RUNNERS 키가 actions 모듈에 해당 함수를 갖는다."""
    import actions

    for step, runner_name in _STEP_RUNNERS.items():
        assert hasattr(
            actions, runner_name
        ), f"actions.{runner_name} not found for step '{step}'"


# ── 단일 단계 실행 ────────────────────────────────────────────────────────────


def test_run_single_step_ok(tmp_path: Path):
    mock_result = {"status": "ok", "message": "done"}

    with patch("actions.format_code", return_value=mock_result):
        result = run(tmp_path, steps="format")

    assert result["status"] == "ok"
    assert result["executed"] == 1
    assert result["total"] == 1
    assert result["failed_at"] is None


def test_run_single_step_failure(tmp_path: Path):
    mock_result = {"status": "error", "message": "failed"}

    with patch("actions.format_code", return_value=mock_result):
        result = run(tmp_path, steps="format")

    assert result["status"] == "error"
    assert result["failed_at"] == "format"
    assert result["executed"] == 1


# ── 멀티 단계 + fail_fast ────────────────────────────────────────────────────


def test_run_multi_step_all_ok(tmp_path: Path):
    ok = {"status": "ok"}

    with patch("actions.format_code", return_value=ok):
        with patch("actions.test_runner", return_value=ok):
            result = run(tmp_path, steps="format test")

    assert result["status"] == "ok"
    assert result["executed"] == 2
    assert result["failed_at"] is None


def test_run_fail_fast_stops_at_first_failure(tmp_path: Path):
    ok = {"status": "ok"}
    fail = {"status": "error", "message": "oops"}

    with patch("actions.format_code", return_value=fail):
        with patch("actions.test_runner", return_value=ok):
            result = run(tmp_path, steps="format test", fail_fast=True)

    assert result["failed_at"] == "format"
    assert result["executed"] == 1  # test는 실행 안 됨


def test_run_no_fail_fast_continues_after_failure(tmp_path: Path):
    ok = {"status": "ok"}
    fail = {"status": "error", "message": "oops"}

    with patch("actions.format_code", return_value=fail):
        with patch("actions.test_runner", return_value=ok):
            result = run(tmp_path, steps="format test", fail_fast=False)

    assert result["executed"] == 2  # 두 단계 모두 실행


def test_run_partial_status_when_some_steps_executed(tmp_path: Path):
    ok = {"status": "ok"}
    fail = {"status": "error"}

    # 3단계 중 1단계 성공 후 2단계 실패 → partial
    with patch("actions.format_code", return_value=ok):
        with patch("actions.test_runner", return_value=fail):
            with patch("actions.commit", return_value=ok):
                result = run(tmp_path, steps="format test commit", fail_fast=True)

    assert result["status"] == "partial"
    assert result["executed"] == 2


# ── 결과 구조 ──────────────────────────────────────────────────────────────────


def test_run_results_contain_step_key(tmp_path: Path):
    ok = {"status": "ok"}

    with patch("actions.format_code", return_value=ok):
        with patch("actions.test_runner", return_value=ok):
            result = run(tmp_path, steps="format test")

    for step_result in result["results"]:
        assert "step" in step_result
        assert "status" in step_result


def test_run_results_order_preserved(tmp_path: Path):
    ok = {"status": "ok"}

    with patch("actions.format_code", return_value=ok):
        with patch("actions.test_runner", return_value=ok):
            with patch("actions.commit", return_value=ok):
                result = run(tmp_path, steps="format test commit")

    steps = [r["step"] for r in result["results"]]
    assert steps == ["format", "test", "commit"]


# ── nothing_to_commit 은 성공으로 처리 ─────────────────────────────────────────


def test_run_nothing_to_commit_is_not_failure(tmp_path: Path):
    ntc = {"status": "nothing_to_commit"}

    with patch("actions.commit", return_value=ntc):
        result = run(tmp_path, steps="commit")

    assert result["status"] == "ok"
    assert result["failed_at"] is None


# ── 예외 처리 ──────────────────────────────────────────────────────────────────


def test_run_exception_in_runner_captured(tmp_path: Path):
    with patch("actions.format_code", side_effect=RuntimeError("boom")):
        result = run(tmp_path, steps="format")

    assert result["status"] == "error"
    assert result["results"][0]["status"] == "error"
