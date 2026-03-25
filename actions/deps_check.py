"""actions/deps_check.py — 의존성 파일을 읽어 설치된 패키지 버전을 비교합니다. (v1.1.0)"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

# 지원되는 의존성 파일 (우선순위 순)
_DEP_FILES = [
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "go.mod",
]


def run(root: Path) -> dict:
    """의존성 파일을 자동 감지하여 설치된 버전과 비교합니다.

    지원 형식: requirements.txt, pyproject.toml, package.json, go.mod
    여러 파일이 있으면 우선순위에 따라 첫 번째를 사용합니다.

    Returns:
        {"status": "ok"|"error", "dep_file": str, "packages": [...]}
    """
    root = Path(root).resolve()

    dep_file, fmt = _find_dep_file(root)
    if dep_file is None:
        return {
            "status": "error",
            "message": f"의존성 파일을 찾을 수 없습니다. ({', '.join(_DEP_FILES)} 중 하나가 필요합니다.)",
            "packages": [],
            "dep_file": "",
        }

    try:
        requirements = _parse(dep_file, fmt)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"{dep_file.name} 파싱 실패: {exc}",
            "packages": [],
            "dep_file": str(dep_file),
        }

    packages = []
    for name, required_version in requirements:
        installed_version = _get_installed_version(name, fmt)
        outdated = _is_outdated(required_version, installed_version)
        packages.append(
            {
                "name": name,
                "required": required_version or "any",
                "installed": installed_version or "not_installed",
                "outdated": outdated,
            }
        )

    return {
        "status": "ok",
        "dep_file": str(dep_file.relative_to(root)),
        "packages": packages,
    }


# ── 파일 감지 ─────────────────────────────────────────────────────────────────


def _find_dep_file(root: Path) -> tuple[Path | None, str]:
    """우선순위에 따라 의존성 파일을 찾습니다."""
    for name in _DEP_FILES:
        path = root / name
        if path.exists():
            return path, name
    return None, ""


# ── 파서 ──────────────────────────────────────────────────────────────────────


def _parse(dep_file: Path, fmt: str) -> list[tuple[str, str]]:
    """파일 형식에 맞는 파서를 호출합니다."""
    if fmt == "requirements.txt":
        return _parse_requirements(dep_file)
    elif fmt == "pyproject.toml":
        return _parse_pyproject(dep_file)
    elif fmt == "package.json":
        return _parse_package_json(dep_file)
    elif fmt == "go.mod":
        return _parse_go_mod(dep_file)
    return []


def _parse_requirements(req_file: Path) -> list[tuple[str, str]]:
    """requirements.txt 파서."""
    requirements = []
    content = req_file.read_text(encoding="utf-8", errors="ignore")
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([><=!~][^#\s]*)?", line)
        if match:
            name = match.group(1)
            spec = (match.group(2) or "").strip()
            requirements.append((name, spec))
    return requirements


def _parse_pyproject(path: Path) -> list[tuple[str, str]]:
    """pyproject.toml 파서 (표준 라이브러리 tomllib 또는 tomli 사용)."""
    content = path.read_text(encoding="utf-8")
    try:
        import tomllib  # Python 3.11+

        data: dict[str, Any] = tomllib.loads(content)
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore

            data = tomllib.loads(content)
        except ImportError:
            # fallback: 정규식으로 의존성 줄만 추출
            return _parse_pyproject_regex(content)

    deps: list[str] = []
    # PEP 621: [project].dependencies
    deps += data.get("project", {}).get("dependencies", [])
    # Poetry: [tool.poetry.dependencies]
    for name, val in (
        data.get("tool", {}).get("poetry", {}).get("dependencies", {}).items()
    ):
        if name.lower() == "python":
            continue
        if isinstance(val, str):
            deps.append(
                f"{name}{val}"
                if val.startswith(("^", "~", ">", "<", "=", "!"))
                else name
            )
        else:
            deps.append(name)

    result = []
    for dep in deps:
        match = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([><=!~^][^;,\s]*)?", dep.strip())
        if match:
            result.append((match.group(1), (match.group(2) or "").strip()))
    return result


def _parse_pyproject_regex(content: str) -> list[tuple[str, str]]:
    """tomllib 미사용 시 정규식 fallback."""
    result = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r"dependencies\s*=\s*\[", stripped):
            in_deps = True
            continue
        if in_deps:
            if stripped.startswith("]"):
                break
            match = re.search(r'"([A-Za-z0-9_\-\.]+)\s*([><=!~^][^"]*)?"', stripped)
            if match:
                result.append((match.group(1), (match.group(2) or "").strip()))
    return result


def _parse_package_json(path: Path) -> list[tuple[str, str]]:
    """package.json 파서 (dependencies + devDependencies)."""
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    result = []
    for section in ("dependencies", "devDependencies"):
        for name, ver in data.get(section, {}).items():
            # npm 버전 표기: ^1.0.0, ~1.0.0, 1.0.0 등
            result.append((name, ver))
    return result


def _parse_go_mod(path: Path) -> list[tuple[str, str]]:
    """go.mod 파서."""
    result = []
    in_require = False
    content = path.read_text(encoding="utf-8", errors="ignore")
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "require (":
            in_require = True
            continue
        if stripped.startswith("require ") and not stripped.startswith("require ("):
            # single-line: require github.com/foo/bar v1.2.3
            parts = stripped.split()
            if len(parts) >= 3:
                result.append((parts[1], parts[2]))
            continue
        if in_require:
            if stripped == ")":
                in_require = False
                continue
            parts = stripped.split()
            if len(parts) >= 2 and not stripped.startswith("//"):
                result.append((parts[0], parts[1]))
    return result


# ── 버전 확인 ─────────────────────────────────────────────────────────────────


def _get_installed_version(package_name: str, fmt: str) -> Optional[str]:
    """포맷에 따라 패키지 설치 버전을 확인합니다."""
    if fmt in ("requirements.txt", "pyproject.toml"):
        return _pip_version(package_name)
    elif fmt == "package.json":
        return _npm_version(package_name)
    elif fmt == "go.mod":
        return _go_version(package_name)
    return None


def _pip_version(package_name: str) -> Optional[str]:
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


def _npm_version(package_name: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["npm", "list", package_name, "--depth=0", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout or "{}")
        deps = data.get("dependencies", {})
        pkg = deps.get(package_name, {})
        return pkg.get("version")
    except Exception:
        return None


def _go_version(module_path: str) -> Optional[str]:
    """go list -m -json으로 모듈 버전 확인."""
    try:
        result = subprocess.run(
            ["go", "list", "-m", "-json", module_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout or "{}")
        return data.get("Version")
    except Exception:
        return None


def _is_outdated(required_spec: Optional[str], installed: Optional[str]) -> bool:
    """required 버전 스펙과 installed 버전을 비교합니다."""
    if not installed:
        return True
    if not required_spec:
        return False
    exact_match = re.match(r"^==(.+)$", required_spec)
    if exact_match:
        return installed != exact_match.group(1).strip()
    return False
