"""Tests for tools/llm/registry.py v3 Phase 2 additions -- lead/worker/fallback."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.llm.base import LLMError
from tools.llm.registry import LLMRegistry


@pytest.fixture
def config_root(tmp_path):
    locky_dir = tmp_path / ".locky"
    locky_dir.mkdir()
    return tmp_path


def _write_config(root: Path, content: str) -> None:
    (root / ".locky" / "config.yaml").write_text(content, encoding="utf-8")


class TestGetLeadClient:
    def test_lead_falls_back_to_default(self, config_root):
        _write_config(config_root, "ollama:\n  model: llama3\n")
        client = LLMRegistry.get_lead_client(config_root)
        assert client.provider_name == "ollama"

    def test_lead_from_config(self, config_root):
        _write_config(config_root, """
llm:
  lead:
    provider: ollama
    model: codellama:7b
  worker:
    provider: ollama
    model: qwen2.5-coder:7b
""")
        client = LLMRegistry.get_lead_client(config_root)
        assert client.provider_name == "ollama"
        assert client.model_name == "codellama:7b"


class TestGetWorkerClient:
    def test_worker_falls_back(self, config_root):
        _write_config(config_root, "ollama:\n  model: llama3\n")
        client = LLMRegistry.get_worker_client(config_root)
        assert client.provider_name == "ollama"

    def test_worker_from_config(self, config_root):
        _write_config(config_root, """
llm:
  worker:
    provider: ollama
    model: phi3:mini
""")
        client = LLMRegistry.get_worker_client(config_root)
        assert client.model_name == "phi3:mini"


class TestGetFallbackClient:
    def test_no_fallback_returns_none(self, config_root):
        _write_config(config_root, "ollama:\n  model: llama3\n")
        client = LLMRegistry.get_fallback_client(config_root)
        assert client is None

    def test_fallback_from_config(self, config_root):
        _write_config(config_root, """
llm:
  provider: ollama
  model: qwen2.5-coder:7b
  fallback:
    provider: ollama
    model: phi3:mini
""")
        client = LLMRegistry.get_fallback_client(config_root)
        assert client is not None
        assert client.model_name == "phi3:mini"

    def test_fallback_error_returns_none(self, config_root):
        _write_config(config_root, """
llm:
  fallback:
    provider: nonexistent_provider
    model: test
""")
        client = LLMRegistry.get_fallback_client(config_root)
        assert client is None
