"""tests/test_llm_litellm.py -- LiteLLMClient 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.llm.base import LLMError


class TestLiteLLMClientImportError:
    def test_import_error_message(self):
        """litellm 미설치 시 명확한 에러 메시지."""
        with patch.dict("sys.modules", {"litellm": None}):
            # Force fresh import
            import importlib
            import tools.llm.litellm_adapter as mod

            importlib.reload(mod)

            with pytest.raises(LLMError, match="litellm이 설치되지 않았습니다"):
                mod.LiteLLMClient(model="gpt-4o")


class TestLiteLLMClientWithMock:
    def _make_client(self):
        """Mock litellm으로 LiteLLMClient 생성."""
        mock_litellm = MagicMock()
        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            import importlib
            import tools.llm.litellm_adapter as mod

            importlib.reload(mod)
            client = mod.LiteLLMClient(model="gpt-4o")
            client._litellm = mock_litellm
            return client, mock_litellm

    def test_chat_success(self):
        client, mock_litellm = self._make_client()

        mock_choice = MagicMock()
        mock_choice.message.content = "hello from litellm"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_litellm.completion.return_value = mock_response

        resp = client.chat([{"role": "user", "content": "hi"}])
        assert resp.content == "hello from litellm"
        assert resp.provider == "litellm"

    def test_chat_with_system(self):
        client, mock_litellm = self._make_client()

        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None
        mock_litellm.completion.return_value = mock_response

        client.chat([{"role": "user", "content": "hi"}], system="be nice")

        call_args = mock_litellm.completion.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert messages[0] == {"role": "system", "content": "be nice"}

    def test_properties(self):
        client, _ = self._make_client()
        assert client.provider_name == "litellm"
        assert client.model_name == "gpt-4o"

    def test_health_check_success(self):
        client, mock_litellm = self._make_client()
        mock_litellm.completion.return_value = MagicMock()
        assert client.health_check() is True

    def test_health_check_failure(self):
        client, mock_litellm = self._make_client()
        mock_litellm.completion.side_effect = Exception("fail")
        assert client.health_check() is False
