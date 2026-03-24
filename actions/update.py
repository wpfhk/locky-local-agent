"""actions/update.py — git pull + pip 재설치 자동 업데이트 (v1.1.0)"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run(root: Path, check_only: bool = False) -> dict:
    """locky-agent를 최신 버전으로 업데이트합니다.

    Args:
        root: 현재 작업 디렉터리 (미사용, 인터페이스 통일용)
        check_only: True이면 버전 확인만 하고 실제 업데이트는 수행하지 않음

    Returns:
        {
          "status": "ok"|"up_to_date"|"check"|"error",
          "current_version": str,
          "new_version": str | None,
          "updated": bool,
          "message": str
        }
    """
    repo_root = _find_locky_repo()
    if repo_root is None:
        return {
            "status": "error",
            "current_version": _get_version(None),
            "new_version": None,
            "updated": False,
            "message": (
                "locky-agent git 저장소를 찾을 수 없습니다. "
                "git clone으로 설치된 경우에만 update가 가능합니다."
            ),
        }

    current_version = _get_version(repo_root)

    if check_only:
        latest_commit = _get_latest_remote_commit(repo_root)
        current_commit = _get_current_commit(repo_root)
        up_to_date = latest_commit == current_commit
        return {
            "status": "check",
            "current_version": current_version,
            "new_version": None,
            "updated": False,
            "message": (
                f"현재 버전: {current_version} ({current_commit[:7] if current_commit else '?'})\n"
                + ("최신 버전입니다." if up_to_date else "업데이트가 있습니다. `locky update`를 실행하세요.")
            ),
        }

    changed, pull_output = _git_pull(repo_root)

    new_version = _get_version(repo_root)

    if not changed:
        return {
            "status": "up_to_date",
            "current_version": current_version,
            "new_version": new_version,
            "updated": False,
            "message": f"이미 최신 버전입니다. ({current_version})",
        }

    success = _reinstall(repo_root)
    if not success:
        return {
            "status": "error",
            "current_version": current_version,
            "new_version": new_version,
            "updated": False,
            "message": "pip 재설치에 실패했습니다. 수동으로 `pip install -e .`를 실행해 주세요.",
        }

    msg = f"업데이트 완료: {current_version} → {new_version}"
    if current_version == new_version:
        msg = f"파일 업데이트 완료 (버전 {new_version}). 변경사항을 적용하려면 locky를 재시작하세요."
    else:
        msg += "\n변경사항을 적용하려면 locky를 재시작하세요."

    return {
        "status": "ok",
        "current_version": current_version,
        "new_version": new_version,
        "updated": True,
        "message": msg,
    }


def _find_locky_repo() -> Optional[Path]:
    """locky-agent 패키지 위치에서 git 루트를 탐색합니다."""
    try:
        import locky_cli
        pkg_path = Path(locky_cli.__file__).parent.parent.resolve()
        # git 루트 확인
        if (pkg_path / ".git").exists():
            return pkg_path
        # 상위로 탐색
        for parent in pkg_path.parents:
            if (parent / ".git").exists():
                return parent
    except Exception:
        pass
    return None


def _get_version(repo_root: Optional[Path]) -> str:
    """pyproject.toml에서 version을 읽습니다."""
    try:
        if repo_root is None:
            import locky_cli
            repo_root = Path(locky_cli.__file__).parent.parent.resolve()
        pyproject = repo_root / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("version") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


def _get_current_commit(repo_root: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _get_latest_remote_commit(repo_root: Path) -> Optional[str]:
    try:
        subprocess.run(
            ["git", "fetch", "origin", "main"],
            cwd=repo_root, capture_output=True, timeout=30,
        )
        result = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _git_pull(repo_root: Path) -> tuple[bool, str]:
    """git pull origin main 실행. (changed, output) 반환."""
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=repo_root, capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        output = result.stdout.strip()
        changed = "Already up to date." not in output
        return changed, output
    except Exception as e:
        raise RuntimeError(f"git pull 실패: {e}") from e


def _reinstall(repo_root: Path) -> bool:
    """pip install -e . 또는 pipx upgrade 실행."""
    try:
        # pipx로 설치된 경우 확인
        if shutil.which("pipx"):
            result = subprocess.run(
                ["pipx", "upgrade", "locky-agent"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                return True

        # pip install -e . fallback
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "-q"],
            cwd=repo_root, capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False
