"""tests/test_tools_base.py — BaseTool, ToolResult 테스트 (4개)"""
import pytest
from pathlib import Path
from locky.tools import BaseTool, ToolResult


def test_tool_result_from_dict_ok():
    d = {"status": "ok", "message": "done"}
    result = ToolResult.from_dict(d)
    assert result.status == "ok"
    assert result.message == "done"
    assert result.ok is True


def test_tool_result_from_dict_error():
    d = {"status": "error"}
    result = ToolResult.from_dict(d)
    assert result.ok is False


def test_tool_result_ok_statuses():
    for status in ("ok", "pass", "clean", "nothing_to_commit"):
        assert ToolResult(status=status).ok is True
    assert ToolResult(status="error").ok is False


def test_base_tool_run_not_implemented(tmp_path):
    tool = BaseTool()
    with pytest.raises(NotImplementedError):
        tool.run(tmp_path)


def test_base_tool_repr():
    tool = BaseTool()
    assert "BaseTool" in repr(tool)
