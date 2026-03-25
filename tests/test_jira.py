"""tests/test_jira.py — actions/jira.py + tools/jira_client.py 단위 테스트."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ------------------------------------------------------------------
# Fixtures & helpers
# ------------------------------------------------------------------

MOCK_ISSUE_RAW = {
    "key": "PROJ-1",
    "fields": {
        "summary": "Fix login bug",
        "status": {"name": "In Progress"},
        "assignee": {"displayName": "Alice"},
        "priority": {"name": "High"},
        "issuetype": {"name": "Bug"},
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Users cannot login."}],
                }
            ],
        },
    },
}

MOCK_ISSUE_PARSED = {
    "key": "PROJ-1",
    "summary": "Fix login bug",
    "status": "In Progress",
    "assignee": "Alice",
    "priority": "High",
    "issuetype": "Bug",
    "description": "Users cannot login.\n",
}


def _make_response(status_code: int, body: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


# ------------------------------------------------------------------
# tools/jira_client.py
# ------------------------------------------------------------------

class TestJiraClientSearch:
    def test_search_returns_parsed_issues(self):
        from tools.jira_client import JiraClient

        body = {"issues": [MOCK_ISSUE_RAW]}
        resp = _make_response(200, body)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = resp

            client = JiraClient("https://example.atlassian.net", "user@test.com", "token123")
            issues = client.search_issues("project = PROJ")

        assert len(issues) == 1
        assert issues[0]["key"] == "PROJ-1"
        assert issues[0]["summary"] == "Fix login bug"
        assert issues[0]["status"] == "In Progress"

    def test_search_empty_result(self):
        from tools.jira_client import JiraClient

        resp = _make_response(200, {"issues": []})
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = resp
            client = JiraClient("https://example.atlassian.net", "user@test.com", "token123")
            issues = client.search_issues("project = EMPTY")
        assert issues == []


class TestJiraClientCreate:
    def test_create_returns_key_and_url(self):
        from tools.jira_client import JiraClient

        body = {"key": "PROJ-2", "id": "10002"}
        resp = _make_response(201, body)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.post.return_value = resp

            client = JiraClient("https://example.atlassian.net", "user@test.com", "token123")
            result = client.create_issue("PROJ", "New feature")

        assert result["key"] == "PROJ-2"
        assert "PROJ-2" in result["url"]


class TestJiraClientHealth:
    def test_health_check_ok(self):
        from tools.jira_client import JiraClient

        resp = _make_response(200, {"displayName": "Alice"})
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = resp
            client = JiraClient("https://example.atlassian.net", "user@test.com", "token123")
            assert client.health_check() is True

    def test_health_check_fail(self):
        from tools.jira_client import JiraClient

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection refused")
            client = JiraClient("https://example.atlassian.net", "user@test.com", "token123")
            assert client.health_check() is False


class TestJiraAuthErrors:
    def test_401_raises_auth_error(self):
        from tools.jira_client import JiraClient, JiraAuthError

        resp = MagicMock()
        resp.status_code = 401
        resp.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = resp

            client = JiraClient("https://example.atlassian.net", "user@test.com", "badtoken")
            with pytest.raises(JiraAuthError):
                client.search_issues("project = PROJ")

    def test_403_raises_forbidden(self):
        from tools.jira_client import JiraClient, JiraForbiddenError

        resp = MagicMock()
        resp.status_code = 403

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = resp

            client = JiraClient("https://example.atlassian.net", "user@test.com", "token")
            with pytest.raises(JiraForbiddenError):
                client.search_issues("project = PROJ")


class TestAdfToText:
    def test_paragraph_node(self):
        from tools.jira_client import JiraClient

        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello world"}],
                }
            ],
        }
        result = JiraClient.adf_to_text(adf)
        assert "Hello world" in result

    def test_none_returns_empty(self):
        from tools.jira_client import JiraClient
        assert JiraClient.adf_to_text(None) == ""

    def test_non_dict_returns_empty(self):
        from tools.jira_client import JiraClient
        assert JiraClient.adf_to_text("plain text") == ""  # type: ignore


# ------------------------------------------------------------------
# actions/jira.py
# ------------------------------------------------------------------

class TestBuildJql:
    def test_project_only(self):
        from actions.jira import _build_jql
        jql = _build_jql(project="PROJ")
        assert "project = PROJ" in jql

    def test_all_filters(self):
        from actions.jira import _build_jql
        jql = _build_jql(project="PROJ", status="In Progress", assignee="me")
        assert "project = PROJ" in jql
        assert "status" in jql
        assert "currentUser()" in jql

    def test_empty_returns_order_by(self):
        from actions.jira import _build_jql
        jql = _build_jql()
        assert "ORDER BY" in jql


class TestResolveOutput:
    def test_default_path(self, tmp_path):
        from actions.jira import _resolve_output
        out = _resolve_output(tmp_path, "PROJ", None)
        assert ".locky" in str(out)
        assert "PROJ" in out.name
        assert out.suffix == ".md"

    def test_explicit_output(self, tmp_path):
        from actions.jira import _resolve_output
        custom = str(tmp_path / "custom.md")
        out = _resolve_output(tmp_path, "PROJ", custom)
        assert out == Path(custom).resolve()

    def test_conflict_adds_suffix(self, tmp_path):
        from actions.jira import _resolve_output
        jira_dir = tmp_path / ".locky" / "jira"
        jira_dir.mkdir(parents=True)
        from datetime import date
        today = date.today().isoformat()
        (jira_dir / f"{today}-PROJ.md").write_text("existing")
        out = _resolve_output(tmp_path, "PROJ", None)
        assert "-2" in out.name


class TestRenderMd:
    def test_header_and_count(self):
        from actions.jira import _render_md
        issues = [MOCK_ISSUE_PARSED]
        md = _render_md(issues, project="PROJ", filters={})
        assert "# Jira Issues — PROJ" in md
        assert "총 1건" in md

    def test_issue_section(self):
        from actions.jira import _render_md
        issues = [MOCK_ISSUE_PARSED]
        md = _render_md(issues, project="PROJ", filters={})
        assert "PROJ-1" in md
        assert "Fix login bug" in md
        assert "In Progress" in md


class TestRunList:
    def test_list_ok(self, tmp_path):
        from actions.jira import run_list

        with patch("actions.jira._get_jira_client") as mock_get:
            mock_client = MagicMock()
            mock_client.search_issues.return_value = [MOCK_ISSUE_PARSED]
            mock_get.return_value = mock_client

            result = run_list(tmp_path, project="PROJ")

        assert result["status"] == "ok"
        assert result["count"] == 1
        assert result["saved_to"] is not None
        # .md 파일이 실제로 생성됐는지 확인
        saved_path = tmp_path / result["saved_to"]
        assert saved_path.exists()

    def test_list_no_save(self, tmp_path):
        from actions.jira import run_list

        with patch("actions.jira._get_jira_client") as mock_get:
            mock_client = MagicMock()
            mock_client.search_issues.return_value = [MOCK_ISSUE_PARSED]
            mock_get.return_value = mock_client
            result = run_list(tmp_path, no_save=True)

        assert result["status"] == "ok"
        assert result["saved_to"] is None

    def test_list_missing_token(self, tmp_path):
        from actions.jira import run_list

        with patch.dict("os.environ", {"JIRA_API_TOKEN": ""}, clear=False):
            with patch("config.JIRA_BASE_URL", ""), \
                 patch("config.JIRA_EMAIL", ""):
                result = run_list(tmp_path)

        assert result["status"] == "error"


class TestRunCreate:
    def test_create_dry_run(self, tmp_path):
        from actions.jira import run_create
        result = run_create(tmp_path, project="PROJ", summary="Test issue", dry_run=True)
        assert result["status"] == "dry_run"
        assert result["key"] is None

    def test_create_missing_project(self, tmp_path):
        from actions.jira import run_create
        result = run_create(tmp_path, project="", summary="Test")
        assert result["status"] == "error"

    def test_create_ok(self, tmp_path):
        from actions.jira import run_create

        with patch("actions.jira._get_jira_client") as mock_get:
            mock_client = MagicMock()
            mock_client.create_issue.return_value = {
                "key": "PROJ-3", "id": "10003",
                "url": "https://example.atlassian.net/browse/PROJ-3",
            }
            mock_get.return_value = mock_client
            result = run_create(tmp_path, project="PROJ", summary="New task")

        assert result["status"] == "ok"
        assert result["key"] == "PROJ-3"


class TestRunStatus:
    def test_status_ok(self, tmp_path):
        from actions.jira import run_status

        with patch("actions.jira._get_jira_client") as mock_get, \
             patch("config.JIRA_BASE_URL", "https://example.atlassian.net"):
            mock_client = MagicMock()
            mock_client.health_check.return_value = True
            mock_client.get_current_user.return_value = "Alice"
            mock_client.get_projects.return_value = [{"key": "PROJ", "name": "Project"}]
            mock_get.return_value = mock_client
            result = run_status(tmp_path)

        assert result["status"] == "ok"
        assert result["user"] == "Alice"
        assert result["projects"] == 1

    def test_status_connection_error(self, tmp_path):
        from actions.jira import run_status

        with patch("actions.jira._get_jira_client") as mock_get, \
             patch("config.JIRA_BASE_URL", "https://example.atlassian.net"):
            mock_client = MagicMock()
            mock_client.health_check.return_value = False
            mock_get.return_value = mock_client
            result = run_status(tmp_path)

        assert result["status"] == "error"
