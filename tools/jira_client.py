"""tools/jira_client.py — Jira REST API v3 httpx 클라이언트."""

from __future__ import annotations

import base64
from typing import Any

import httpx


class JiraAuthError(Exception):
    """인증 실패 (401)."""


class JiraForbiddenError(Exception):
    """권한 없음 (403)."""


class JiraNotFoundError(Exception):
    """리소스 없음 (404)."""


class JiraClient:
    """Jira Cloud REST API v3 래퍼 (httpx 동기 클라이언트)."""

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._auth_header = _make_basic_auth(email, api_token)
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_issues(self, jql: str, max_results: int = 50) -> list[dict]:
        """JQL로 이슈를 검색하여 정규화된 이슈 목록을 반환합니다."""
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,status,assignee,priority,issuetype,description",
        }
        data = self._get("/rest/api/3/search", params=params)
        return [_parse_issue(issue) for issue in data.get("issues", [])]

    def create_issue(
        self,
        project: str,
        summary: str,
        description: str = "",
        issue_type: str = "Task",
        priority: str = "Medium",
    ) -> dict:
        """새 Jira 이슈를 생성하고 key/id/url을 반환합니다."""
        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": project},
                "summary": summary,
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
            }
        }
        if description:
            payload["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }
        data = self._post("/rest/api/3/issue", json=payload)
        key = data.get("key", "")
        issue_id = data.get("id", "")
        url = f"{self.base_url}/browse/{key}" if key else ""
        return {"key": key, "id": issue_id, "url": url}

    def get_projects(self) -> list[dict]:
        """접근 가능한 프로젝트 목록을 반환합니다."""
        data = self._get("/rest/api/3/project")
        return [{"key": p.get("key", ""), "name": p.get("name", "")} for p in data]

    def health_check(self) -> bool:
        """인증 상태를 확인합니다. 성공하면 True."""
        try:
            self._get("/rest/api/3/myself")
            return True
        except Exception:
            return False

    def get_current_user(self) -> str:
        """현재 인증된 사용자의 displayName을 반환합니다."""
        try:
            data = self._get("/rest/api/3/myself")
            return data.get("displayName", data.get("emailAddress", "unknown"))
        except Exception:
            return "unknown"

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self._headers(), params=params)
            _raise_for_status(resp, context=path)
            return resp.json()

    def _post(self, path: str, json: dict) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self._headers(), json=json)
            _raise_for_status(resp, context=path)
            return resp.json()

    def _headers(self) -> dict:
        return {
            "Authorization": self._auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # ADF → plain text
    # ------------------------------------------------------------------

    @staticmethod
    def adf_to_text(adf: dict | None) -> str:
        """Atlassian Document Format(ADF) dict를 plain text로 변환합니다."""
        if not adf or not isinstance(adf, dict):
            return ""
        return _adf_node_to_text(adf).strip()


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _make_basic_auth(email: str, api_token: str) -> str:
    raw = f"{email}:{api_token}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _raise_for_status(resp: httpx.Response, context: str = "") -> None:
    if resp.status_code == 401:
        raise JiraAuthError(
            "Jira 인증 실패: JIRA_API_TOKEN 또는 JIRA_EMAIL을 확인하세요."
        )
    if resp.status_code == 403:
        raise JiraForbiddenError(
            "Jira 권한 없음: 해당 프로젝트에 접근 권한이 없습니다."
        )
    if resp.status_code == 404:
        detail = f" ({context})" if context else ""
        raise JiraNotFoundError(f"Jira 리소스를 찾을 수 없습니다{detail}.")
    resp.raise_for_status()


def _parse_issue(raw: dict) -> dict:
    """Jira API 이슈 응답을 정규화된 dict로 변환합니다."""
    fields = raw.get("fields", {})
    status_obj = fields.get("status") or {}
    assignee_obj = fields.get("assignee") or {}
    priority_obj = fields.get("priority") or {}
    issuetype_obj = fields.get("issuetype") or {}
    description_raw = fields.get("description")

    return {
        "key": raw.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": status_obj.get("name", ""),
        "assignee": assignee_obj.get("displayName", "Unassigned"),
        "priority": priority_obj.get("name", ""),
        "issuetype": issuetype_obj.get("name", ""),
        "description": JiraClient.adf_to_text(description_raw),
    }


def _adf_node_to_text(node: dict) -> str:
    """ADF 노드를 재귀적으로 plain text로 변환합니다."""
    node_type = node.get("type", "")
    text = node.get("text", "")

    if node_type == "text":
        return text

    parts = []
    for child in node.get("content", []):
        parts.append(_adf_node_to_text(child))

    joined = " ".join(p for p in parts if p)

    if node_type in ("paragraph", "heading"):
        return joined + "\n"
    if node_type in ("bulletList", "orderedList"):
        return joined
    if node_type == "listItem":
        return "- " + joined
    if node_type == "hardBreak":
        return "\n"

    return joined
