"""locky_cli/config_loader.py — .locky/config.yaml 파서 및 설정 병합 (v3.0.0)"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_CONFIG_FILE = ".locky/config.yaml"

_DEFAULTS = {
    "ollama": {
        "model": "qwen2.5-coder:7b",
        "base_url": "http://localhost:11434",
        "timeout": 300,
    },
    "hook": {
        "steps": ["format", "test", "scan"],
    },
    "init": {
        "auto_profile": True,
    },
}


def load_config(root: Path) -> dict[str, Any]:
    """config.yaml을 읽어 dict 반환. 파일 없거나 파싱 실패 시 빈 dict."""
    path = Path(root) / _CONFIG_FILE
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore

        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_ollama_model(root: Path) -> str:
    """우선순위: 환경변수 > config.yaml > 기본값"""
    if env_val := os.getenv("OLLAMA_MODEL"):
        return env_val
    cfg = load_config(root)
    return cfg.get("ollama", {}).get("model") or _DEFAULTS["ollama"]["model"]


def get_ollama_base_url(root: Path) -> str:
    """우선순위: 환경변수 > config.yaml > 기본값"""
    if env_val := os.getenv("OLLAMA_BASE_URL"):
        return env_val
    cfg = load_config(root)
    return cfg.get("ollama", {}).get("base_url") or _DEFAULTS["ollama"]["base_url"]


def get_ollama_timeout(root: Path) -> int:
    """우선순위: 환경변수 > config.yaml > 기본값"""
    if env_val := os.getenv("OLLAMA_TIMEOUT"):
        try:
            return int(env_val)
        except ValueError:
            pass
    cfg = load_config(root)
    return int(cfg.get("ollama", {}).get("timeout") or _DEFAULTS["ollama"]["timeout"])


def get_hook_steps(root: Path) -> list[str]:
    """우선순위: config.yaml > 기본값"""
    cfg = load_config(root)
    steps = cfg.get("hook", {}).get("steps")
    if steps and isinstance(steps, list):
        return [str(s) for s in steps]
    return list(_DEFAULTS["hook"]["steps"])


def get_auto_profile(root: Path) -> bool:
    """init.auto_profile 설정 읽기"""
    cfg = load_config(root)
    val = cfg.get("init", {}).get("auto_profile")
    if val is None:
        return bool(_DEFAULTS["init"]["auto_profile"])
    return bool(val)


# ---------------------------------------------------------------------------
# v3.0.0: LLM / MCP 설정 헬퍼
# ---------------------------------------------------------------------------


def get_llm_config(root: Path) -> dict[str, Any]:
    """llm 섹션 읽기. 없으면 ollama 섹션에서 변환.

    Returns:
        {"provider": str, "model": str, "api_key_env": str|None,
         "base_url": str|None, "timeout": int}
    """
    cfg = load_config(root)

    # 1. llm 섹션 우선
    llm = cfg.get("llm")
    if llm and isinstance(llm, dict):
        return {
            "provider": llm.get("provider", "ollama"),
            "model": llm.get("model", "qwen2.5-coder:7b"),
            "api_key_env": llm.get("api_key_env"),
            "base_url": llm.get("base_url"),
            "timeout": int(llm.get("timeout", 300)),
        }

    # 2. ollama 섹션 fallback
    return {
        "provider": "ollama",
        "model": get_ollama_model(root),
        "api_key_env": None,
        "base_url": get_ollama_base_url(root),
        "timeout": get_ollama_timeout(root),
    }


def get_mcp_servers(root: Path) -> list[dict[str, Any]]:
    """mcp_servers 섹션 읽기. 없으면 빈 리스트."""
    cfg = load_config(root)
    servers = cfg.get("mcp_servers", [])
    if not isinstance(servers, list):
        return []
    return [s for s in servers if isinstance(s, dict) and s.get("name")]


# ---------------------------------------------------------------------------
# v3 Phase 2: Lead/Worker + Validation
# ---------------------------------------------------------------------------


def get_lead_config(root: Path) -> dict[str, Any]:
    """llm.lead 섹션 읽기.  없으면 get_llm_config() 반환."""
    cfg = load_config(root)
    llm = cfg.get("llm", {})
    lead = llm.get("lead") if isinstance(llm, dict) else None
    if lead and isinstance(lead, dict):
        return {
            "provider": lead.get("provider", "ollama"),
            "model": lead.get("model", ""),
            "api_key_env": lead.get("api_key_env"),
            "base_url": lead.get("base_url"),
            "timeout": int(lead.get("timeout", 300)),
        }
    return get_llm_config(root)


def get_worker_config(root: Path) -> dict[str, Any]:
    """llm.worker 섹션 읽기.  없으면 get_llm_config() 반환."""
    cfg = load_config(root)
    llm = cfg.get("llm", {})
    worker = llm.get("worker") if isinstance(llm, dict) else None
    if worker and isinstance(worker, dict):
        return {
            "provider": worker.get("provider", "ollama"),
            "model": worker.get("model", ""),
            "api_key_env": worker.get("api_key_env"),
            "base_url": worker.get("base_url"),
            "timeout": int(worker.get("timeout", 300)),
        }
    return get_llm_config(root)


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate config dict. Returns list of warnings/errors. Empty = valid."""
    issues: list[str] = []

    # LLM section
    llm = config.get("llm")
    if llm and isinstance(llm, dict):
        provider = llm.get("provider", "")
        valid_providers = {"ollama", "openai", "anthropic", "litellm"}

        # Check top-level provider
        if provider and provider not in valid_providers:
            issues.append(f"Unknown LLM provider: '{provider}'")

        # Check lead/worker sub-sections
        for role in ("lead", "worker", "fallback"):
            sub = llm.get(role)
            if sub and isinstance(sub, dict):
                sub_provider = sub.get("provider", "")
                if sub_provider and sub_provider not in valid_providers:
                    issues.append(f"Unknown provider in llm.{role}: '{sub_provider}'")
                sub_api_key_env = sub.get("api_key_env", "")
                if sub_provider in ("openai", "anthropic") and not sub_api_key_env:
                    issues.append(
                        f"llm.{role}: provider '{sub_provider}' requires api_key_env"
                    )

        # Top-level provider api_key check
        api_key_env = llm.get("api_key_env", "")
        if provider in ("openai", "anthropic") and not api_key_env:
            issues.append(f"llm.provider '{provider}' requires api_key_env")

    return issues


def detect_available_providers() -> dict[str, Any]:
    """Auto-detect which LLM providers are available.

    Returns:
        {"ollama": {"available": bool, "models": list},
         "openai": {"available": bool},
         "anthropic": {"available": bool}}
    """
    result: dict[str, Any] = {}

    # Ollama
    try:
        import httpx

        resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            result["ollama"] = {"available": True, "models": models}
        else:
            result["ollama"] = {"available": False, "models": []}
    except Exception:
        result["ollama"] = {"available": False, "models": []}

    # OpenAI
    result["openai"] = {"available": bool(os.getenv("OPENAI_API_KEY"))}

    # Anthropic
    result["anthropic"] = {"available": bool(os.getenv("ANTHROPIC_API_KEY"))}

    return result
