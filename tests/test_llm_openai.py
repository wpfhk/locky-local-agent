"""tests/test_llm_openai.py -- OpenAILLMClient 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.llm.base import LLMAuthError, LLMConnectionError, LLMTimeoutError


class TestOpenAILLMClientInit:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from tools.llm.openai import OpenAILLMClient

        with pytest.raises(LLMAuthError, match="API 키가 설정되지 않았습니다"):
            OpenAILLMClient(model="gpt-4o")

    def test_explicit_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from tools.llm.openai import OpenAILLMClient

        client = OpenAILLMClient(model="gpt-4o", api_key="sk-test")
        assert client.provider_name == "openai"
        assert client.model_name == "gpt-4o"

    def test_env_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        from tools.llm.openai import OpenAILLMClient

        client = OpenAILLMClient(model="gpt-4o")
        assert client._api_key == "sk-env"

    def test_custom_base_url(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from tools.llm.openai import OpenAILLMClient

        client = OpenAILLMClient(model="m", base_url="http://localhost:8080/v1")
        assert client._base_url == "http://localhost:8080/v1"


class TestOpenAILLMClientChat:
    def test_chat_success(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from tools.llm.openai import OpenAILLMClient

        client = OpenAILLMClient(model="gpt-4o")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_resp.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.openai.httpx.Client", return_value=mock_http):
            resp = client.chat([{"role": "user", "content": "hi"}])

        assert resp.content == "hello"
        assert resp.provider == "openai"
        assert resp.usage["prompt_tokens"] == 10

    def test_chat_with_system(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from tools.llm.openai import OpenAILLMClient

        client = OpenAILLMClient(model="gpt-4o")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": None,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.openai.httpx.Client", return_value=mock_http):
            client.chat([{"role": "user", "content": "hi"}], system="be nice")

        call_args = mock_http.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["messages"][0] == {"role": "system", "content": "be nice"}

    def test_chat_auth_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-bad")
        from tools.llm.openai import OpenAILLMClient

        client = OpenAILLMClient(model="gpt-4o")

        mock_resp = MagicMock()
        mock_resp.status_code = 401

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.openai.httpx.Client", return_value=mock_http):
            with pytest.raises(LLMAuthError, match="인증 실패"):
                client.chat([{"role": "user", "content": "hi"}])

    def test_chat_connection_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from tools.llm.openai import OpenAILLMClient
        import httpx

        client = OpenAILLMClient(model="gpt-4o")

        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.ConnectError("refused")
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.openai.httpx.Client", return_value=mock_http):
            with pytest.raises(LLMConnectionError):
                client.chat([{"role": "user", "content": "hi"}])


class TestOpenAILLMClientHealthCheck:
    def test_health_check_success(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from tools.llm.openai import OpenAILLMClient

        client = OpenAILLMClient(model="gpt-4o")

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_http = MagicMock()
        mock_http.get.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.openai.httpx.Client", return_value=mock_http):
            assert client.health_check() is True

    def test_health_check_failure(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from tools.llm.openai import OpenAILLMClient

        client = OpenAILLMClient(model="gpt-4o")

        mock_http = MagicMock()
        mock_http.get.side_effect = Exception("fail")
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.openai.httpx.Client", return_value=mock_http):
            assert client.health_check() is False
