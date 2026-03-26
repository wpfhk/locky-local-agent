"""tests/test_mcp_server.py — MCP server export tests."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.mcp.server import MCPServer, _TOOL_DEFINITIONS, _TOOL_DISPATCH


class TestMCPServerInit:
    def test_default_streams(self):
        server = MCPServer()
        assert server._initialized is False

    def test_custom_streams(self):
        stdin = StringIO()
        stdout = StringIO()
        server = MCPServer(stdin=stdin, stdout=stdout)
        assert server._stdin is stdin
        assert server._stdout is stdout


class TestMCPServerHandleRequest:
    def setup_method(self):
        self.server = MCPServer(stdin=StringIO(), stdout=StringIO())

    def test_initialize(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = self.server.handle_request(msg)
        assert resp["id"] == 1
        result = resp["result"]
        assert result["serverInfo"]["name"] == "locky-mcp"
        assert "tools" in result["capabilities"]
        assert self.server._initialized is True

    def test_tools_list(self):
        msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = self.server.handle_request(msg)
        tools = resp["result"]["tools"]
        assert len(tools) == len(_TOOL_DEFINITIONS)
        tool_names = {t["name"] for t in tools}
        assert "locky_format" in tool_names
        assert "locky_scan" in tool_names
        assert "locky_test" in tool_names
        assert "locky_deps" in tool_names

    @patch("tools.mcp.server.actions")
    def test_tools_call_format(self, mock_actions):
        mock_actions.format_code = MagicMock(
            return_value={"status": "ok", "language": "python"}
        )
        msg = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "locky_format",
                "arguments": {"root": "/tmp/test", "check": True},
            },
        }
        resp = self.server.handle_request(msg)
        assert resp["id"] == 3
        content = resp["result"]["content"][0]
        assert content["type"] == "text"
        result_data = json.loads(content["text"])
        assert result_data["status"] == "ok"
        mock_actions.format_code.assert_called_once()

    @patch("tools.mcp.server.actions")
    def test_tools_call_scan(self, mock_actions):
        mock_actions.security_scan = MagicMock(
            return_value={"status": "clean", "issues": []}
        )
        msg = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "locky_scan",
                "arguments": {"root": "/tmp/test", "severity": "high"},
            },
        }
        resp = self.server.handle_request(msg)
        result_data = json.loads(resp["result"]["content"][0]["text"])
        assert result_data["status"] == "clean"

    def test_tools_call_unknown_tool(self):
        msg = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        }
        resp = self.server.handle_request(msg)
        assert resp["result"]["isError"] is True

    @patch("tools.mcp.server.actions")
    def test_tools_call_exception(self, mock_actions):
        mock_actions.test_runner = MagicMock(side_effect=RuntimeError("boom"))
        msg = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "locky_test",
                "arguments": {"root": "/tmp"},
            },
        }
        resp = self.server.handle_request(msg)
        result_data = json.loads(resp["result"]["content"][0]["text"])
        assert result_data["status"] == "error"
        assert "boom" in result_data["message"]

    def test_unknown_method(self):
        msg = {"jsonrpc": "2.0", "id": 7, "method": "unknown/method", "params": {}}
        resp = self.server.handle_request(msg)
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_notification_no_response(self):
        msg = {"method": "notifications/initialized", "params": {}}
        resp = self.server.handle_request(msg)
        assert resp is None


class TestMCPServerSend:
    def test_send_format(self):
        stdout = StringIO()
        server = MCPServer(stdout=stdout)
        server._send({"jsonrpc": "2.0", "id": 1, "result": {}})
        output = stdout.getvalue()
        assert output.startswith("Content-Length:")
        assert '"jsonrpc"' in output


class TestMCPServerReadMessage:
    def test_read_content_length_framing(self):
        body = '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}'
        content = f"Content-Length: {len(body)}\r\n\r\n{body}"
        stdin = StringIO(content)
        server = MCPServer(stdin=stdin)
        msg = server._read_message()
        assert msg["method"] == "initialize"

    def test_read_raw_json(self):
        body = '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}\n'
        stdin = StringIO(body)
        server = MCPServer(stdin=stdin)
        msg = server._read_message()
        assert msg["method"] == "tools/list"

    def test_read_eof(self):
        stdin = StringIO("")
        server = MCPServer(stdin=stdin)
        msg = server._read_message()
        assert msg is None


class TestToolDefinitions:
    def test_all_tools_have_dispatch(self):
        """Every tool definition has a dispatch entry."""
        for tool_def in _TOOL_DEFINITIONS:
            assert tool_def["name"] in _TOOL_DISPATCH

    def test_all_dispatch_has_definition(self):
        """Every dispatch entry has a tool definition."""
        tool_names = {t["name"] for t in _TOOL_DEFINITIONS}
        for name in _TOOL_DISPATCH:
            assert name in tool_names

    def test_tool_schema_valid(self):
        """All tool definitions have required fields."""
        for tool_def in _TOOL_DEFINITIONS:
            assert "name" in tool_def
            assert "description" in tool_def
            assert "inputSchema" in tool_def
            schema = tool_def["inputSchema"]
            assert schema["type"] == "object"
            assert "properties" in schema
