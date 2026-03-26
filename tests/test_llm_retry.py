"""Tests for tools/llm/retry.py -- RetryHandler + RetryConfig."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from tools.llm.base import (
    BaseLLMClient,
    LLMAuthError,
    LLMConnectionError,
    LLMError,
    LLMResponse,
    LLMTimeoutError,
)
from tools.llm.retry import RetryConfig, RetryHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(
    chat_side_effect=None,
    stream_side_effect=None,
    chat_return=None,
) -> MagicMock:
    """Create a mock BaseLLMClient."""
    client = MagicMock(spec=BaseLLMClient)
    client.provider_name = "mock"
    client.model_name = "mock-model"
    if chat_return:
        client.chat.return_value = chat_return
    if chat_side_effect:
        client.chat.side_effect = chat_side_effect
    if stream_side_effect:
        client.stream.side_effect = stream_side_effect
    return client


def _ok_response(content: str = "ok") -> LLMResponse:
    return LLMResponse(content=content, model="mock", provider="mock")


# ---------------------------------------------------------------------------
# RetryConfig tests
# ---------------------------------------------------------------------------


class TestRetryConfig:
    def test_defaults(self):
        cfg = RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.base_delay == 1.0
        assert cfg.max_delay == 30.0
        assert cfg.exponential_base == 2.0
        assert LLMConnectionError in cfg.retryable_errors
        assert LLMTimeoutError in cfg.retryable_errors

    def test_custom(self):
        cfg = RetryConfig(max_retries=5, base_delay=0.5)
        assert cfg.max_retries == 5
        assert cfg.base_delay == 0.5


# ---------------------------------------------------------------------------
# RetryHandler.execute tests
# ---------------------------------------------------------------------------


class TestRetryHandlerExecute:
    def test_success_first_try(self):
        handler = RetryHandler(config=RetryConfig(max_retries=3, base_delay=0))
        fn = MagicMock(return_value=42)
        assert handler.execute(fn) == 42
        assert fn.call_count == 1

    @patch("tools.llm.retry.time.sleep")
    def test_retries_on_connection_error(self, mock_sleep):
        handler = RetryHandler(config=RetryConfig(max_retries=2, base_delay=0.01))
        fn = MagicMock(
            side_effect=[
                LLMConnectionError("fail", provider="x"),
                LLMConnectionError("fail", provider="x"),
                42,
            ]
        )
        assert handler.execute(fn) == 42
        assert fn.call_count == 3

    @patch("tools.llm.retry.time.sleep")
    def test_retries_on_timeout_error(self, mock_sleep):
        handler = RetryHandler(config=RetryConfig(max_retries=1, base_delay=0.01))
        fn = MagicMock(
            side_effect=[LLMTimeoutError("slow", provider="x"), 99]
        )
        assert handler.execute(fn) == 99

    @patch("tools.llm.retry.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        handler = RetryHandler(config=RetryConfig(max_retries=2, base_delay=0.01))
        fn = MagicMock(
            side_effect=LLMConnectionError("down", provider="x")
        )
        with pytest.raises(LLMConnectionError):
            handler.execute(fn)
        assert fn.call_count == 3  # initial + 2 retries

    def test_non_retryable_raises_immediately(self):
        handler = RetryHandler(config=RetryConfig(max_retries=3))
        fn = MagicMock(side_effect=LLMAuthError("bad key", provider="x"))
        with pytest.raises(LLMAuthError):
            handler.execute(fn)
        assert fn.call_count == 1

    def test_generic_exception_raises_immediately(self):
        handler = RetryHandler(config=RetryConfig(max_retries=3))
        fn = MagicMock(side_effect=ValueError("boom"))
        with pytest.raises(ValueError):
            handler.execute(fn)
        assert fn.call_count == 1


# ---------------------------------------------------------------------------
# RetryHandler.chat_with_retry tests
# ---------------------------------------------------------------------------


class TestChatWithRetry:
    def test_success(self):
        client = _make_client(chat_return=_ok_response("hello"))
        handler = RetryHandler(config=RetryConfig(max_retries=1, base_delay=0))
        resp = handler.chat_with_retry(client, [{"role": "user", "content": "hi"}])
        assert resp.content == "hello"

    @patch("tools.llm.retry.time.sleep")
    def test_fallback_on_exhausted(self, mock_sleep):
        primary = _make_client(
            chat_side_effect=LLMConnectionError("down", provider="p")
        )
        fallback = _make_client(chat_return=_ok_response("fallback"))
        handler = RetryHandler(
            config=RetryConfig(max_retries=1, base_delay=0.01),
            fallback_client=fallback,
        )
        resp = handler.chat_with_retry(primary, [{"role": "user", "content": "hi"}])
        assert resp.content == "fallback"
        assert fallback.chat.call_count == 1

    @patch("tools.llm.retry.time.sleep")
    def test_no_fallback_raises(self, mock_sleep):
        primary = _make_client(
            chat_side_effect=LLMConnectionError("down", provider="p")
        )
        handler = RetryHandler(config=RetryConfig(max_retries=1, base_delay=0.01))
        with pytest.raises(LLMConnectionError):
            handler.chat_with_retry(primary, [{"role": "user", "content": "hi"}])

    @patch("tools.llm.retry.time.sleep")
    def test_retry_then_success(self, mock_sleep):
        client = _make_client(
            chat_side_effect=[
                LLMTimeoutError("slow", provider="x"),
                _ok_response("recovered"),
            ]
        )
        handler = RetryHandler(config=RetryConfig(max_retries=2, base_delay=0.01))
        resp = handler.chat_with_retry(client, [{"role": "user", "content": "hi"}])
        assert resp.content == "recovered"


# ---------------------------------------------------------------------------
# RetryHandler.stream_with_retry tests
# ---------------------------------------------------------------------------


class TestStreamWithRetry:
    def test_success(self):
        client = _make_client()
        client.stream.return_value = iter(["hello", " world"])
        handler = RetryHandler(config=RetryConfig(max_retries=1, base_delay=0))
        tokens = list(handler.stream_with_retry(client, []))
        assert tokens == ["hello", " world"]

    @patch("tools.llm.retry.time.sleep")
    def test_fallback_stream(self, mock_sleep):
        primary = _make_client(
            stream_side_effect=LLMConnectionError("down", provider="p")
        )
        fallback = _make_client()
        fallback.stream.return_value = iter(["fb"])
        handler = RetryHandler(
            config=RetryConfig(max_retries=1, base_delay=0.01),
            fallback_client=fallback,
        )
        tokens = list(handler.stream_with_retry(primary, []))
        assert tokens == ["fb"]

    @patch("tools.llm.retry.time.sleep")
    def test_no_fallback_stream_raises(self, mock_sleep):
        primary = _make_client(
            stream_side_effect=LLMConnectionError("down", provider="p")
        )
        handler = RetryHandler(config=RetryConfig(max_retries=1, base_delay=0.01))
        with pytest.raises(LLMConnectionError):
            list(handler.stream_with_retry(primary, []))

    def test_empty_stream(self):
        client = _make_client()
        client.stream.return_value = iter([])
        handler = RetryHandler(config=RetryConfig(max_retries=1, base_delay=0))
        tokens = list(handler.stream_with_retry(client, []))
        assert tokens == []


# ---------------------------------------------------------------------------
# Exponential backoff delay tests
# ---------------------------------------------------------------------------


class TestBackoffDelay:
    @patch("tools.llm.retry.time.sleep")
    def test_delay_increases(self, mock_sleep):
        handler = RetryHandler(
            config=RetryConfig(
                max_retries=3, base_delay=1.0, exponential_base=2.0, max_delay=100
            )
        )
        fn = MagicMock(side_effect=LLMConnectionError("fail", provider="x"))
        with pytest.raises(LLMConnectionError):
            handler.execute(fn)

        # Delays: 1*2^0=1, 1*2^1=2, 1*2^2=4
        calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert calls == [1.0, 2.0, 4.0]

    @patch("tools.llm.retry.time.sleep")
    def test_max_delay_cap(self, mock_sleep):
        handler = RetryHandler(
            config=RetryConfig(
                max_retries=5, base_delay=10.0, exponential_base=3.0, max_delay=30.0
            )
        )
        fn = MagicMock(side_effect=LLMConnectionError("fail", provider="x"))
        with pytest.raises(LLMConnectionError):
            handler.execute(fn)

        calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert all(d <= 30.0 for d in calls)


# ---------------------------------------------------------------------------
# last_error property
# ---------------------------------------------------------------------------


class TestLastError:
    def test_none_on_success(self):
        handler = RetryHandler()
        fn = MagicMock(return_value=1)
        handler.execute(fn)
        assert handler.last_error is None

    @patch("tools.llm.retry.time.sleep")
    def test_set_on_failure(self, mock_sleep):
        handler = RetryHandler(config=RetryConfig(max_retries=1, base_delay=0.01))
        fn = MagicMock(side_effect=LLMConnectionError("fail", provider="x"))
        with pytest.raises(LLMConnectionError):
            handler.execute(fn)
        assert handler.last_error is not None
        assert isinstance(handler.last_error, LLMConnectionError)
