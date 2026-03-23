"""Security Auditor — 정적 보안 분석 서브에이전트."""

from __future__ import annotations

import re
from typing import List

from config import OLLAMA_MODEL
from states.state import LockyGlobalState
from tools.mcp_filesystem import read_file, search_in_files
from tools.ollama_client import OllamaClient

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
    """
    위험 패턴으로 파일들을 검색하여 잠재적 이슈를 반환합니다.
    """
    issues: List[dict] = []

    for pattern_str, severity, category, description in _DANGER_PATTERNS:
        matches = search_in_files(pattern=pattern_str, root=".")

        for match in matches:
            file_path = match["file"]
            # modified_files에 포함된 파일만 대상으로 (또는 modified_files가 비어 있으면 전체)
            if modified_files and not any(
                file_path.endswith(mf) or mf.endswith(file_path)
                for mf in modified_files
            ):
                continue

            # 테스트 파일은 기준 완화
            is_test_file = "test" in file_path.lower() or file_path.startswith("tests/")
            effective_severity = severity
            if is_test_file and severity in ("critical", "high"):
                effective_severity = "medium"

            issues.append({
                "severity": effective_severity,
                "category": category,
                "file": file_path,
                "line": match["line"],
                "code_snippet": match["content"].strip()[:200],
                "description": description,
                "recommendation": _get_recommendation(category),
                "_pattern": pattern_str,
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


def _build_security_review_prompt(file_path: str, content: str) -> str:
    """Ollama 보안 검토 프롬프트를 생성합니다."""
    return f"""당신은 보안 감사 전문가입니다. 아래 코드를 OWASP Top 10 기준으로 검토하세요.

## 파일: {file_path}
```python
{content}
```

## 검사 항목
1. 하드코딩된 시크릿 (API 키, 패스워드, 토큰)
2. SQL/Command/Code 인젝션 취약점
3. 경로 순회 공격 가능성
4. 안전하지 않은 역직렬화
5. 취약한 암호화 알고리즘
6. 민감 정보 로깅

## 출력 규칙
- 발견된 실제 이슈만 보고하세요 (오탐 최소화)
- 컨텍스트를 반드시 확인한 후 판정하세요
- 이슈가 없으면 "보안 이슈 없음"을 출력하세요
- 이슈가 있으면 각각에 대해 severity(critical/high/medium/low), 위치, 설명, 권고사항을 작성하세요
"""


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

    # 2. Ollama 보안 검토 (Python 파일만)
    client = OllamaClient(model=OLLAMA_MODEL)
    ollama_issues: List[dict] = []

    py_files = [f for f in modified_files if f.endswith(".py")]
    for file_path in py_files:
        print(f"[SecurityAuditor] Ollama 보안 검토: {file_path}")
        try:
            content = read_file(file_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"[SecurityAuditor] 읽기 실패 {file_path}: {e}")
            continue

        if not content.strip():
            continue

        prompt = _build_security_review_prompt(file_path, content[:_MAX_FILE_SIZE])
        messages = [{"role": "user", "content": prompt}]

        try:
            response = client.chat(messages)
        except Exception as e:
            print(f"[SecurityAuditor] Ollama 호출 실패 {file_path}: {e}")
            continue

        # 이슈 없음 응답 처리
        if "보안 이슈 없음" in response or "no security issue" in response.lower():
            continue

        # 응답에서 이슈 파싱 (간단한 severity 키워드 탐지)
        for sev in ("critical", "high", "medium", "low"):
            if sev in response.lower():
                # 중복 방지: 패턴 스캔에서 이미 발견된 이슈 제외
                already_found = any(
                    i["file"] == file_path and i["severity"] == sev
                    for i in pattern_issues
                )
                if not already_found:
                    ollama_issues.append({
                        "severity": sev,
                        "category": "ollama_review",
                        "file": file_path,
                        "line": 0,
                        "code_snippet": "",
                        "description": f"Ollama 보안 검토: {sev} 수준 이슈 발견",
                        "recommendation": response[:500],
                    })
                    break  # 파일당 하나만 추가 (중복 방지)

    # 이슈 통합 및 중복 제거
    all_issues = pattern_issues + ollama_issues

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
