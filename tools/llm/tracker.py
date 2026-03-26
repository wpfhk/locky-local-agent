"""tools/llm/tracker.py -- Token usage & cost tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Pricing table (per 1M tokens, USD)
# ---------------------------------------------------------------------------

_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-3": {"input": 0.25, "output": 1.25},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    # Google
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
}

# Providers whose models are always free (local).
_FREE_PROVIDERS = {"ollama"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class UsageRecord:
    """Single LLM call usage."""

    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: float
    timestamp: str


@dataclass
class TokenTracker:
    """Accumulates token usage across multiple LLM calls."""

    records: list[UsageRecord] = field(default_factory=list)

    # -- public API --------------------------------------------------------

    def record(
        self,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> UsageRecord:
        """Record a single LLM call's usage and return the record."""
        cost = _estimate_cost(provider, model, prompt_tokens, completion_tokens)
        rec = UsageRecord(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.records.append(rec)
        return rec

    def get_session_total(self) -> dict[str, Any]:
        """Aggregate totals across all records."""
        total_in = sum(r.prompt_tokens for r in self.records)
        total_out = sum(r.completion_tokens for r in self.records)
        total_cost = sum(r.cost for r in self.records)
        return {
            "prompt_tokens": total_in,
            "completion_tokens": total_out,
            "total_tokens": total_in + total_out,
            "total_cost": total_cost,
            "call_count": len(self.records),
        }

    def format_summary(self) -> str:
        """Human-readable one-line summary."""
        totals = self.get_session_total()
        parts = [
            f"{totals['prompt_tokens']:,} in / {totals['completion_tokens']:,} out",
        ]
        if totals["total_cost"] > 0:
            parts.append(f"${totals['total_cost']:.4f}")
        else:
            parts.append("$0 (local)")
        return " | ".join(parts)

    def reset(self) -> None:
        """Clear all records."""
        self.records.clear()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _estimate_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Estimate cost in USD.  Returns 0.0 for local/unknown models."""
    if provider.lower() in _FREE_PROVIDERS:
        return 0.0

    # Try exact match, then prefix match.
    pricing = _PRICING.get(model)
    if pricing is None:
        # Prefix match: "gpt-4o-2024-05-13" -> "gpt-4o"
        for key in _PRICING:
            if model.startswith(key):
                pricing = _PRICING[key]
                break

    if pricing is None:
        return 0.0

    cost_in = (prompt_tokens / 1_000_000) * pricing["input"]
    cost_out = (completion_tokens / 1_000_000) * pricing["output"]
    return round(cost_in + cost_out, 6)
