"""actions/test_runner.py — pytest를 실행하고 결과를 리포트합니다."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional


def run(
    root: Path,
    path: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    pytest를 실행하고 결과를 리포트합니다.

    Args:
        root: 프로젝트 루트 Path
        path: 특정 테스트 경로 (None이면 전체)
        verbose: True면 -v 옵션 추가

    Returns:
        {"status": "pass"|"fail"|"error", "passed": int, "failed": int,
         "errors": int, "duration": float, "output": str}
    """
    root = Path(root).resolve()

    if not shutil.which("pytest"):
        return {
            "status": "error",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "duration": 0.0,
            "output": "pytest가 설치되지 않았습니다.",
        }

    cmd = ["pytest"]
    if verbose:
        cmd.append("-v")
    if path:
        cmd.append(path)

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
        )
        duration = time.time() - t0
        output = (result.stdout + result.stderr).strip()

        passed, failed, errors = _parse_pytest_output(output)

        if result.returncode == 0:
            status = "pass"
        elif result.returncode == 1:
            status = "fail"
        else:
            status = "error"

        return {
            "status": status,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "duration": round(duration, 2),
            "output": output,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "duration": round(time.time() - t0, 2),
            "output": "pytest 타임아웃 (120s)",
        }
    except Exception as exc:
        return {
            "status": "error",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "duration": round(time.time() - t0, 2),
            "output": str(exc),
        }


def _parse_pytest_output(output: str) -> tuple[int, int, int]:
    """pytest 출력에서 passed/failed/errors 수를 파싱합니다."""
    passed = 0
    failed = 0
    errors = 0

    # 예: "3 passed, 1 failed, 2 errors in 0.5s"
    match = re.search(
        r"(?:(\d+) passed)?.*?(?:(\d+) failed)?.*?(?:(\d+) error)?",
        output,
        re.IGNORECASE,
    )
    if match:
        passed = int(match.group(1) or 0)
        failed = int(match.group(2) or 0)
        errors = int(match.group(3) or 0)

    # 더 정확한 파싱 시도
    p_match = re.search(r"(\d+) passed", output)
    f_match = re.search(r"(\d+) failed", output)
    e_match = re.search(r"(\d+) error", output)

    if p_match:
        passed = int(p_match.group(1))
    if f_match:
        failed = int(f_match.group(1))
    if e_match:
        errors = int(e_match.group(1))

    return passed, failed, errors
