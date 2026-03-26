"""tests/test_mcp_registry.py -- MCPRegistry + config 테스트."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.mcp.client import MCPError
from tools.mcp.config import MCPServerConfig, load_mcp_config, _resolve_env
from tools.mcp.registry import MCPRegistry


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestLoadMCPConfig:
    def test_empty_config(self):
        with patch("tools.mcp.config._load_raw_config", return_value={}):
            servers = load_mcp_config()
        assert servers == []

    def test_valid_config(self):
        config = {
            "mcp_servers": [
                {
                    "name": "filesystem",
                    "command": ["npx", "@mcp/server-fs", "/tmp"],
                },
                {
                    "name": "github",
                    "command": ["npx", "@mcp/server-github"],
                    "env": {"GITHUB_TOKEN": "my-token"},
                    "timeout": 60,
                },
            ]
        }
        with patch("tools.mcp.config._load_raw_config", return_value=config):
            servers = load_mcp_config()

        assert len(servers) == 2
        assert servers[0].name == "filesystem"
        assert servers[0].command == ["npx", "@mcp/server-fs", "/tmp"]
        assert servers[1].name == "github"
        assert servers[1].env == {"GITHUB_TOKEN": "my-token"}
        assert servers[1].timeout == 60

    def test_invalid_entries_skipped(self):
        config = {
            "mcp_servers": [
                {"name": "valid", "command": ["echo"]},
                {"name": "", "command": []},  # invalid: empty name/command
                "not a dict",  # invalid: not a dict
                {"name": "no_cmd"},  # invalid: no command
            ]
        }
        with patch("tools.mcp.config._load_raw_config", return_value=config):
            servers = load_mcp_config()

        assert len(servers) == 1
        assert servers[0].name == "valid"

    def test_not_a_list(self):
        config = {"mcp_servers": "invalid"}
        with patch("tools.mcp.config._load_raw_config", return_value=config):
            servers = load_mcp_config()
        assert servers == []


class TestResolveEnv:
    def test_simple_substitution(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "secret123")
        result = _resolve_env({"TOKEN": "${MY_TOKEN}"})
        assert result == {"TOKEN": "secret123"}

    def test_missing_env_var(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        result = _resolve_env({"KEY": "${MISSING_VAR}"})
        assert result == {"KEY": ""}

    def test_mixed_content(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        result = _resolve_env({"URL": "http://${HOST}:8080"})
        assert result == {"URL": "http://localhost:8080"}

    def test_no_substitution(self):
        result = _resolve_env({"KEY": "plain_value"})
        assert result == {"KEY": "plain_value"}

    def test_non_string_value(self):
        result = _resolve_env({"PORT": 8080})
        assert result == {"PORT": "8080"}


# ---------------------------------------------------------------------------
# MCPServerConfig
# ---------------------------------------------------------------------------


class TestMCPServerConfig:
    def test_defaults(self):
        cfg = MCPServerConfig(name="test", command=["echo"])
        assert cfg.timeout == 30
        assert cfg.env == {}


# ---------------------------------------------------------------------------
# MCPRegistry
# ---------------------------------------------------------------------------


class TestMCPRegistry:
    def test_list_servers(self):
        configs = [
            MCPServerConfig(name="fs", command=["npx", "fs"]),
            MCPServerConfig(name="git", command=["npx", "git"]),
        ]
        with patch("tools.mcp.registry.load_mcp_config", return_value=configs):
            registry = MCPRegistry()
            servers = registry.list_servers()

        assert len(servers) == 2
        assert servers[0].name == "fs"

    def test_get_client_creates(self):
        configs = [MCPServerConfig(name="fs", command=["npx", "fs"])]
        with patch("tools.mcp.registry.load_mcp_config", return_value=configs):
            registry = MCPRegistry()
            client = registry.get_client("fs")

        assert client.name == "fs"

    def test_get_client_caches(self):
        configs = [MCPServerConfig(name="fs", command=["npx", "fs"])]
        with patch("tools.mcp.registry.load_mcp_config", return_value=configs):
            registry = MCPRegistry()
            client1 = registry.get_client("fs")
            client2 = registry.get_client("fs")

        assert client1 is client2

    def test_get_client_not_found(self):
        with patch("tools.mcp.registry.load_mcp_config", return_value=[]):
            registry = MCPRegistry()
            with pytest.raises(MCPError, match="등록되지 않았습니다"):
                registry.get_client("nonexistent")

    def test_stop_all(self):
        configs = [MCPServerConfig(name="fs", command=["echo"])]
        with patch("tools.mcp.registry.load_mcp_config", return_value=configs):
            registry = MCPRegistry()
            client = registry.get_client("fs")

        with patch.object(client, "stop") as mock_stop:
            registry.stop_all()
            mock_stop.assert_called_once()

        assert len(registry._clients) == 0

    def test_context_manager(self):
        configs = [MCPServerConfig(name="fs", command=["echo"])]
        with patch("tools.mcp.registry.load_mcp_config", return_value=configs):
            with MCPRegistry() as registry:
                servers = registry.list_servers()
                assert len(servers) == 1
