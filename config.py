import os

# Ollama 설정
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

# MCP Filesystem 설정
MCP_FILESYSTEM_ROOT = os.getenv("MCP_FILESYSTEM_ROOT", os.getcwd())

# 파이프라인 설정
MAX_RETRY_ITERATIONS = int(os.getenv("MAX_RETRY_ITERATIONS", "3"))
