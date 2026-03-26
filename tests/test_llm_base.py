"""tests/test_llm_base.py -- BaseLLMClient, LLMResponse, LLMError 테스트."""

from __future__ import annotations

import pytest

from tools.llm.base import (
    BaseLLMClient,
    LLMAuthError,
    LLMConnectionError,
    LLMError,
    LLMModelNotFoundError,
    LLMResponse,
    LLMTimeoutError,
)


# ---------------------------------------------------------------------------
# LLMResponse
# ---------------------------------------------------------------------------


class TestLLMResponse:
    def test_basic_creation(self):
        r = LLMResponse(content="hello", model="gpt-4o", provider="openai")
        assert r.content == "hello"
        assert r.model == "gpt-4o"
        assert r.provider == "openai"
        assert r.usage is None

    def test_with_usage(self):
        r = LLMResponse(
            content="hi",
            model="m",
            provider="p",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert r.usage["prompt_tokens"] == 10
        assert r.usage["completion_tokens"] == 5


# ---------------------------------------------------------------------------
# LLMError hierarchy
# ---------------------------------------------------------------------------


class TestLLMErrors:
    def test_base_error(self):
        e = LLMError("fail", provider="test")
        assert str(e) == "fail"
        assert e.provider == "test"

    def test_connection_error(self):
        e = LLMConnectionError("no connect", provider="ollama")
        assert isinstance(e, LLMError)
        assert e.provider == "ollama"

    def test_auth_error(self):
        e = LLMAuthError("bad key", provider="openai")
        assert isinstance(e, LLMError)
        assert e.provider == "openai"

    def test_model_not_found_error(self):
        e = LLMModelNotFoundError("no model", provider="ollama")
        assert isinstance(e, LLMError)

    def test_timeout_error(self):
        e = LLMTimeoutError("timeout", provider="anthropic")
        assert isinstance(e, LLMError)

    def test_default_provider(self):
        e = LLMError("fail")
        assert e.provider == "unknown"


# ---------------------------------------------------------------------------
# BaseLLMClient is abstract
# ---------------------------------------------------------------------------


class TestBaseLLMClientAbstract:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseLLMClient()

    def test_concrete_subclass(self):
        class DummyClient(BaseLLMClient):
            def chat(self, messages, system=""):
                return LLMResponse(content="ok", model="dummy", provider="dummy")

            def stream(self, messages, system=""):
                yield "ok"

            def health_check(self):
                return True

            @property
            def provider_name(self):
                return "dummy"

            @property
            def model_name(self):
                return "dummy-model"

        client = DummyClient()
        assert client.provider_name == "dummy"
        assert client.model_name == "dummy-model"
        assert client.health_check() is True
        resp = client.chat([])
        assert resp.content == "ok"
        tokens = list(client.stream([]))
        assert tokens == ["ok"]
