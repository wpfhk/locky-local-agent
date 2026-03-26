"""tools/llm/registry.py -- LLM provider registry + factory."""

from __future__ import annotations

import os
from pathlib import Path

from .base import BaseLLMClient, LLMError


# Provider name -> module.class mapping (lazy import)
_PROVIDERS: dict[str, tuple[str, str]] = {
    "ollama": ("tools.llm.ollama", "OllamaLLMClient"),
    "openai": ("tools.llm.openai", "OpenAILLMClient"),
    "anthropic": ("tools.llm.anthropic", "AnthropicLLMClient"),
    "litellm": ("tools.llm.litellm_adapter", "LiteLLMClient"),
}


class LLMRegistry:
    """프로바이더 레지스트리 + 팩토리.

    config.yaml / 환경변수 기반으로 적절한 LLM 클라이언트를 생성합니다.
    """

    @staticmethod
    def get_client(root: Path | None = None) -> BaseLLMClient:
        """config.yaml / 환경변수 기반으로 LLM 클라이언트 반환.

        우선순위:
        1. config.yaml ``llm`` 섹션
        2. config.yaml ``ollama`` 섹션 (하위 호환)
        3. ``OLLAMA_*`` 환경변수
        4. 기본값 (Ollama, qwen2.5-coder:7b)
        """
        cfg = _load_config(root)

        # 1. llm 섹션 확인
        llm_cfg = cfg.get("llm")
        if llm_cfg and isinstance(llm_cfg, dict):
            provider = llm_cfg.get("provider", "ollama")
            model = llm_cfg.get("model", "")
            api_key_env = llm_cfg.get("api_key_env")
            base_url = llm_cfg.get("base_url")
            timeout = int(llm_cfg.get("timeout", 300))

            api_key = os.environ.get(api_key_env, "") if api_key_env else None

            return LLMRegistry.get_client_by_provider(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            )

        # 2. ollama 섹션 fallback
        ollama_cfg = cfg.get("ollama", {})
        model = (
            os.environ.get("OLLAMA_MODEL")
            or ollama_cfg.get("model")
            or "qwen2.5-coder:7b"
        )
        base_url = (
            os.environ.get("OLLAMA_BASE_URL")
            or ollama_cfg.get("base_url")
            or "http://localhost:11434"
        )
        timeout = int(
            os.environ.get("OLLAMA_TIMEOUT")
            or ollama_cfg.get("timeout")
            or 300
        )

        from .ollama import OllamaLLMClient

        return OllamaLLMClient(model=model, base_url=base_url, timeout=timeout)

    @staticmethod
    def get_client_by_provider(
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 300,
    ) -> BaseLLMClient:
        """명시적 프로바이더/모델 지정으로 클라이언트 생성."""
        if provider not in _PROVIDERS:
            raise LLMError(
                f"지원하지 않는 프로바이더: '{provider}'. "
                f"사용 가능: {', '.join(_PROVIDERS.keys())}",
                provider=provider,
            )

        mod_path, cls_name = _PROVIDERS[provider]
        import importlib

        module = importlib.import_module(mod_path)
        cls = getattr(module, cls_name)

        # Build kwargs based on provider
        kwargs: dict = {"model": model, "timeout": timeout}
        if provider == "ollama":
            if base_url:
                kwargs["base_url"] = base_url
        elif provider in ("openai", "anthropic"):
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url
        elif provider == "litellm":
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url

        return cls(**kwargs)

    @staticmethod
    def get_lead_client(root: Path | None = None) -> BaseLLMClient:
        """Return the *lead* LLM client (complex reasoning tasks).

        Falls back to ``get_client()`` when no ``llm.lead`` section exists.
        """
        cfg = _load_config(root)
        llm_cfg = cfg.get("llm", {})
        lead_cfg = llm_cfg.get("lead") if isinstance(llm_cfg, dict) else None

        if lead_cfg and isinstance(lead_cfg, dict):
            return LLMRegistry.get_client_by_provider(
                provider=lead_cfg.get("provider", "ollama"),
                model=lead_cfg.get("model", ""),
                api_key=os.environ.get(lead_cfg.get("api_key_env", ""), "") or None,
                base_url=lead_cfg.get("base_url"),
                timeout=int(lead_cfg.get("timeout", 300)),
            )
        return LLMRegistry.get_client(root)

    @staticmethod
    def get_worker_client(root: Path | None = None) -> BaseLLMClient:
        """Return the *worker* LLM client (simple tasks like commit messages).

        Falls back to ``get_client()`` when no ``llm.worker`` section exists.
        """
        cfg = _load_config(root)
        llm_cfg = cfg.get("llm", {})
        worker_cfg = llm_cfg.get("worker") if isinstance(llm_cfg, dict) else None

        if worker_cfg and isinstance(worker_cfg, dict):
            return LLMRegistry.get_client_by_provider(
                provider=worker_cfg.get("provider", "ollama"),
                model=worker_cfg.get("model", ""),
                api_key=os.environ.get(worker_cfg.get("api_key_env", ""), "") or None,
                base_url=worker_cfg.get("base_url"),
                timeout=int(worker_cfg.get("timeout", 300)),
            )
        return LLMRegistry.get_client(root)

    @staticmethod
    def get_fallback_client(root: Path | None = None) -> BaseLLMClient | None:
        """Return the fallback LLM client, or None if not configured."""
        cfg = _load_config(root)
        llm_cfg = cfg.get("llm", {})
        fb_cfg = llm_cfg.get("fallback") if isinstance(llm_cfg, dict) else None

        if fb_cfg and isinstance(fb_cfg, dict):
            try:
                return LLMRegistry.get_client_by_provider(
                    provider=fb_cfg.get("provider", "ollama"),
                    model=fb_cfg.get("model", ""),
                    api_key=os.environ.get(fb_cfg.get("api_key_env", ""), "") or None,
                    base_url=fb_cfg.get("base_url"),
                    timeout=int(fb_cfg.get("timeout", 300)),
                )
            except Exception:
                return None
        return None

    @staticmethod
    def list_providers() -> list[str]:
        """사용 가능한 프로바이더 목록.

        litellm은 설치 여부에 따라 포함/제외.
        """
        available = ["ollama", "openai", "anthropic"]
        try:
            import litellm  # noqa: F401

            available.append("litellm")
        except ImportError:
            pass
        return available


def _load_config(root: Path | None) -> dict:
    """config.yaml 로드. 실패 시 빈 dict."""
    try:
        from locky_cli.config_loader import load_config

        return load_config(root or Path.cwd())
    except Exception:
        return {}
