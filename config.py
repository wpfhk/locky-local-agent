import os
from pathlib import Path

from locky_cli.fs_context import get_filesystem_root


def _cfg(env_key: str, config_key_path: list, default: str) -> str:
    """우선순위: 환경변수 > .locky/config.yaml > 기본값"""
    if env_val := os.getenv(env_key):
        return env_val
    try:
        from locky_cli.config_loader import load_config

        cfg = load_config(Path.cwd())
        val = cfg
        for k in config_key_path:
            val = val[k]
        if val is not None:
            return str(val)
    except Exception:
        pass
    return default


# Ollama 설정
OLLAMA_BASE_URL = _cfg(
    "OLLAMA_BASE_URL", ["ollama", "base_url"], "http://localhost:11434"
)
OLLAMA_MODEL = _cfg("OLLAMA_MODEL", ["ollama", "model"], "qwen2.5-coder:7b")
OLLAMA_TIMEOUT = int(_cfg("OLLAMA_TIMEOUT", ["ollama", "timeout"], "300"))
OLLAMA_TASK_TIMEOUT = int(os.getenv("OLLAMA_TASK_TIMEOUT", "60"))


def get_mcp_filesystem_root() -> str:
    """현재 컨텍스트의 MCP 루트 경로 문자열."""
    return str(get_filesystem_root())


# Jira 설정
JIRA_BASE_URL = _cfg("JIRA_BASE_URL", ["jira", "base_url"], "")
JIRA_EMAIL = _cfg("JIRA_EMAIL", ["jira", "email"], "")
# JIRA_API_TOKEN: 환경변수 전용 (config.yaml에 저장 금지)

# 파이프라인 설정
MAX_RETRY_ITERATIONS = int(os.getenv("MAX_RETRY_ITERATIONS", "3"))
