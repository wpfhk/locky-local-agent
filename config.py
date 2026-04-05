"""config.py -- Ollama 설정 (v4.0.0). 환경변수 기반 단순 설정."""

import os

# Ollama 설정
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
try:
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
except (ValueError, TypeError):
    OLLAMA_TIMEOUT = 300
