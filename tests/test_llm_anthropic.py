"""tests/test_llm_anthropic.py -- AnthropicLLMClient 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.llm.base import LLMAuthError, LLMConnectionError


class TestAnthropicLLMClientInit:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from tools.llm.anthropic import AnthropicLLMClient

        with pytest.raises(LLMAuthError, match="API 키가 설정되지 않았습니다"):
            AnthropicLLMClient()

    def test_explicit_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient(api_key="sk-ant-test")
        assert client.provider_name == "anthropic"
        assert client._api_key == "sk-ant-test"

    def test_env_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env")
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient()
        assert client._api_key == "sk-ant-env"


class TestAnthropicLLMClientChat:
    def test_chat_success(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"type": "text", "text": "hello from claude"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        mock_resp.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.anthropic.httpx.Client", return_value=mock_http):
            resp = client.chat([{"role": "user", "content": "hi"}])

        assert resp.content == "hello from claude"
        assert resp.provider == "anthropic"
        assert resp.usage["prompt_tokens"] == 10
        assert resp.usage["completion_tokens"] == 5

    def test_chat_with_system(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"type": "text", "text": "ok"}],
            "usage": None,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.anthropic.httpx.Client", return_value=mock_http):
            client.chat([{"role": "user", "content": "hi"}], system="be nice")

        call_args = mock_http.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["system"] == "be nice"

    def test_chat_auth_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-bad")
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 401

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.anthropic.httpx.Client", return_value=mock_http):
            with pytest.raises(LLMAuthError, match="인증 실패"):
                client.chat([{"role": "user", "content": "hi"}])

    def test_chat_connection_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        from tools.llm.anthropic import AnthropicLLMClient
        import httpx

        client = AnthropicLLMClient()

        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.ConnectError("refused")
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.anthropic.httpx.Client", return_value=mock_http):
            with pytest.raises(LLMConnectionError):
                client.chat([{"role": "user", "content": "hi"}])

    def test_chat_multiple_content_blocks(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [
                {"type": "text", "text": "part1 "},
                {"type": "text", "text": "part2"},
            ],
            "usage": None,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.anthropic.httpx.Client", return_value=mock_http):
            resp = client.chat([{"role": "user", "content": "hi"}])

        assert resp.content == "part1 part2"


class TestAnthropicLLMClientHealthCheck:
    def test_health_check_200(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.anthropic.httpx.Client", return_value=mock_http):
            assert client.health_check() is True

    def test_health_check_400_is_reachable(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient()

        mock_resp = MagicMock()
        mock_resp.status_code = 400

        mock_http = MagicMock()
        mock_http.post.return_value = mock_resp
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.anthropic.httpx.Client", return_value=mock_http):
            assert client.health_check() is True

    def test_health_check_exception(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        from tools.llm.anthropic import AnthropicLLMClient

        client = AnthropicLLMClient()

        mock_http = MagicMock()
        mock_http.post.side_effect = Exception("fail")
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with patch("tools.llm.anthropic.httpx.Client", return_value=mock_http):
            assert client.health_check() is False
