"""Tests for config_loader.py v3 Phase 2 additions -- lead/worker + validation."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from locky_cli.config_loader import (
    detect_available_providers,
    get_lead_config,
    get_llm_config,
    get_worker_config,
    validate_config,
)


@pytest.fixture
def config_root(tmp_path):
    """Create a temp root with .locky/config.yaml."""
    locky_dir = tmp_path / ".locky"
    locky_dir.mkdir()
    return tmp_path


def _write_config(root: Path, content: str) -> None:
    (root / ".locky" / "config.yaml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# get_lead_config tests
# ---------------------------------------------------------------------------


class TestGetLeadConfig:
    def test_no_lead_falls_back(self, config_root):
        _write_config(config_root, "llm:\n  provider: openai\n  model: gpt-4o\n  api_key_env: OPENAI_API_KEY\n")
        cfg = get_lead_config(config_root)
        assert cfg["provider"] == "openai"
        assert cfg["model"] == "gpt-4o"

    def test_lead_present(self, config_root):
        _write_config(config_root, """
llm:
  lead:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
  worker:
    provider: ollama
    model: qwen2.5-coder:7b
""")
        cfg = get_lead_config(config_root)
        assert cfg["provider"] == "anthropic"
        assert cfg["model"] == "claude-sonnet-4-6"

    def test_no_config(self, config_root):
        # No config.yaml at all
        cfg = get_lead_config(config_root)
        assert cfg["provider"] == "ollama"


# ---------------------------------------------------------------------------
# get_worker_config tests
# ---------------------------------------------------------------------------


class TestGetWorkerConfig:
    def test_worker_present(self, config_root):
        _write_config(config_root, """
llm:
  lead:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
  worker:
    provider: ollama
    model: qwen2.5-coder:7b
""")
        cfg = get_worker_config(config_root)
        assert cfg["provider"] == "ollama"
        assert cfg["model"] == "qwen2.5-coder:7b"

    def test_no_worker_falls_back(self, config_root):
        _write_config(config_root, "ollama:\n  model: llama3\n")
        cfg = get_worker_config(config_root)
        assert cfg["provider"] == "ollama"
        assert cfg["model"] == "llama3"


# ---------------------------------------------------------------------------
# validate_config tests
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_valid_config(self):
        cfg = {"llm": {"provider": "ollama", "model": "qwen2.5-coder:7b"}}
        assert validate_config(cfg) == []

    def test_unknown_provider(self):
        cfg = {"llm": {"provider": "fake-ai"}}
        issues = validate_config(cfg)
        assert len(issues) == 1
        assert "Unknown LLM provider" in issues[0]

    def test_missing_api_key_env_openai(self):
        cfg = {"llm": {"provider": "openai", "model": "gpt-4o"}}
        issues = validate_config(cfg)
        assert any("api_key_env" in i for i in issues)

    def test_missing_api_key_env_anthropic(self):
        cfg = {"llm": {"provider": "anthropic", "model": "claude"}}
        issues = validate_config(cfg)
        assert any("api_key_env" in i for i in issues)

    def test_valid_with_api_key(self):
        cfg = {"llm": {"provider": "openai", "model": "gpt-4o", "api_key_env": "OPENAI_API_KEY"}}
        assert validate_config(cfg) == []

    def test_lead_worker_validation(self):
        cfg = {
            "llm": {
                "lead": {"provider": "invalid"},
                "worker": {"provider": "ollama", "model": "test"},
            }
        }
        issues = validate_config(cfg)
        assert any("llm.lead" in i for i in issues)

    def test_worker_needs_api_key(self):
        cfg = {
            "llm": {
                "worker": {"provider": "openai", "model": "gpt-4o"},
            }
        }
        issues = validate_config(cfg)
        assert any("api_key_env" in i for i in issues)

    def test_empty_config(self):
        assert validate_config({}) == []

    def test_no_llm_section(self):
        cfg = {"hook": {"steps": ["format"]}}
        assert validate_config(cfg) == []

    def test_ollama_no_api_key_needed(self):
        cfg = {"llm": {"provider": "ollama", "model": "test"}}
        assert validate_config(cfg) == []


# ---------------------------------------------------------------------------
# detect_available_providers tests
# ---------------------------------------------------------------------------


class TestDetectProviders:
    @patch("httpx.get")
    def test_ollama_available(self, mock_get):
        mock_resp = type("R", (), {"status_code": 200, "json": lambda self: {"models": [{"name": "llama3"}]}})()
        mock_get.return_value = mock_resp
        with patch.dict(os.environ, {}, clear=False):
            result = detect_available_providers()
        assert result["ollama"]["available"] is True
        assert "llama3" in result["ollama"]["models"]

    @patch("httpx.get", side_effect=Exception("no conn"))
    def test_ollama_unavailable(self, mock_get):
        result = detect_available_providers()
        assert result["ollama"]["available"] is False

    def test_openai_by_env(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            result = detect_available_providers()
        assert result["openai"]["available"] is True

    def test_openai_missing(self):
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            result = detect_available_providers()
        assert result["openai"]["available"] is False

    def test_anthropic_by_env(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False):
            result = detect_available_providers()
        assert result["anthropic"]["available"] is True
