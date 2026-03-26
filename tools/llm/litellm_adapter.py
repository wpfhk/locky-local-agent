"""tools/llm/litellm_adapter.py -- Optional litellm adapter for 75+ providers."""

from __future__ import annotations

from typing import Generator

from .base import (
    BaseLLMClient,
    LLMConnectionError,
    LLMError,
    LLMResponse,
    LLMTimeoutError,
)


class LiteLLMClient(BaseLLMClient):
    """litellm 기반 LLM 클라이언트.

    ``pip install locky-agent[litellm]`` 으로 설치해야 사용 가능.
    litellm이 없으면 ``__init__`` 에서 ``LLMError`` 발생.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 300,
    ):
        try:
            import litellm as _litellm  # noqa: F401
        except ImportError as exc:
            raise LLMError(
                "litellm이 설치되지 않았습니다. "
                "`pip install locky-agent[litellm]` 또는 `pip install litellm`을 실행하세요.",
                provider="litellm",
            ) from exc

        self._litellm = _litellm
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout

    # -- BaseLLMClient interface ------------------------------------------

    def chat(self, messages: list[dict], system: str = "") -> LLMResponse:
        req_messages = list(messages)
        if system:
            req_messages = [{"role": "system", "content": system}] + req_messages

        kwargs: dict = {
            "model": self._model,
            "messages": req_messages,
            "timeout": self._timeout,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["api_base"] = self._base_url

        try:
            response = self._litellm.completion(**kwargs)
        except Exception as exc:
            exc_str = str(exc).lower()
            if "timeout" in exc_str:
                raise LLMTimeoutError(
                    f"litellm 타임아웃: {exc}", provider="litellm"
                ) from exc
            if "auth" in exc_str or "api key" in exc_str or "401" in exc_str:
                from .base import LLMAuthError

                raise LLMAuthError(
                    f"litellm 인증 실패: {exc}", provider="litellm"
                ) from exc
            raise LLMConnectionError(
                f"litellm 호출 실패: {exc}", provider="litellm"
            ) from exc

        choice = response.choices[0]
        content = choice.message.content or ""
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
            }
        return LLMResponse(
            content=content,
            model=self._model,
            provider="litellm",
            usage=usage,
        )

    def stream(
        self, messages: list[dict], system: str = ""
    ) -> Generator[str, None, None]:
        req_messages = list(messages)
        if system:
            req_messages = [{"role": "system", "content": system}] + req_messages

        kwargs: dict = {
            "model": self._model,
            "messages": req_messages,
            "stream": True,
            "timeout": self._timeout,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["api_base"] = self._base_url

        try:
            response = self._litellm.completion(**kwargs)
            for chunk in response:
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", "") or ""
                if content:
                    yield content
        except Exception as exc:
            raise LLMConnectionError(
                f"litellm 스트리밍 실패: {exc}", provider="litellm"
            ) from exc

    def health_check(self) -> bool:
        # litellm doesn't have a direct health check; we attempt a minimal call
        try:
            self._litellm.completion(
                model=self._model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
                timeout=10,
            )
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "litellm"

    @property
    def model_name(self) -> str:
        return self._model
