"""tests/test_llm_ollama.py -- OllamaLLMClient 테스트."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.llm.base import LLMConnectionError, LLMModelNotFoundError, LLMTimeoutError
from tools.llm.ollama import OllamaLLMClient


@pytest.fixture
def client():
    return OllamaLLMClient(model="test-model", base_url="http://localhost:11434", timeout=10)


class TestOllamaLLMClientChat:
    def test_chat_success(self, client, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "hello world"}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.ollama.httpx.Client", return_value=mock_client):
            resp = client.chat([{"role": "user", "content": "hi"}])

        assert resp.content == "hello world"
        assert resp.provider == "ollama"
        assert resp.model == "test-model"

    def test_chat_with_system(self, client, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "ok"}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.ollama.httpx.Client", return_value=mock_client):
            resp = client.chat([{"role": "user", "content": "hi"}], system="be nice")

        call_args = mock_client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["system"] == "be nice"

    def test_chat_connection_error(self, client):
        import httpx

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.ollama.httpx.Client", return_value=mock_client):
            with pytest.raises(LLMConnectionError, match="연결할 수 없습니다"):
                client.chat([{"role": "user", "content": "hi"}])

    def test_chat_timeout_error(self, client):
        import httpx

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ReadTimeout("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.ollama.httpx.Client", return_value=mock_client):
            with pytest.raises(LLMTimeoutError, match="타임아웃"):
                client.chat([{"role": "user", "content": "hi"}])


class TestOllamaLLMClientHealthCheck:
    def test_health_check_success(self, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.ollama.httpx.Client", return_value=mock_client):
            assert client.health_check() is True

    def test_health_check_failure(self, client):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("fail")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.ollama.httpx.Client", return_value=mock_client):
            assert client.health_check() is False


class TestOllamaLLMClientProperties:
    def test_provider_name(self, client):
        assert client.provider_name == "ollama"

    def test_model_name(self, client):
        assert client.model_name == "test-model"


class TestOllamaLLMClientModelCheck:
    def test_check_model_available_true(self, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"models": [{"name": "test-model:latest"}]}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.ollama.httpx.Client", return_value=mock_client):
            assert client.check_model_available() is True

    def test_check_model_available_false(self, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"models": [{"name": "other-model:latest"}]}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.ollama.httpx.Client", return_value=mock_client):
            assert client.check_model_available() is False

    def test_ensure_available_no_server(self, client):
        with patch.object(client, "health_check", return_value=False):
            with pytest.raises(LLMConnectionError):
                client.ensure_available()

    def test_ensure_available_no_model(self, client):
        with patch.object(client, "health_check", return_value=True):
            with patch.object(client, "check_model_available", return_value=False):
                with pytest.raises(LLMModelNotFoundError):
                    client.ensure_available()
