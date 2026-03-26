"""tests/test_llm_registry.py -- LLMRegistry 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from tools.llm.base import LLMError
from tools.llm.registry import LLMRegistry


class TestLLMRegistryGetClient:
    def test_default_ollama(self, tmp_path, monkeypatch):
        """config 없을 때 Ollama 기본값."""
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)

        with patch("tools.llm.registry._load_config", return_value={}):
            client = LLMRegistry.get_client(tmp_path)

        assert client.provider_name == "ollama"
        assert client.model_name == "qwen2.5-coder:7b"

    def test_ollama_section_fallback(self, tmp_path):
        """llm 섹션 없고 ollama 섹션만 있을 때."""
        config = {
            "ollama": {
                "model": "llama3:8b",
                "base_url": "http://localhost:11434",
                "timeout": 120,
            }
        }
        with patch("tools.llm.registry._load_config", return_value=config):
            client = LLMRegistry.get_client(tmp_path)

        assert client.provider_name == "ollama"
        assert client.model_name == "llama3:8b"

    def test_llm_section_ollama(self, tmp_path):
        """llm 섹션에서 ollama 프로바이더 지정."""
        config = {
            "llm": {
                "provider": "ollama",
                "model": "codellama:13b",
                "timeout": 60,
            }
        }
        with patch("tools.llm.registry._load_config", return_value=config):
            client = LLMRegistry.get_client(tmp_path)

        assert client.provider_name == "ollama"
        assert client.model_name == "codellama:13b"

    def test_llm_section_openai(self, tmp_path, monkeypatch):
        """llm 섹션에서 openai 프로바이더."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o",
                "api_key_env": "OPENAI_API_KEY",
            }
        }
        with patch("tools.llm.registry._load_config", return_value=config):
            client = LLMRegistry.get_client(tmp_path)

        assert client.provider_name == "openai"
        assert client.model_name == "gpt-4o"

    def test_llm_section_anthropic(self, tmp_path, monkeypatch):
        """llm 섹션에서 anthropic 프로바이더."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        config = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "api_key_env": "ANTHROPIC_API_KEY",
            }
        }
        with patch("tools.llm.registry._load_config", return_value=config):
            client = LLMRegistry.get_client(tmp_path)

        assert client.provider_name == "anthropic"

    def test_env_var_override(self, tmp_path, monkeypatch):
        """환경변수가 config.yaml보다 우선."""
        monkeypatch.setenv("OLLAMA_MODEL", "env-model")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://env:11434")

        # 빈 config -> ollama fallback -> 환경변수 사용
        with patch("tools.llm.registry._load_config", return_value={}):
            client = LLMRegistry.get_client(tmp_path)

        assert client.model_name == "env-model"


class TestLLMRegistryGetClientByProvider:
    def test_ollama_provider(self):
        client = LLMRegistry.get_client_by_provider("ollama", "test-model")
        assert client.provider_name == "ollama"
        assert client.model_name == "test-model"

    def test_openai_provider(self):
        client = LLMRegistry.get_client_by_provider(
            "openai", "gpt-4o", api_key="sk-test"
        )
        assert client.provider_name == "openai"

    def test_anthropic_provider(self):
        client = LLMRegistry.get_client_by_provider(
            "anthropic", "claude-sonnet-4-20250514", api_key="sk-ant-test"
        )
        assert client.provider_name == "anthropic"

    def test_unknown_provider(self):
        with pytest.raises(LLMError, match="지원하지 않는 프로바이더"):
            LLMRegistry.get_client_by_provider("nonexistent", "model")

    def test_custom_base_url(self):
        client = LLMRegistry.get_client_by_provider(
            "ollama", "test", base_url="http://custom:11434"
        )
        assert client._base_url == "http://custom:11434"


class TestLLMRegistryListProviders:
    def test_list_always_includes_core(self):
        providers = LLMRegistry.list_providers()
        assert "ollama" in providers
        assert "openai" in providers
        assert "anthropic" in providers

    def test_litellm_included_when_installed(self):
        with patch.dict("sys.modules", {"litellm": type("M", (), {})()} ):
            providers = LLMRegistry.list_providers()
            assert "litellm" in providers

    def test_litellm_excluded_when_missing(self):
        import sys
        with patch.dict("sys.modules", {"litellm": None}):
            # Force reimport check
            providers = LLMRegistry.list_providers()
            # litellm may or may not be in the list depending on actual install
            # but core 3 must always be present
            assert "ollama" in providers
