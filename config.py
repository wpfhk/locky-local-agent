import os

from locky_cli.fs_context import get_filesystem_root

# Ollama 설정
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
OLLAMA_TASK_TIMEOUT = int(os.getenv("OLLAMA_TASK_TIMEOUT", "60"))  # task-breaking 전용 짧은 타임아웃


def get_mcp_filesystem_root() -> str:
    """현재 컨텍스트의 MCP 루트 경로 문자열."""
    return str(get_filesystem_root())

# 파이프라인 설정
MAX_RETRY_ITERATIONS = int(os.getenv("MAX_RETRY_ITERATIONS", "3"))
