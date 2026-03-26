"""tools/llm/ollama.py -- Ollama LLM client (BaseLLMClient 구현)."""

from __future__ import annotations

import json
from typing import Generator

import httpx

from .base import (
    BaseLLMClient,
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMResponse,
    LLMTimeoutError,
)


class OllamaLLMClient(BaseLLMClient):
    """Ollama API 기반 LLM 클라이언트.

    기존 ``tools/ollama_client.OllamaClient`` 의 기능을
    ``BaseLLMClient`` 인터페이스로 재구현합니다.
    """

    def __init__(
        self,
        model: str = "qwen2.5-coder:7b",
        base_url: str = "http://localhost:11434",
        timeout: int = 300,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # -- BaseLLMClient interface ------------------------------------------

    def chat(self, messages: list[dict], system: str = "") -> LLMResponse:
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError as exc:
            raise LLMConnectionError(
                f"Ollama 서버에 연결할 수 없습니다 ({self._base_url}): {exc}",
                provider="ollama",
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Ollama 응답 타임아웃 ({self._timeout}s): {exc}",
                provider="ollama",
            ) from exc

        content = data.get("message", {}).get("content", "")
        return LLMResponse(
            content=content,
            model=self._model,
            provider="ollama",
            usage=None,
        )

    def stream(
        self, messages: list[dict], system: str = ""
    ) -> Generator[str, None, None]:
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }
        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=self._timeout) as client:
                with client.stream(
                    "POST", f"{self._base_url}/api/chat", json=payload
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            if token := data.get("message", {}).get("content", ""):
                                yield token
                            if data.get("done"):
                                break
        except httpx.ConnectError as exc:
            raise LLMConnectionError(
                f"Ollama 서버에 연결할 수 없습니다: {exc}",
                provider="ollama",
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Ollama 스트리밍 타임아웃: {exc}",
                provider="ollama",
            ) from exc

    def health_check(self) -> bool:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    # -- Ollama 전용 헬퍼 --------------------------------------------------

    def check_model_available(self) -> bool:
        """모델이 설치되어 있는지 확인."""
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                models = resp.json().get("models", [])
                model_base = self._model.split(":")[0]
                return any(
                    m.get("name", "") == self._model
                    or m.get("name", "").startswith(model_base + ":")
                    for m in models
                )
        except Exception:
            return False

    def ensure_available(self) -> None:
        """Ollama 서버 + 모델 사용 가능 여부 확인. 불가 시 예외."""
        if not self.health_check():
            raise LLMConnectionError(
                f"Ollama 서버에 연결할 수 없습니다 ({self._base_url}). "
                "`ollama serve`를 실행하세요.",
                provider="ollama",
            )
        if not self.check_model_available():
            raise LLMModelNotFoundError(
                f"모델 '{self._model}'이(가) 설치되지 않았습니다. "
                f"`ollama pull {self._model}`을 실행하세요.",
                provider="ollama",
            )
