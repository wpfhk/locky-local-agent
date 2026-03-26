"""tools/llm/openai.py -- OpenAI-compatible LLM client (httpx 기반, SDK 불필요)."""

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

_DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAILLMClient(BaseLLMClient):
    """OpenAI Chat Completions API 클라이언트.

    OpenAI 호환 API (OpenRouter, vLLM, LM Studio 등)도 ``base_url`` 변경으로 지원.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str | None = None,
        timeout: int = 300,
    ):
        self._model = model
        self._api_key = api_key or os.environ.get(api_key_env, "")
        self._base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout

        if not self._api_key:
            raise LLMAuthError(
                f"OpenAI API 키가 설정되지 않았습니다. "
                f"환경변수 {api_key_env}를 설정하세요.",
                provider="openai",
            )

    # -- BaseLLMClient interface ------------------------------------------

    def chat(self, messages: list[dict], system: str = "") -> LLMResponse:
        req_messages = list(messages)
        if system:
            req_messages = [{"role": "system", "content": system}] + req_messages

        payload = {
            "model": self._model,
            "messages": req_messages,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )
                if resp.status_code == 401:
                    raise LLMAuthError(
                        "OpenAI API 인증 실패. API 키를 확인하세요.",
                        provider="openai",
                    )
                resp.raise_for_status()
                data = resp.json()
        except LLMAuthError:
            raise
        except httpx.ConnectError as exc:
            raise LLMConnectionError(
                f"OpenAI API에 연결할 수 없습니다 ({self._base_url}): {exc}",
                provider="openai",
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"OpenAI API 응답 타임아웃 ({self._timeout}s): {exc}",
                provider="openai",
            ) from exc

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage_data = data.get("usage")
        usage = (
            {
                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                "completion_tokens": usage_data.get("completion_tokens", 0),
            }
            if usage_data
            else None
        )
        return LLMResponse(
            content=content,
            model=self._model,
            provider="openai",
            usage=usage,
        )

    def stream(
        self, messages: list[dict], system: str = ""
    ) -> Generator[str, None, None]:
        req_messages = list(messages)
        if system:
            req_messages = [{"role": "system", "content": system}] + req_messages

        payload = {
            "model": self._model,
            "messages": req_messages,
            "stream": True,
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                ) as resp:
                    if resp.status_code == 401:
                        raise LLMAuthError(
                            "OpenAI API 인증 실패.",
                            provider="openai",
                        )
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
        except (LLMAuthError, LLMConnectionError, LLMTimeoutError):
            raise
        except httpx.ConnectError as exc:
            raise LLMConnectionError(
                f"OpenAI API 연결 실패: {exc}",
                provider="openai",
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"OpenAI 스트리밍 타임아웃: {exc}",
                provider="openai",
            ) from exc

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"{self._base_url}/models",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    # -- Private -----------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
