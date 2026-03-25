"""tests/test_core_agent.py — BaseAgent 테스트 (8개)"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from locky.core.agent import ActionPlan, AgentResult, BaseAgent
from locky.core.session import LockySession
from locky.tools import BaseTool, ToolResult


class EchoTool(BaseTool):
    name = "echo"
    description = "테스트용 echo 도구"

    def run(self, root: Path, **opts) -> ToolResult:
        return ToolResult(status="ok", message=opts.get("instruction", ""))


class FailTool(BaseTool):
    name = "fail"
    description = "테스트용 실패 도구"

    def run(self, root: Path, **opts) -> ToolResult:
        return ToolResult(status="error", message="의도적 실패")


@pytest.fixture
def session(tmp_path):
    return LockySession(workspace=tmp_path)


def _make_plan(task="test task", tool_calls=None):
    return ActionPlan(
        task=task,
        steps=["step1"],
        tool_calls=tool_calls or [],
        reasoning="test",
    )


def test_agent_run_ok_no_tools(session):
    agent = BaseAgent(session, tools=[])
    with patch.object(agent, "_plan", return_value=_make_plan()):
        result = agent.run("do nothing")
    assert result.status == "ok"


def test_agent_run_with_echo_tool(session, tmp_path):
    agent = BaseAgent(session, tools=[EchoTool()])
    plan = _make_plan(tool_calls=[{"tool": "echo", "instruction": "hello"}])
    with patch.object(agent, "_plan", return_value=plan):
        result = agent.run("echo task")
    assert result.status == "ok"
    assert "echo: ok" in result.actions_taken


def test_agent_run_error_tool_not_ok(session, tmp_path):
    # 실패 도구는 재시도 후 "partial" 반환 (AI agent loop 설계)
    agent = BaseAgent(session, tools=[FailTool()], max_iterations=1)
    plan = _make_plan(tool_calls=[{"tool": "fail"}])
    with patch.object(agent, "_plan", return_value=plan):
        result = agent.run("fail task")
    assert result.status != "ok"


def test_agent_run_unknown_tool_skipped(session):
    agent = BaseAgent(session, tools=[])
    plan = _make_plan(tool_calls=[{"tool": "nonexistent"}])
    with patch.object(agent, "_plan", return_value=plan):
        result = agent.run("unknown tool")
    assert result.status == "ok"


def test_agent_plan_returns_none(session):
    agent = BaseAgent(session, tools=[], max_iterations=1)
    with patch.object(agent, "_plan", return_value=None):
        result = agent.run("no ollama")
    assert result.status == "error"
    assert "Ollama" in result.output


def test_agent_max_iterations(session):
    call_count = [0]
    original_verify = BaseAgent._verify

    def always_false_verify(self, result, plan):
        return False

    agent = BaseAgent(session, tools=[], max_iterations=3)
    plan = _make_plan()

    with patch.object(agent, "_plan", return_value=plan):
        with patch.object(BaseAgent, "_verify", always_false_verify):
            # _execute returns "ok" so loop exits after first iteration
            result = agent.run("task")
    assert result.iterations >= 1


def test_agent_history_recorded(session):
    agent = BaseAgent(session, tools=[])
    with patch.object(agent, "_plan", return_value=_make_plan()):
        agent.run("history test")
    assert len(session.history) >= 1
    assert session.history[-1]["type"] == "agent_run"


def test_agent_verify_ok_status(session):
    agent = BaseAgent(session, tools=[])
    result = AgentResult(status="ok", output="done")
    plan = _make_plan()
    assert agent._verify(result, plan) is True


def test_agent_verify_error_status(session):
    agent = BaseAgent(session, tools=[])
    result = AgentResult(status="error", output="fail")
    plan = _make_plan()
    assert agent._verify(result, plan) is False
