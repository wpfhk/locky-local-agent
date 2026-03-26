"""tests/test_mcp_client.py -- MCPClient 테스트."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from tools.mcp.client import MCPClient, MCPError, MCPTimeoutError, MCPTool


class TestMCPClientInit:
    def test_basic_init(self):
        client = MCPClient(name="test", command=["echo", "hi"])
        assert client.name == "test"
        assert client._command == ["echo", "hi"]
        assert client._timeout == 30

    def test_custom_timeout(self):
        client = MCPClient(name="test", command=["echo"], timeout=60)
        assert client._timeout == 60

    def test_with_env(self):
        client = MCPClient(name="test", command=["echo"], env={"KEY": "val"})
        assert client._env == {"KEY": "val"}


class TestMCPClientStartStop:
    def test_start_success(self):
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.poll.return_value = None

        # Mock _send_request and _send_notification
        client = MCPClient(name="test", command=["echo"])

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(client, "_send_request", return_value={"protocolVersion": "2024-11-05"}):
                with patch.object(client, "_send_notification"):
                    client.start()

        assert client._initialized is True

    def test_start_command_not_found(self):
        client = MCPClient(name="test", command=["nonexistent_command_xyz"])

        with patch("subprocess.Popen", side_effect=FileNotFoundError("not found")):
            with pytest.raises(MCPError, match="시작 실패"):
                client.start()

    def test_stop(self):
        client = MCPClient(name="test", command=["echo"])
        mock_proc = MagicMock()
        client._process = mock_proc
        client._initialized = True

        client.stop()

        mock_proc.terminate.assert_called_once()
        assert client._process is None
        assert client._initialized is False

    def test_context_manager(self):
        client = MCPClient(name="test", command=["echo"])

        with patch.object(client, "start"):
            with patch.object(client, "stop") as mock_stop:
                with client:
                    pass
                mock_stop.assert_called_once()


class TestMCPClientEnsureStarted:
    def test_not_started_error(self):
        client = MCPClient(name="test", command=["echo"])
        with pytest.raises(MCPError, match="시작되지 않았습니다"):
            client._ensure_started()

    def test_process_exited_error(self):
        client = MCPClient(name="test", command=["echo"])
        client._initialized = True
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1
        mock_proc.returncode = 1
        client._process = mock_proc

        with pytest.raises(MCPError, match="프로세스가 종료"):
            client._ensure_started()


class TestMCPClientListTools:
    def test_list_tools(self):
        client = MCPClient(name="test", command=["echo"])
        client._initialized = True
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        client._process = mock_proc

        tools_response = {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "inputSchema": {"type": "object"},
                },
                {
                    "name": "write_file",
                    "description": "Write a file",
                    "inputSchema": {"type": "object"},
                },
            ]
        }

        with patch.object(client, "_send_request", return_value=tools_response):
            tools = client.list_tools()

        assert len(tools) == 2
        assert tools[0].name == "read_file"
        assert tools[0].description == "Read a file"
        assert tools[1].name == "write_file"


class TestMCPClientCallTool:
    def test_call_tool(self):
        client = MCPClient(name="test", command=["echo"])
        client._initialized = True
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        client._process = mock_proc

        result = {"content": [{"type": "text", "text": "file contents"}]}

        with patch.object(client, "_send_request", return_value=result):
            resp = client.call_tool("read_file", {"path": "/tmp/test"})

        assert resp["content"][0]["text"] == "file contents"


class TestMCPTool:
    def test_mcp_tool_creation(self):
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert "path" in tool.input_schema["properties"]
