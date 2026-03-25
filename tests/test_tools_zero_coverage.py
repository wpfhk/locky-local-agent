"""tests/test_tools_zero_coverage.py — 0% 커버리지 모듈 테스트"""
from unittest.mock import patch
from pathlib import Path
import pytest

from locky.tools.commit import CommitTool
from locky.tools.scan import ScanTool
from locky.tools import ToolResult
from locky.agents.commit_agent import CommitAgent
from locky.core.session import LockySession


@pytest.fixture
def session(tmp_path):
    return LockySession(workspace=tmp_path)


# --- CommitTool ---

def test_commit_tool_delegates(tmp_path):
    tool = CommitTool()
    with patch("actions.commit.run", return_value={"status": "ok", "message": "feat: x"}) as mock:
        result = tool.run(tmp_path, dry_run=True)
    assert mock.called
    assert isinstance(result, ToolResult)
    assert result.ok


def test_commit_tool_dry_run_false(tmp_path):
    tool = CommitTool()
    with patch("actions.commit.run", return_value={"status": "ok"}) as mock:
        result = tool.run(tmp_path, dry_run=False)
    assert mock.called
    assert result.ok


def test_commit_tool_error_propagates(tmp_path):
    tool = CommitTool()
    with patch("actions.commit.run", return_value={"status": "error", "message": "nothing to commit"}):
        result = tool.run(tmp_path)
    assert result.status == "error"
    assert not result.ok


# --- ScanTool ---

def test_scan_tool_delegates(tmp_path):
    tool = ScanTool()
    with patch("actions.security_scan.run", return_value={"status": "clean", "issues": []}) as mock:
        result = tool.run(tmp_path)
    assert mock.called
    assert isinstance(result, ToolResult)
    assert result.ok


def test_scan_tool_issues_found(tmp_path):
    tool = ScanTool()
    with patch("actions.security_scan.run", return_value={"status": "issues_found", "issues": [{}]}):
        result = tool.run(tmp_path)
    assert result.status == "issues_found"
    assert not result.ok


# --- CommitAgent ---

def test_commit_agent_run_dry_run(session):
    agent = CommitAgent(session)
    with patch("actions.commit.run", return_value={"status": "ok", "message": "feat: y"}):
        result = agent.run(dry_run=True)
    assert result["status"] == "ok"


def test_commit_agent_saves_history(session):
    agent = CommitAgent(session)
    with patch("actions.commit.run", return_value={"status": "ok", "message": "fix: z"}):
        agent.run(dry_run=True)
    assert len(session.history) == 1
    assert session.history[0]["type"] == "commit"


def test_commit_agent_run_push(session):
    agent = CommitAgent(session)
    with patch("actions.commit.run", return_value={"status": "ok"}) as mock:
        result = agent.run(dry_run=False, push=True)
    assert mock.called
    assert result["status"] == "ok"
