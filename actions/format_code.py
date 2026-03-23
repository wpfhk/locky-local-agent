"""actions/format_code.py — black, isort, flake8을 실행합니다."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def run(
    root: Path,
    check_only: bool = False,
    paths: Optional[List[str]] = None,
) -> dict:
    """
    black, isort, flake8을 실행합니다.

    Args:
        root: 프로젝트 루트 Path
        check_only: True면 수정하지 않고 검사만 수행
        paths: 대상 경로 목록 (None이면 전체)

    Returns:
        {"status": "ok"|"error", "black": {...}, "isort": {...}, "flake8": {...}}
    """
    root = Path(root).resolve()
    target_paths = paths if paths else [str(root)]

    black_result = _run_black(root, target_paths, check_only)
    isort_result = _run_isort(root, target_paths, check_only)
    flake8_result = _run_flake8(root, target_paths)

    # 전체 상태: 하나라도 error면 error
    has_error = any(
        r.get("status") == "error"
        for r in [black_result, isort_result, flake8_result]
        if r.get("status") != "not_installed"
    )

    return {
        "status": "error" if has_error else "ok",
        "black": black_result,
        "isort": isort_result,
        "flake8": flake8_result,
    }


def _run_tool(
    name: str,
    cmd: List[str],
    cwd: Path,
    timeout: int = 120,
) -> dict:
    """공통 subprocess 실행 헬퍼."""
    if not shutil.which(name):
        return {"status": "not_installed", "output": f"{name}이 설치되지 않았습니다."}

    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "output": output,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": f"{name} 타임아웃 ({timeout}s)"}
    except Exception as exc:
        return {"status": "error", "output": str(exc)}


def _run_black(root: Path, target_paths: List[str], check_only: bool) -> dict:
    cmd = ["black"]
    if check_only:
        cmd.append("--check")
    cmd += target_paths
    return _run_tool("black", cmd, root)


def _run_isort(root: Path, target_paths: List[str], check_only: bool) -> dict:
    cmd = ["isort"]
    if check_only:
        cmd.append("--check-only")
    cmd += target_paths
    return _run_tool("isort", cmd, root)


def _run_flake8(root: Path, target_paths: List[str]) -> dict:
    cmd = ["flake8"] + target_paths
    return _run_tool("flake8", cmd, root)
