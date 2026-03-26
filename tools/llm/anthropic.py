"""tools/llm/anthropic.py -- Anthropic Messages API client (httpx 기반, SDK 불필요)."""

from __future__ import annotations

import json
import os
from typing import Generator

import httpx

from .base import (
    BaseLLMClient,
    LLMAuthError,
    LLMConnectionError,
    LLMResponse,
    LLMTimeoutError,
)

_DEFAULT_BASE_URL = "https://api.anthropic.com"
_API_VERSION = "2023-06-01"


class AnthropicLLMClient(BaseLLMClient):
    """Anthropic Messages API 클라이언트."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        api_key_env: str = "ANTHROPIC_API_KEY",
        base_url: str | None = None,
        timeout: int = 300,
        max_tokens: int = 4096,
    ):
        self._model = model
        self._api_key = api_key or os.environ.get(api_key_env, "")
        self._base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._max_tokens = max_tokens

        if not self._api_key:
            raise LLMAuthError(
                f"Anthropic API 키가 설정되지 않았습니다. "
                f"환경변수 {api_key_env}를 설정하세요.",
                provider="anthropic",
            )

    # -- BaseLLMClient interface ------------------------------------------

    def chat(self, messages: list[dict], system: str = "") -> LLMResponse:
        payload: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._base_url}/v1/messages",
                    json=payload,
                    headers=self._headers(),
                )
                if resp.status_code == 401:
                    raise LLMAuthError(
                        "Anthropic API 인증 실패. API 키를 확인하세요.",
                        provider="anthropic",
                    )
                resp.raise_for_status()
                data = resp.json()
        except LLMAuthError:
            raise
        except httpx.ConnectError as exc:
            raise LLMConnectionError(
                f"Anthropic API에 연결할 수 없습니다: {exc}",
                provider="anthropic",
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Anthropic API 응답 타임아웃 ({self._timeout}s): {exc}",
                provider="anthropic",
            ) from exc

        # Anthropic response: {"content": [{"type": "text", "text": "..."}], "usage": {...}}
        content_blocks = data.get("content", [])
        content = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )
        usage_data = data.get("usage")
        usage = (
            {
                "prompt_tokens": usage_data.get("input_tokens", 0),
                "completion_tokens": usage_data.get("output_tokens", 0),
            }
            if usage_data
            else None
        )
        return LLMResponse(
            content=content,
            model=self._model,
            provider="anthropic",
            usage=usage,
        )

    def stream(
        self, messages: list[dict], system: str = ""
    ) -> Generator[str, None, None]:
        payload: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
            "stream": True,
        }
        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=self._timeout) as client:
                with client.stream(
                    "POST",
                    f"{self._base_url}/v1/messages",
                    json=payload,
                    headers=self._headers(),
                ) as resp:
                    if resp.status_code == 401:
                        raise LLMAuthError(
                            "Anthropic API 인증 실패.",
                            provider="anthropic",
                        )
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        event_type = event.get("type", "")
                        if event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield text
                        elif event_type == "message_stop":
                            break
        except (LLMAuthError, LLMConnectionError, LLMTimeoutError):
            raise
        except httpx.ConnectError as exc:
            raise LLMConnectionError(
                f"Anthropic API 연결 실패: {exc}",
                provider="anthropic",
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Anthropic 스트리밍 타임아웃: {exc}",
                provider="anthropic",
            ) from exc

    def health_check(self) -> bool:
        # Anthropic has no /models endpoint; send a minimal request
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    f"{self._base_url}/v1/messages",
                    json={
                        "model": self._model,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                    headers=self._headers(),
                )
                # 200 or 400 (bad request) both mean the server is reachable
                return resp.status_code in (200, 400)
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    # -- Private -----------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "Content-Type": "application/json",
        }
