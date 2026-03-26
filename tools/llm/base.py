"""tools/llm/base.py -- BaseLLMClient ABC + error hierarchy + LLMResponse."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


@dataclass
class LLMResponse:
    """LLM 호출 응답."""

    content: str
    model: str
    provider: str
    usage: dict | None = field(default=None)


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class LLMError(Exception):
    """LLM 호출 실패 시 기본 예외."""

    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message)
        self.provider = provider


class LLMConnectionError(LLMError):
    """프로바이더 서버 연결 실패."""


class LLMAuthError(LLMError):
    """API 키 인증 실패."""


class LLMModelNotFoundError(LLMError):
    """지정 모델 없음."""


class LLMTimeoutError(LLMError):
    """응답 타임아웃."""


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BaseLLMClient(ABC):
    """모든 LLM 프로바이더가 구현해야 하는 인터페이스."""

    @abstractmethod
    def chat(self, messages: list[dict], system: str = "") -> LLMResponse:
        """동기 채팅 호출.

        Args:
            messages: ``[{"role": "user"|"assistant", "content": "..."}]``
            system: 시스템 프롬프트 (선택)

        Returns:
            LLMResponse
        """
        ...

    @abstractmethod
    def stream(
        self, messages: list[dict], system: str = ""
    ) -> Generator[str, None, None]:
        """동기 스트리밍. 토큰별 yield.

        Args:
            messages: 메시지 목록
            system: 시스템 프롬프트

        Yields:
            토큰 문자열
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """프로바이더 연결 상태 확인."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """프로바이더 식별자 (예: ``'ollama'``, ``'openai'``)."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """현재 사용 중인 모델명."""
        ...
