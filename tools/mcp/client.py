"""tools/mcp/client.py -- MCP stdio client (JSON-RPC 2.0 over stdin/stdout)."""

from __future__ import annotations

import atexit
import json
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path


class MCPError(Exception):
    """MCP 통신 에러."""


class MCPTimeoutError(MCPError):
    """MCP 서버 응답 타임아웃."""


@dataclass
class MCPTool:
    """MCP 서버가 제공하는 도구 정보."""

    name: str
    description: str
    input_schema: dict


class MCPClient:
    """stdio 기반 MCP 클라이언트.

    하나의 MCP 서버 프로세스를 관리하며 JSON-RPC 2.0 프로토콜로 통신합니다.
    """

    def __init__(
        self,
        name: str,
        command: list[str],
        env: dict[str, str] | None = None,
        timeout: int = 30,
    ):
        self.name = name
        self._command = command
        self._env = env
        self._timeout = timeout
        self._process: subprocess.Popen | None = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._initialized = False

    def start(self) -> None:
        """MCP 서버 프로세스 시작 + initialize 핸드셰이크."""
        if self._process is not None:
            return

        import os

        proc_env = dict(os.environ)
        if self._env:
            proc_env.update(self._env)

        try:
            self._process = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=proc_env,
            )
        except FileNotFoundError as exc:
            raise MCPError(
                f"MCP 서버 '{self.name}' 시작 실패: 명령을 찾을 수 없습니다 -- {self._command[0]}"
            ) from exc
        except Exception as exc:
            raise MCPError(
                f"MCP 서버 '{self.name}' 시작 실패: {exc}"
            ) from exc

        # Register cleanup
        atexit.register(self._cleanup)

        # Send initialize
        result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "locky", "version": "3.0.0"},
        })
        self._initialized = True

        # Send initialized notification
        self._send_notification("notifications/initialized", {})

    def stop(self) -> None:
        """MCP 서버 프로세스 종료."""
        self._cleanup()

    def list_tools(self) -> list[MCPTool]:
        """tools/list 호출로 도구 목록 조회."""
        self._ensure_started()
        result = self._send_request("tools/list", {})
        tools_raw = result.get("tools", [])
        return [
            MCPTool(
                name=t.get("name", ""),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {}),
            )
            for t in tools_raw
            if t.get("name")
        ]

    def call_tool(self, tool_name: str, arguments: dict | None = None) -> dict:
        """tools/call 호출로 도구 실행."""
        self._ensure_started()
        result = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments or {},
        })
        return result

    def __enter__(self) -> MCPClient:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()

    # -- Private -----------------------------------------------------------

    def _ensure_started(self) -> None:
        if not self._initialized or self._process is None:
            raise MCPError(
                f"MCP 서버 '{self.name}'이(가) 시작되지 않았습니다. start()를 먼저 호출하세요."
            )
        if self._process.poll() is not None:
            raise MCPError(
                f"MCP 서버 '{self.name}' 프로세스가 종료되었습니다 (exit code: {self._process.returncode})."
            )

    def _send_request(self, method: str, params: dict) -> dict:
        """JSON-RPC request를 보내고 응답을 반환."""
        with self._lock:
            self._request_id += 1
            req_id = self._request_id

        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        self._write_message(message)
        response = self._read_response(req_id)

        if "error" in response:
            err = response["error"]
            raise MCPError(
                f"MCP 서버 '{self.name}' 에러 [{err.get('code', '?')}]: {err.get('message', 'unknown')}"
            )
        return response.get("result", {})

    def _send_notification(self, method: str, params: dict) -> None:
        """JSON-RPC notification (응답 없음)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        self._write_message(message)

    def _write_message(self, message: dict) -> None:
        """JSON-RPC 메시지를 stdin으로 전송."""
        if self._process is None or self._process.stdin is None:
            raise MCPError(f"MCP 서버 '{self.name}' stdin이 사용 불가합니다.")

        body = json.dumps(message)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        try:
            self._process.stdin.write(header.encode("utf-8"))
            self._process.stdin.write(body.encode("utf-8"))
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPError(
                f"MCP 서버 '{self.name}'에 메시지 전송 실패: {exc}"
            ) from exc

    def _read_response(self, expected_id: int) -> dict:
        """stdin에서 JSON-RPC 응답을 읽음."""
        if self._process is None or self._process.stdout is None:
            raise MCPError(f"MCP 서버 '{self.name}' stdout이 사용 불가합니다.")

        import select
        import sys

        stdout = self._process.stdout

        # Read Content-Length header
        content_length = self._read_content_length(stdout)
        if content_length is None:
            raise MCPTimeoutError(
                f"MCP 서버 '{self.name}'에서 응답 헤더를 읽지 못했습니다."
            )

        # Read body
        body_bytes = stdout.read(content_length)
        if not body_bytes or len(body_bytes) < content_length:
            raise MCPError(
                f"MCP 서버 '{self.name}'에서 불완전한 응답을 받았습니다."
            )

        try:
            data = json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise MCPError(
                f"MCP 서버 '{self.name}'에서 잘못된 JSON 응답: {exc}"
            ) from exc

        # Skip notifications, wait for our response id
        if data.get("id") != expected_id:
            # Could be a notification or wrong id; try reading again
            return self._read_response(expected_id)

        return data

    def _read_content_length(self, stdout) -> int | None:
        """Content-Length 헤더를 읽어 바이트 수 반환."""
        content_length = None
        while True:
            line = stdout.readline()
            if not line:
                return None
            line_str = line.decode("utf-8").strip()
            if line_str == "":
                break
            if line_str.lower().startswith("content-length:"):
                try:
                    content_length = int(line_str.split(":", 1)[1].strip())
                except ValueError:
                    pass
        return content_length

    def _cleanup(self) -> None:
        """프로세스 정리."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
            self._initialized = False
