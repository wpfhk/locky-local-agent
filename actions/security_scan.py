"""actions/security_scan.py — 보안 패턴 스캔 (agents/tester/security_auditor.py 패턴 재사용)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

_EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "node_modules"}

# 위험 패턴 정의 (pattern, severity, category, description)
_DANGER_PATTERNS = [
    # Critical
    (r'password\s*=\s*["\']', "critical", "hardcoded_secret", "하드코딩된 패스워드"),
    (r'api_key\s*=\s*["\']', "critical", "hardcoded_secret", "하드코딩된 API 키"),
    (r'secret\s*=\s*["\']', "critical", "hardcoded_secret", "하드코딩된 시크릿"),
    (r'token\s*=\s*["\'][^${\'"]{8,}', "critical", "hardcoded_secret", "하드코딩된 토큰"),
    # High
    (r'subprocess.*shell\s*=\s*True', "high", "command_injection", "shell=True 사용 (커맨드 인젝션 위험)"),
    (r'eval\(', "high", "code_injection", "eval() 사용 (코드 인젝션 위험)"),
    (r'exec\(', "high", "code_injection", "exec() 사용 (코드 인젝션 위험)"),
    # Medium
    (r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)', "medium", "insecure_http", "비 localhost HTTP 사용"),
    (r'import pickle', "medium", "insecure_deserialization", "pickle 역직렬화 위험"),
    (r'hashlib\.(md5|sha1)\b', "medium", "weak_crypto", "취약한 해시 알고리즘 사용"),
    # Low
    (r'#\s*TODO.*security', "low", "security_todo", "보안 관련 TODO 미해결"),
    (r'verify\s*=\s*False', "low", "ssl_verification_disabled", "SSL 검증 비활성화"),
]

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def run(
    root: Path,
    severity_filter: Optional[str] = None,
) -> dict:
    """
    프로젝트 전체 Python 파일을 보안 패턴으로 스캔합니다.

    Args:
        root: 프로젝트 루트 Path
        severity_filter: "critical", "high", "medium", "low" 중 하나 (None이면 전체)

    Returns:
        {"status": "clean"|"issues_found", "summary": {...}, "issues": [...]}
    """
    root = Path(root).resolve()

    py_files = [
        p for p in root.rglob("*.py")
        if p.is_file() and not _is_excluded(p, root)
    ]

    all_issues = _scan_patterns([str(f) for f in py_files])

    # severity_filter 적용
    if severity_filter:
        filter_level = _SEVERITY_ORDER.get(severity_filter.lower(), 99)
        all_issues = [
            i for i in all_issues
            if _SEVERITY_ORDER.get(i.get("severity", "low"), 99) <= filter_level
        ]

    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for issue in all_issues:
        sev = issue.get("severity", "low")
        if sev in summary:
            summary[sev] += 1

    status = "clean" if not all_issues else "issues_found"

    return {
        "status": status,
        "summary": summary,
        "issues": all_issues,
    }


def _is_excluded(path: Path, root: Path) -> bool:
    """제외 디렉터리 확인."""
    try:
        parts = path.relative_to(root).parts
        return any(part in _EXCLUDE_DIRS for part in parts)
    except ValueError:
        return False


def _scan_patterns(file_paths: List[str]) -> List[dict]:
    """파일 목록을 직접 읽어 위험 패턴을 스캔합니다."""
    issues: List[dict] = []

    for file_path in file_paths:
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        is_test_file = "test" in file_path.lower()
        lines = content.splitlines()

        for pattern_str, severity, category, description in _DANGER_PATTERNS:
            compiled = re.compile(pattern_str, re.IGNORECASE)
            for lineno, line in enumerate(lines, start=1):
                if compiled.search(line):
                    effective_severity = severity
                    if is_test_file and severity in ("critical", "high"):
                        effective_severity = "medium"
                    issues.append({
                        "severity": effective_severity,
                        "category": category,
                        "file": file_path,
                        "line": lineno,
                        "code_snippet": line.strip()[:200],
                        "description": description,
                        "recommendation": _get_recommendation(category),
                    })

    return issues


def _get_recommendation(category: str) -> str:
    """보안 카테고리별 권고사항을 반환합니다."""
    recommendations = {
        "hardcoded_secret": "환경변수(os.environ) 또는 secrets 관리 도구를 사용하세요.",
        "command_injection": "shell=False를 사용하고 인자를 리스트로 전달하세요.",
        "code_injection": "eval()/exec() 대신 안전한 대안을 사용하세요 (ast.literal_eval 등).",
        "insecure_http": "HTTPS를 사용하거나 내부 통신임을 명시적으로 문서화하세요.",
        "insecure_deserialization": "JSON 또는 msgpack 등 안전한 직렬화 형식을 사용하세요.",
        "weak_crypto": "SHA-256 이상의 해시 알고리즘을 사용하세요.",
        "security_todo": "보안 관련 TODO를 해결하세요.",
        "ssl_verification_disabled": "SSL 검증을 활성화하거나 CA 인증서를 올바르게 설정하세요.",
    }
    return recommendations.get(category, "코드를 검토하고 보안 모범 사례를 따르세요.")
