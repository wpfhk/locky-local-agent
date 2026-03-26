"""Tests for tools/llm/streaming.py -- UnifiedStreamer + StreamEvent."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tools.llm.base import BaseLLMClient, LLMResponse
from tools.llm.streaming import StreamEvent, UnifiedStreamer
from tools.llm.tracker import TokenTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_client(tokens: list[str] | None = None) -> MagicMock:
    client = MagicMock(spec=BaseLLMClient)
    client.provider_name = "test"
    client.model_name = "test-model"
    client.stream.return_value = iter(tokens or [])
    return client


# ---------------------------------------------------------------------------
# StreamEvent tests
# ---------------------------------------------------------------------------


class TestStreamEvent:
    def test_defaults(self):
        e = StreamEvent(token="hi")
        assert e.token == "hi"
        assert e.done is False
        assert e.usage is None

    def test_done_event(self):
        e = StreamEvent(token="", done=True, usage={"prompt_tokens": 10})
        assert e.done is True
        assert e.usage is not None


# ---------------------------------------------------------------------------
# UnifiedStreamer.stream_chat tests
# ---------------------------------------------------------------------------


class TestStreamChat:
    def test_yields_tokens(self):
        client = _mock_client(["Hello", " ", "world"])
        streamer = UnifiedStreamer(client)
        events = list(streamer.stream_chat([{"role": "user", "content": "hi"}]))

        # 3 token events + 1 done event
        assert len(events) == 4
        assert events[0].token == "Hello"
        assert events[1].token == " "
        assert events[2].token == "world"
        assert events[3].done is True
        assert events[3].token == ""

    def test_provider_model_set(self):
        client = _mock_client(["x"])
        streamer = UnifiedStreamer(client)
        events = list(streamer.stream_chat([]))
        assert events[0].provider == "test"
        assert events[0].model == "test-model"

    def test_empty_stream(self):
        client = _mock_client([])
        streamer = UnifiedStreamer(client)
        events = list(streamer.stream_chat([]))
        assert len(events) == 1
        assert events[0].done is True

    def test_tracker_integration(self):
        client = _mock_client(["Hello world this is a test"])
        tracker = TokenTracker()
        streamer = UnifiedStreamer(client, tracker=tracker)
        events = list(streamer.stream_chat([{"role": "user", "content": "test"}]))

        done_event = events[-1]
        assert done_event.done is True
        assert done_event.usage is not None
        assert done_event.usage["prompt_tokens"] > 0
        assert done_event.usage["completion_tokens"] > 0
        assert tracker.get_session_total()["call_count"] == 1

    def test_no_tracker_no_usage(self):
        client = _mock_client(["hi"])
        streamer = UnifiedStreamer(client, tracker=None)
        events = list(streamer.stream_chat([]))
        assert events[-1].usage is None


# ---------------------------------------------------------------------------
# UnifiedStreamer.stream_to_string tests
# ---------------------------------------------------------------------------


class TestStreamToString:
    def test_collects_text(self):
        client = _mock_client(["Hello", " ", "world"])
        streamer = UnifiedStreamer(client)
        text, usage = streamer.stream_to_string([])
        assert text == "Hello world"

    def test_with_tracker(self):
        client = _mock_client(["data"])
        tracker = TokenTracker()
        streamer = UnifiedStreamer(client, tracker=tracker)
        text, usage = streamer.stream_to_string([{"role": "user", "content": "q"}])
        assert text == "data"
        assert usage is not None

    def test_empty_string(self):
        client = _mock_client([])
        streamer = UnifiedStreamer(client)
        text, usage = streamer.stream_to_string([])
        assert text == ""


# ---------------------------------------------------------------------------
# UnifiedStreamer.stream_to_response tests
# ---------------------------------------------------------------------------


class TestStreamToResponse:
    def test_returns_llm_response(self):
        client = _mock_client(["hi", " there"])
        streamer = UnifiedStreamer(client)
        resp = streamer.stream_to_response([])
        assert isinstance(resp, LLMResponse)
        assert resp.content == "hi there"
        assert resp.provider == "test"
        assert resp.model == "test-model"

    def test_with_tracker(self):
        client = _mock_client(["test"])
        tracker = TokenTracker()
        streamer = UnifiedStreamer(client, tracker=tracker)
        resp = streamer.stream_to_response([{"role": "user", "content": "q"}])
        assert resp.usage is not None
