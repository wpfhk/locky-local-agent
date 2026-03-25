"""tests/test_tools_format.py — FormatTool 위임 패턴 테스트 (3개)"""

from pathlib import Path
from unittest.mock import patch

from locky.tools import ToolResult
from locky.tools.format import FormatTool


def test_format_tool_delegates_to_actions(tmp_path):
    """FormatTool.run()이 actions.format_code.run으로 위임하는지 확인."""
    tool = FormatTool()
    mock_result = {"status": "ok", "formatted": 2}
    with patch("actions.format_code.run", return_value=mock_result) as mock_run:
        result = tool.run(tmp_path)
    mock_run.assert_called_once_with(tmp_path)
    assert isinstance(result, ToolResult)
    assert result.ok


def test_format_tool_returns_tool_result(tmp_path):
    """FormatTool.run() 반환 타입이 ToolResult인지 확인."""
    tool = FormatTool()
    with patch("actions.format_code.run", return_value={"status": "ok"}):
        result = tool.run(tmp_path)
    assert isinstance(result, ToolResult)
    assert result.status == "ok"


def test_format_tool_propagates_error(tmp_path):
    """actions.format_code.run 오류 시 ToolResult에 반영되는지 확인."""
    tool = FormatTool()
    with patch(
        "actions.format_code.run",
        return_value={"status": "error", "message": "black not found"},
    ):
        result = tool.run(tmp_path)
    assert result.status == "error"
    assert not result.ok
