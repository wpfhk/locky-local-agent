"""actions/jira.py — Jira 이슈 조회·생성·상태 확인 자동화."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------
# Public runners — run(root, **opts) -> dict 패턴
# ------------------------------------------------------------------


def run_list(
    root: Path,
    project: str = "",
    status_filter: str = "",
    assignee: str = "",
    max_results: int = 50,
    output_file: Optional[str] = None,
    no_save: bool = False,
) -> dict:
    """Jira 이슈를 조회하고 .md 파일로 저장합니다.

    Returns:
        {"status": "ok"|"error", "count": int, "saved_to": str|None, "issues": [...]}
    """
    try:
        client = _get_jira_client(root)
    except ValueError as exc:
        return {"status": "error", "message": str(exc), "count": 0, "issues": []}

    jql = _build_jql(project=project, status=status_filter, assignee=assignee)
    try:
        issues = client.search_issues(jql, max_results=max_results)
    except Exception as exc:
        return {"status": "error", "message": str(exc), "count": 0, "issues": []}

    saved_to: Optional[str] = None
    if not no_save:
        out_path = _resolve_output(root, project or "jira", output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_content = _render_md(
            issues,
            project=project,
            filters={"status": status_filter, "assignee": assignee},
        )
        out_path.write_text(md_content, encoding="utf-8")
        saved_to = str(out_path.relative_to(root))

    return _sanitize_result(
        {
            "status": "ok",
            "count": len(issues),
            "saved_to": saved_to,
            "issues": issues,
        }
    )


def run_create(
    root: Path,
    project: str,
    summary: str,
    description: str = "",
    issue_type: str = "Task",
    priority: str = "Medium",
    dry_run: bool = False,
) -> dict:
    """Jira 이슈를 생성합니다.

    Returns:
        {"status": "ok"|"dry_run"|"error", "key": str|None, "url": str|None, "message": str}
    """
    if not project:
        return {
            "status": "error",
            "key": None,
            "url": None,
            "message": "--project 옵션이 필요합니다.",
        }
    if not summary:
        return {
            "status": "error",
            "key": None,
            "url": None,
            "message": "--summary 옵션이 필요합니다.",
        }

    if dry_run:
        payload = {
            "project": project,
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "priority": priority,
        }
        return {
            "status": "dry_run",
            "key": None,
            "url": None,
            "message": f"[dry-run] 생성될 이슈 페이로드: {payload}",
        }

    try:
        client = _get_jira_client(root)
    except ValueError as exc:
        return {"status": "error", "key": None, "url": None, "message": str(exc)}

    try:
        result = client.create_issue(
            project=project,
            summary=summary,
            description=description,
            issue_type=issue_type,
            priority=priority,
        )
    except Exception as exc:
        return {"status": "error", "key": None, "url": None, "message": str(exc)}

    return _sanitize_result(
        {
            "status": "ok",
            "key": result["key"],
            "url": result["url"],
            "message": f"이슈 생성 완료: {result['key']}",
        }
    )


def run_status(root: Path) -> dict:
    """Jira 연결 상태를 확인합니다.

    Returns:
        {"status": "ok"|"error", "url": str, "user": str, "projects": int}
    """
    try:
        client = _get_jira_client(root)
    except ValueError as exc:
        return {"status": "error", "url": "", "user": "", "message": str(exc)}

    from config import JIRA_BASE_URL

    if not client.health_check():
        return {
            "status": "error",
            "url": JIRA_BASE_URL,
            "user": "",
            "message": "Jira 연결 실패: 인증 정보 또는 URL을 확인하세요.",
        }

    user = client.get_current_user()
    try:
        projects = client.get_projects()
        project_count = len(projects)
    except Exception:
        project_count = 0

    return _sanitize_result(
        {
            "status": "ok",
            "url": JIRA_BASE_URL,
            "user": user,
            "projects": project_count,
        }
    )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _get_jira_client(root: Path):
    """config + 환경변수에서 JiraClient를 생성합니다."""
    from config import JIRA_BASE_URL, JIRA_EMAIL
    from tools.jira_client import JiraClient

    base_url = JIRA_BASE_URL
    email = JIRA_EMAIL
    api_token = os.getenv("JIRA_API_TOKEN", "")

    if not base_url:
        raise ValueError(
            "JIRA_BASE_URL이 설정되지 않았습니다. "
            "환경변수 또는 .locky/config.yaml의 jira.base_url을 설정하세요."
        )
    if not email:
        raise ValueError(
            "JIRA_EMAIL이 설정되지 않았습니다. "
            "환경변수 또는 .locky/config.yaml의 jira.email을 설정하세요."
        )
    if not api_token:
        raise ValueError(
            "JIRA_API_TOKEN 환경변수가 설정되지 않았습니다. "
            "https://id.atlassian.com/manage-profile/security/api-tokens 에서 발급하세요."
        )

    return JiraClient(base_url=base_url, email=email, api_token=api_token)


_SENSITIVE_KEYS = frozenset(
    {"api_token", "token", "password", "secret", "authorization"}
)


def _sanitize_result(result: dict) -> dict:
    """result dict에서 민감 키를 제거하여 안전하게 반환합니다."""
    return {k: v for k, v in result.items() if k.lower() not in _SENSITIVE_KEYS}


def _build_jql(project: str = "", status: str = "", assignee: str = "") -> str:
    """필터 조건을 JQL 문자열로 조합합니다."""
    parts = []
    if project:
        parts.append(f"project = {project}")
    if status:
        parts.append(f'status = "{status}"')
    if assignee:
        if assignee.lower() == "me":
            parts.append("assignee = currentUser()")
        else:
            parts.append(f'assignee = "{assignee}"')
    if not parts:
        return "ORDER BY created DESC"
    return " AND ".join(parts) + " ORDER BY created DESC"


def _resolve_output(root: Path, project: str, output_file: Optional[str]) -> Path:
    """저장 경로를 결정합니다. 기본: .locky/jira/{date}-{project}.md"""
    if output_file:
        return Path(output_file).resolve()

    today = date.today().isoformat()
    base_dir = root / ".locky" / "jira"
    candidate = base_dir / f"{today}-{project}.md"

    if not candidate.exists():
        return candidate

    # 중복 시 suffix
    suffix = 2
    while True:
        candidate = base_dir / f"{today}-{project}-{suffix}.md"
        if not candidate.exists():
            return candidate
        suffix += 1


def _render_md(issues: list[dict], project: str, filters: dict) -> str:
    """이슈 목록을 .md 문자열로 렌더링합니다."""
    today = date.today().isoformat()
    proj_label = project or "ALL"

    filter_parts = []
    if filters.get("status"):
        filter_parts.append(f"status={filters['status']}")
    if filters.get("assignee"):
        filter_parts.append(f"assignee={filters['assignee']}")
    filter_str = ", ".join(filter_parts) if filter_parts else "전체"

    lines = [
        f"# Jira Issues — {proj_label} ({today})",
        "",
        f"> 조회 조건: {filter_str}",
        f"> 총 {len(issues)}건",
        "",
        "---",
        "",
    ]

    for issue in issues:
        lines.append(f"## {issue['key']}: {issue['summary']}")
        lines.append("")
        lines.append(f"- **상태**: {issue['status']}")
        lines.append(f"- **담당자**: {issue['assignee']}")
        lines.append(f"- **우선순위**: {issue['priority']}")
        lines.append(f"- **타입**: {issue['issuetype']}")
        lines.append("")
        if issue.get("description"):
            lines.append(issue["description"])
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
