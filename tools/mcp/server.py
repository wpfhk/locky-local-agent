"""tools/mcp/server.py — MCP stdio server exposing locky actions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

import actions

# Tool definitions for MCP tools/list
_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "locky_format",
        "description": "Run code formatters (black, prettier, gofmt, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Project root path"},
                "check": {"type": "boolean", "description": "Check only, don't modify", "default": False},
                "lang": {"type": "string", "description": "Language (auto/python/javascript/etc.)", "default": "auto"},
            },
            "required": ["root"],
        },
    },
    {
        "name": "locky_scan",
        "description": "Run OWASP security pattern scan",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Project root path"},
                "severity": {"type": "string", "description": "Severity filter (critical/high/medium/low)"},
            },
            "required": ["root"],
        },
    },
    {
        "name": "locky_test",
        "description": "Run pytest test suite",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Project root path"},
                "path": {"type": "string", "description": "Specific test path"},
                "verbose": {"type": "boolean", "description": "Verbose output", "default": False},
            },
            "required": ["root"],
        },
    },
    {
        "name": "locky_deps",
        "description": "Check dependency versions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Project root path"},
            },
            "required": ["root"],
        },
    },
]

# Tool name -> (module_attr, kwarg_mapping)
_TOOL_DISPATCH: dict[str, tuple[str, dict[str, str]]] = {
    "locky_format": ("format_code", {"check": "check_only", "lang": "lang"}),
    "locky_scan": ("security_scan", {"severity": "severity_filter"}),
    "locky_test": ("test_runner", {"path": "path", "verbose": "verbose"}),
    "locky_deps": ("deps_check", {}),
}


class MCPServer:
    """MCP stdio server that exposes locky actions as tools.

    Implements JSON-RPC 2.0 over stdin/stdout for MCP protocol.
    """

    SERVER_NAME = "locky-mcp"
    SERVER_VERSION = "0.1.0"
    PROTOCOL_VERSION = "2024-11-05"

    def __init__(
        self,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ):
        self._stdin = stdin or sys.stdin
        self._stdout = stdout or sys.stdout
        self._initialized = False

    def _send(self, message: dict[str, Any]) -> None:
        """Send a JSON-RPC message to stdout."""
        data = json.dumps(message)
        # MCP uses Content-Length header framing
        header = f"Content-Length: {len(data)}\r\n\r\n"
        self._stdout.write(header)
        self._stdout.write(data)
        self._stdout.flush()

    def _read_message(self) -> dict[str, Any] | None:
        """Read a JSON-RPC message from stdin."""
        # Read Content-Length header
        line = self._stdin.readline()
        if not line:
            return None

        line = line.strip()
        if line.startswith("Content-Length:"):
            length = int(line.split(":")[1].strip())
            # Read empty line
            self._stdin.readline()
            # Read body
            body = self._stdin.read(length)
            return json.loads(body)

        # Try to parse as raw JSON (for simple clients)
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                return None

        return None

    def _handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        self._initialized = True
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": self.SERVER_NAME,
                "version": self.SERVER_VERSION,
            },
        }

    def _handle_tools_list(self) -> dict:
        """Handle tools/list request."""
        return {"tools": _TOOL_DEFINITIONS}

    def _handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in _TOOL_DISPATCH:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"error": f"Unknown tool: {tool_name}"}
                        ),
                    }
                ],
                "isError": True,
            }

        module_attr, kwarg_map = _TOOL_DISPATCH[tool_name]

        # Extract root
        root_str = arguments.pop("root", ".")
        root = Path(root_str).resolve()

        # Map argument names
        kwargs: dict[str, Any] = {}
        for arg_name, kwarg_name in kwarg_map.items():
            if arg_name in arguments:
                kwargs[kwarg_name] = arguments[arg_name]

        try:
            runner = getattr(actions, module_attr)
            result = runner(root, **kwargs)
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, default=str),
                }
            ],
            "isError": result.get("status") == "error",
        }

    def handle_request(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single JSON-RPC request and return a response.

        Args:
            message: Parsed JSON-RPC request

        Returns:
            JSON-RPC response dict, or None for notifications
        """
        method = message.get("method", "")
        params = message.get("params", {})
        req_id = message.get("id")

        if method == "initialize":
            result = self._handle_initialize(params)
        elif method == "notifications/initialized":
            return None  # notification, no response
        elif method == "tools/list":
            result = self._handle_tools_list()
        elif method == "tools/call":
            result = self._handle_tools_call(params)
        else:
            result = None
            if req_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            return None

        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }
        return None

    def run(self) -> None:
        """Main server loop. Reads from stdin, writes to stdout."""
        while True:
            try:
                message = self._read_message()
                if message is None:
                    break

                response = self.handle_request(message)
                if response is not None:
                    self._send(response)
            except (KeyboardInterrupt, EOFError):
                break
            except Exception:
                continue


def run_server() -> None:
    """Entry point for `locky serve-mcp`."""
    server = MCPServer()
    server.run()
