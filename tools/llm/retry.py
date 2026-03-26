"""tools/llm/retry.py -- Exponential backoff retry + provider fallback."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Generator

from .base import (
    BaseLLMClient,
    LLMConnectionError,
    LLMError,
    LLMResponse,
    LLMTimeoutError,
)


@dataclass
class RetryConfig:
    """Retry behaviour configuration."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_errors: tuple[type[Exception], ...] = field(
        default_factory=lambda: (LLMConnectionError, LLMTimeoutError)
    )


class RetryHandler:
    """Exponential-backoff retry with optional fallback client.

    Usage::

        handler = RetryHandler(fallback_client=ollama_client)
        response = handler.chat_with_retry(primary_client, messages)
    """

    def __init__(
        self,
        config: RetryConfig | None = None,
        fallback_client: BaseLLMClient | None = None,
    ):
        self._config = config or RetryConfig()
        self._fallback = fallback_client
        self._last_error: Exception | None = None

    # -- public API --------------------------------------------------------

    @property
    def last_error(self) -> Exception | None:
        return self._last_error

    def execute(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *fn* with retry logic.

        Retries on retryable errors up to ``max_retries`` times with
        exponential backoff.  Non-retryable errors are raised immediately.
        """
        cfg = self._config
        last_exc: Exception | None = None

        for attempt in range(cfg.max_retries + 1):
            try:
                result = fn(*args, **kwargs)
                self._last_error = None
                return result
            except cfg.retryable_errors as exc:  # type: ignore[misc]
                last_exc = exc
                self._last_error = exc
                if attempt < cfg.max_retries:
                    delay = min(
                        cfg.base_delay * (cfg.exponential_base ** attempt),
                        cfg.max_delay,
                    )
                    time.sleep(delay)
            except LLMError:
                raise
            except Exception:
                raise

        # All retries exhausted – raise
        if last_exc is not None:
            raise last_exc

    def chat_with_retry(
        self,
        client: BaseLLMClient,
        messages: list[dict],
        system: str = "",
    ) -> LLMResponse:
        """Call ``client.chat()`` with retry, falling back if configured."""
        try:
            return self.execute(client.chat, messages, system)
        except LLMError:
            if self._fallback is not None:
                return self._fallback.chat(messages, system)
            raise

    def stream_with_retry(
        self,
        client: BaseLLMClient,
        messages: list[dict],
        system: str = "",
    ) -> Generator[str, None, None]:
        """Call ``client.stream()`` with retry, falling back if configured.

        Because generators are lazy, the retry wraps the *creation* of the
        generator.  If the first call fails we retry; once iteration begins
        errors propagate as-is.
        """
        cfg = self._config
        last_exc: Exception | None = None

        for attempt in range(cfg.max_retries + 1):
            try:
                gen = client.stream(messages, system)
                # Force the first yield to detect connection errors early.
                first_token = next(gen, None)
                if first_token is not None:
                    yield first_token
                yield from gen
                return
            except cfg.retryable_errors as exc:  # type: ignore[misc]
                last_exc = exc
                if attempt < cfg.max_retries:
                    delay = min(
                        cfg.base_delay * (cfg.exponential_base ** attempt),
                        cfg.max_delay,
                    )
                    time.sleep(delay)

        # Fallback
        if self._fallback is not None:
            yield from self._fallback.stream(messages, system)
            return

        if last_exc is not None:
            raise last_exc
