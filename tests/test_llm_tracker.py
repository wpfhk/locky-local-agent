"""Tests for tools/llm/tracker.py -- TokenTracker + cost estimation."""

from __future__ import annotations

import pytest

from tools.llm.tracker import TokenTracker, UsageRecord, _estimate_cost


# ---------------------------------------------------------------------------
# _estimate_cost tests
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def test_ollama_free(self):
        assert _estimate_cost("ollama", "qwen2.5-coder:7b", 1000, 500) == 0.0

    def test_openai_gpt4o(self):
        cost = _estimate_cost("openai", "gpt-4o", 1_000_000, 1_000_000)
        # input: 2.50, output: 10.00 -> 12.50
        assert cost == 12.5

    def test_openai_gpt4o_mini(self):
        cost = _estimate_cost("openai", "gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == pytest.approx(0.75, rel=0.01)

    def test_anthropic_sonnet(self):
        cost = _estimate_cost("openai", "claude-sonnet-4-6", 100_000, 50_000)
        # input: 0.3, output: 0.75 -> 1.05
        assert cost == pytest.approx(1.05, rel=0.01)

    def test_unknown_model_free(self):
        assert _estimate_cost("openai", "super-new-model", 1000, 1000) == 0.0

    def test_prefix_match(self):
        cost = _estimate_cost("openai", "gpt-4o-2024-05-13", 1_000_000, 0)
        assert cost == 2.5  # matches "gpt-4o" prefix

    def test_zero_tokens(self):
        assert _estimate_cost("openai", "gpt-4o", 0, 0) == 0.0


# ---------------------------------------------------------------------------
# UsageRecord tests
# ---------------------------------------------------------------------------


class TestUsageRecord:
    def test_fields(self):
        rec = UsageRecord(
            provider="openai",
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001,
            timestamp="2026-01-01T00:00:00",
        )
        assert rec.provider == "openai"
        assert rec.model == "gpt-4o"
        assert rec.prompt_tokens == 100
        assert rec.completion_tokens == 50
        assert rec.cost == 0.001


# ---------------------------------------------------------------------------
# TokenTracker tests
# ---------------------------------------------------------------------------


class TestTokenTracker:
    def test_empty_tracker(self):
        tracker = TokenTracker()
        totals = tracker.get_session_total()
        assert totals["prompt_tokens"] == 0
        assert totals["completion_tokens"] == 0
        assert totals["total_tokens"] == 0
        assert totals["total_cost"] == 0.0
        assert totals["call_count"] == 0

    def test_record_single(self):
        tracker = TokenTracker()
        rec = tracker.record("openai", "gpt-4o", 1000, 500)
        assert isinstance(rec, UsageRecord)
        assert rec.prompt_tokens == 1000
        assert rec.completion_tokens == 500
        assert rec.timestamp  # non-empty

    def test_record_multiple(self):
        tracker = TokenTracker()
        tracker.record("openai", "gpt-4o", 1000, 500)
        tracker.record("ollama", "qwen2.5-coder:7b", 2000, 1000)
        totals = tracker.get_session_total()
        assert totals["prompt_tokens"] == 3000
        assert totals["completion_tokens"] == 1500
        assert totals["total_tokens"] == 4500
        assert totals["call_count"] == 2

    def test_ollama_zero_cost(self):
        tracker = TokenTracker()
        rec = tracker.record("ollama", "llama3", 5000, 3000)
        assert rec.cost == 0.0

    def test_format_summary_local(self):
        tracker = TokenTracker()
        tracker.record("ollama", "qwen2.5-coder:7b", 100, 50)
        summary = tracker.format_summary()
        assert "100" in summary
        assert "50" in summary
        assert "$0 (local)" in summary

    def test_format_summary_paid(self):
        tracker = TokenTracker()
        tracker.record("openai", "gpt-4o", 1_000_000, 100_000)
        summary = tracker.format_summary()
        assert "$" in summary
        assert "local" not in summary

    def test_reset(self):
        tracker = TokenTracker()
        tracker.record("openai", "gpt-4o", 1000, 500)
        tracker.reset()
        assert tracker.get_session_total()["call_count"] == 0
        assert len(tracker.records) == 0

    def test_multiple_providers_cost(self):
        tracker = TokenTracker()
        tracker.record("openai", "gpt-4o", 100_000, 50_000)
        tracker.record("ollama", "qwen2.5-coder:7b", 200_000, 100_000)
        totals = tracker.get_session_total()
        # Only openai should contribute cost
        assert totals["total_cost"] > 0
        # Ollama records have 0 cost
        assert tracker.records[1].cost == 0.0
