"""tools/llm/streaming.py -- Unified streaming output for all providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generator

from .base import BaseLLMClient, LLMResponse
from .tracker import TokenTracker


@dataclass
class StreamEvent:
    """Single streaming event."""

    token: str
    provider: str = ""
    model: str = ""
    done: bool = False
    usage: dict | None = None


class UnifiedStreamer:
    """Provider-agnostic streaming wrapper.

    Wraps ``BaseLLMClient.stream()`` and emits ``StreamEvent`` objects,
    optionally tracking tokens via a ``TokenTracker``.
    """

    def __init__(
        self,
        client: BaseLLMClient,
        tracker: TokenTracker | None = None,
    ):
        self._client = client
        self._tracker = tracker

    def stream_chat(
        self,
        messages: list[dict],
        system: str = "",
    ) -> Generator[StreamEvent, None, None]:
        """Yield ``StreamEvent`` for each token, plus a final done event."""
        provider = self._client.provider_name
        model = self._client.model_name
        collected: list[str] = []

        for token in self._client.stream(messages, system):
            collected.append(token)
            yield StreamEvent(token=token, provider=provider, model=model)

        # Final event
        usage: dict | None = None
        if self._tracker is not None:
            # Estimate tokens from collected text (rough: 1 token ~ 4 chars).
            approx_out = max(1, sum(len(t) for t in collected) // 4)
            # Input tokens are harder to estimate without provider data;
            # use a rough heuristic.
            approx_in = max(
                1,
                sum(len(m.get("content", "")) for m in messages) // 4,
            )
            rec = self._tracker.record(provider, model, approx_in, approx_out)
            usage = {
                "prompt_tokens": rec.prompt_tokens,
                "completion_tokens": rec.completion_tokens,
                "cost": rec.cost,
            }

        yield StreamEvent(
            token="",
            provider=provider,
            model=model,
            done=True,
            usage=usage,
        )

    def stream_to_string(
        self,
        messages: list[dict],
        system: str = "",
    ) -> tuple[str, dict | None]:
        """Stream and collect into a single string.

        Returns:
            (full_text, usage_dict_or_None)
        """
        parts: list[str] = []
        usage: dict | None = None

        for event in self.stream_chat(messages, system):
            if event.done:
                usage = event.usage
            else:
                parts.append(event.token)

        return "".join(parts), usage

    def stream_to_response(
        self,
        messages: list[dict],
        system: str = "",
    ) -> LLMResponse:
        """Stream and return an ``LLMResponse``."""
        text, usage = self.stream_to_string(messages, system)
        return LLMResponse(
            content=text,
            model=self._client.model_name,
            provider=self._client.provider_name,
            usage=usage,
        )
