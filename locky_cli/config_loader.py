"""locky_cli/config_loader.py — .locky/config.yaml 파서 및 설정 병합 (v1.1.0)"""

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
