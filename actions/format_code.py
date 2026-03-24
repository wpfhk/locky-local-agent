"""actions/format_code.py — black, isort, flake8 + 다언어 포맷터 실행. (v0.5.0)"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


# 비-Python 언어별 포맷터 커맨드 (도구명, 추가 인수 리스트)
# 각 항목: (tool_name, [extra_args_before_files])
_LANG_FORMATTERS: dict[str, list[tuple[str, list[str]]]] = {
    "javascript": [("prettier", ["--write"])],
    "typescript": [("prettier", ["--write"]), ("eslint", ["--fix"])],
    "go": [("gofmt", ["-w"])],
    "rust": [("rustfmt", [])],
    "kotlin": [("ktlint", ["-F"])],
    "swift": [("swiftformat", [])],
}


def run(
    root: Path,
    check_only: bool = False,
    paths: Optional[List[str]] = None,
    lang: str = "auto",
) -> dict:
    """black/isort/flake8 또는 언어별 포맷터를 실행합니다.

    Args:
        root: 프로젝트 루트 Path
        check_only: True면 수정하지 않고 검사만 수행 (Python 전용)
        paths: 대상 경로 목록 (None이면 전체 루트)
        lang: 사용할 언어. "auto"면 lang_detect로 자동 감지.

    Returns:
        {"status": "ok"|"error", "language": str, <tool>: {...}, ...}
    """
    root = Path(root).resolve()
    target_paths = paths if paths else [str(root)]

    if lang == "auto":
        try:
            from locky_cli.lang_detect import detect as _detect
            lang = _detect(root).get("primary", "python")
        except Exception:
            lang = "python"

    if lang == "python":
        tools = _run_python(root, target_paths, check_only)
    else:
        tools = _run_lang(root, target_paths, lang)

    has_error = any(
        r.get("status") == "error"
        for r in tools.values()
        if r.get("status") != "not_installed"
    )

    return {
        "status": "error" if has_error else "ok",
        "language": lang,
        **tools,
    }


# ── Python ────────────────────────────────────────────────────────────────────


def _run_python(root: Path, target_paths: list[str], check_only: bool) -> dict:
    return {
        "black": _run_black(root, target_paths, check_only),
        "isort": _run_isort(root, target_paths, check_only),
        "flake8": _run_flake8(root, target_paths),
    }


def _run_black(root: Path, target_paths: list[str], check_only: bool) -> dict:
    cmd = ["black"]
    if check_only:
        cmd.append("--check")
    cmd += target_paths
    return _run_tool("black", cmd, root)


def _run_isort(root: Path, target_paths: list[str], check_only: bool) -> dict:
    cmd = ["isort"]
    if check_only:
        cmd.append("--check-only")
    cmd += target_paths
    return _run_tool("isort", cmd, root)


def _run_flake8(root: Path, target_paths: list[str]) -> dict:
    cmd = ["flake8"] + target_paths
    return _run_tool("flake8", cmd, root)


# ── 다언어 ────────────────────────────────────────────────────────────────────


def _run_lang(root: Path, target_paths: list[str], lang: str) -> dict:
    """비-Python 언어 포맷터를 실행합니다."""
    formatters = _LANG_FORMATTERS.get(lang)
    if not formatters:
        return {
            "_info": {
                "status": "ok",
                "output": f"포맷터 미정의 언어: {lang} (지원: {', '.join(_LANG_FORMATTERS)})",
            }
        }

    tools = {}
    for tool_name, extra_args in formatters:
        cmd = [tool_name] + extra_args + target_paths
        tools[tool_name] = _run_tool(tool_name, cmd, root)
    return tools


# ── 공통 subprocess 헬퍼 ──────────────────────────────────────────────────────


def _run_tool(
    name: str,
    cmd: list[str],
    cwd: Path,
    timeout: int = 120,
) -> dict:
    """공통 subprocess 실행 헬퍼."""
    if not shutil.which(name):
        return {"status": "not_installed", "output": f"{name}이(가) 설치되지 않았습니다."}

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
