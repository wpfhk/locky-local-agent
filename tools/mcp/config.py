"""tools/mcp/config.py -- MCP server configuration loader."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MCPServerConfig:
    """단일 MCP 서버 설정."""

    name: str
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)
    timeout: int = 30


def load_mcp_config(root: Path | None = None) -> list[MCPServerConfig]:
    """config.yaml에서 MCP 서버 목록을 로드합니다.

    Returns:
        MCPServerConfig 목록. 설정 없으면 빈 리스트.
    """
    cfg = _load_raw_config(root)
    servers_raw = cfg.get("mcp_servers", [])
    if not isinstance(servers_raw, list):
        return []

    result: list[MCPServerConfig] = []
    for entry in servers_raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "")
        command = entry.get("command", [])
        if not name or not command:
            continue

        # 환경변수 치환: ${VAR} -> os.environ.get(VAR, "")
        env_raw = entry.get("env", {})
        env_resolved = _resolve_env(env_raw) if env_raw else {}
        timeout = int(entry.get("timeout", 30))

        result.append(
            MCPServerConfig(
                name=name,
                command=list(command),
                env=env_resolved,
                timeout=timeout,
            )
        )
    return result


_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _resolve_env(env_raw: dict) -> dict[str, str]:
    """환경변수 치환. ``${VAR}`` -> ``os.environ.get(VAR, "")``."""
    resolved: dict[str, str] = {}
    for key, value in env_raw.items():
        if isinstance(value, str):
            resolved[key] = _ENV_PATTERN.sub(
                lambda m: os.environ.get(m.group(1), ""), value
            )
        else:
            resolved[key] = str(value)
    return resolved


def _load_raw_config(root: Path | None) -> dict:
    """config.yaml 로드."""
    try:
        from locky_cli.config_loader import load_config

        return load_config(root or Path.cwd())
    except Exception:
        return {}
