"""tools/mcp/registry.py -- MCP server registry (config-based management)."""

from __future__ import annotations

from pathlib import Path

from .client import MCPClient, MCPTool
from .config import MCPServerConfig, load_mcp_config


class MCPRegistry:
    """MCP 서버 레지스트리.

    config.yaml의 ``mcp_servers`` 섹션에서 서버 목록을 로드하고
    MCPClient 인스턴스를 관리합니다.
    """

    def __init__(self, root: Path | None = None):
        self._root = root
        self._configs: list[MCPServerConfig] = []
        self._clients: dict[str, MCPClient] = {}
        self._loaded = False

    def load(self) -> None:
        """config.yaml에서 MCP 서버 설정을 로드."""
        self._configs = load_mcp_config(self._root)
        self._loaded = True

    def list_servers(self) -> list[MCPServerConfig]:
        """등록된 MCP 서버 목록."""
        if not self._loaded:
            self.load()
        return list(self._configs)

    def get_client(self, name: str) -> MCPClient:
        """이름으로 MCPClient를 가져옴. 없으면 생성.

        반환된 클라이언트는 ``start()`` 호출 전까지 프로세스가 시작되지 않습니다.
        """
        if name in self._clients:
            return self._clients[name]

        if not self._loaded:
            self.load()

        config = next((c for c in self._configs if c.name == name), None)
        if config is None:
            from .client import MCPError

            raise MCPError(
                f"MCP 서버 '{name}'이(가) config.yaml에 등록되지 않았습니다. "
                f"등록된 서버: {', '.join(c.name for c in self._configs) or '(없음)'}"
            )

        client = MCPClient(
            name=config.name,
            command=config.command,
            env=config.env or None,
            timeout=config.timeout,
        )
        self._clients[name] = client
        return client

    def list_all_tools(self) -> dict[str, list[MCPTool]]:
        """모든 등록된 서버의 도구 목록을 조회.

        Returns:
            {server_name: [MCPTool, ...]}
        """
        if not self._loaded:
            self.load()

        result: dict[str, list[MCPTool]] = {}
        for config in self._configs:
            try:
                client = self.get_client(config.name)
                client.start()
                result[config.name] = client.list_tools()
            except Exception:
                result[config.name] = []
        return result

    def stop_all(self) -> None:
        """모든 MCP 클라이언트 프로세스 종료."""
        for client in self._clients.values():
            try:
                client.stop()
            except Exception:
                pass
        self._clients.clear()

    def __enter__(self) -> MCPRegistry:
        self.load()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop_all()
