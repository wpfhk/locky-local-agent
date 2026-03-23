"""actions/deps_check.py — requirements.txt와 실제 설치된 패키지 버전을 비교합니다."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional


def run(root: Path) -> dict:
    """
    requirements.txt와 실제 설치된 패키지 버전을 비교합니다.

    Args:
        root: 프로젝트 루트 Path

    Returns:
        {"status": "ok"|"error", "packages": [{"name": str, "required": str, "installed": str, "outdated": bool}]}
    """
    root = Path(root).resolve()
    req_file = root / "requirements.txt"

    if not req_file.exists():
        return {
            "status": "error",
            "message": f"requirements.txt 파일을 찾을 수 없습니다: {req_file}",
            "packages": [],
        }

    try:
        requirements = _parse_requirements(req_file)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"requirements.txt 파싱 실패: {exc}",
            "packages": [],
        }

    packages = []
    for name, required_version in requirements:
        installed_version = _get_installed_version(name)
        outdated = _is_outdated(required_version, installed_version)
        packages.append({
            "name": name,
            "required": required_version or "any",
            "installed": installed_version or "not_installed",
            "outdated": outdated,
        })

    return {
        "status": "ok",
        "packages": packages,
    }


def _parse_requirements(req_file: Path) -> List[tuple[str, Optional[str]]]:
    """requirements.txt를 파싱하여 (name, version_spec) 목록을 반환합니다."""
    requirements = []
    content = req_file.read_text(encoding="utf-8", errors="ignore")

    for line in content.splitlines():
        line = line.strip()
        # 주석 및 빈 줄 제외
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # 버전 스펙 파싱
        match = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([><=!~][^#\s]*)?", line)
        if match:
            name = match.group(1)
            version_spec = match.group(2) or ""
            requirements.append((name, version_spec.strip()))

    return requirements


def _get_installed_version(package_name: str) -> Optional[str]:
    """pip show로 설치된 패키지 버전을 확인합니다."""
    try:
        result = subprocess.run(
            ["pip", "show", package_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        return None
    except Exception:
        return None


def _is_outdated(required_spec: Optional[str], installed: Optional[str]) -> bool:
    """required 버전 스펙과 installed 버전을 비교합니다."""
    if not installed:
        return True  # 미설치
    if not required_spec:
        return False  # 버전 제약 없음

    # 정확한 버전 비교 (==)
    exact_match = re.match(r"^==(.+)$", required_spec)
    if exact_match:
        return installed != exact_match.group(1).strip()

    # 그 외 스펙은 간단히 False (설치됨으로 간주)
    return False
