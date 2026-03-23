"""Security Auditor — 정적 보안 분석 서브에이전트."""

from __future__ import annotations

import re
from typing import List

from states.state import LockyGlobalState
from tools.mcp_filesystem import read_file

_MAX_FILE_SIZE = 5000

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


def _scan_patterns(modified_files: List[str]) -> List[dict]:
    """수정된 파일만 직접 읽어 위험 패턴을 스캔합니다."""
    issues: List[dict] = []

    for file_path in modified_files:
        try:
            content = read_file(file_path)
        except (FileNotFoundError, ValueError):
            continue

        is_test_file = "test" in file_path.lower() or file_path.startswith("tests/")
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



def audit_security(state: LockyGlobalState) -> dict:
    """
    modified_files에 대해 정적 보안 분석을 수행합니다.

    Args:
        state: 전역 파이프라인 상태 (coder_output.modified_files 포함)

    Returns:
        tester_output에 security_issues를 포함한 dict
    """
    coder_output = state.get("coder_output") or {}
    modified_files: List[str] = coder_output.get("modified_files", [])

    # 수정된 파일이 없으면 스캔 생략
    if not modified_files:
        print("[SecurityAuditor] 수정된 파일 없음 — 보안 스캔 생략")
        existing_tester = state.get("tester_output") or {}
        return {
            "tester_output": {
                **existing_tester,
                "security_issues": [],
                "security_summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "scan_status": "skipped"},
            }
        }

    # 1. 패턴 기반 정적 스캔
    print(f"[SecurityAuditor] 위험 패턴 스캔 중 ({len(modified_files)}개 파일)...")
    pattern_issues = _scan_patterns(modified_files)
    print(f"[SecurityAuditor] 패턴 스캔 결과: {len(pattern_issues)}개 잠재 이슈")

    # 패턴 스캔만으로 충분 — Ollama 보안 검토는 속도 대비 효과 낮음
    all_issues = pattern_issues

    # 심각도별 집계
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for issue in all_issues:
        sev = issue.get("severity", "low")
        if sev in summary:
            summary[sev] += 1

    scan_status = "clean" if not all_issues else "issues_found"
    print(
        f"[SecurityAuditor] 완료 — "
        f"critical={summary['critical']}, high={summary['high']}, "
        f"medium={summary['medium']}, low={summary['low']}"
    )

    # _pattern 필드 제거 (내부 필드)
    cleaned_issues = [
        {k: v for k, v in issue.items() if k != "_pattern"}
        for issue in all_issues
    ]

    existing_tester = state.get("tester_output") or {}

    return {
        "tester_output": {
            **existing_tester,
            "security_issues": cleaned_issues,
            "security_summary": {**summary, "scan_status": scan_status},
        }
    }
