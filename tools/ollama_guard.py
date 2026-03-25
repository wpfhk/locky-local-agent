"""tools/ollama_guard.py — Ollama 서버 헬스체크 및 자동 시작. (v1.0.0)"""

from __future__ import annotations

import subprocess
import time


def ensure_ollama(
    base_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:7b",
    timeout: int = 10,
) -> dict:
    """Ollama 서버가 준비됐는지 확인하고, 미기동 시 백그라운드 시작을 시도합니다.

    1. GET /api/tags 로 헬스체크
    2. 실패 시: `ollama serve` 백그라운드 시작 (3초 대기 후 재시도)
    3. 모델 미설치 확인 후 설치 안내 제공

    Returns:
        {"status": "ok"|"started"|"error", "message": str, "model_available": bool}
    """
    # 1차 헬스체크
    tags = _fetch_tags(base_url, timeout)
    if tags is None:
        # Ollama 미기동 → 백그라운드 시작 시도
        started = _try_start_ollama()
        if not started:
            return {
                "status": "error",
                "message": (
                    f"Ollama 서버에 연결할 수 없습니다 ({base_url}). "
                    "수동으로 `ollama serve`를 실행하세요."
                ),
                "model_available": False,
            }
        time.sleep(3)
        tags = _fetch_tags(base_url, timeout)
        if tags is None:
            return {
                "status": "error",
                "message": "Ollama 시작 후에도 연결에 실패했습니다. `ollama serve` 상태를 확인하세요.",
                "model_available": False,
            }
        server_status = "started"
    else:
        server_status = "ok"

    # 모델 설치 확인
    model_available = _check_model(tags, model)
    if not model_available:
        return {
            "status": server_status,
            "message": (
                f"모델 '{model}'이(가) 설치되지 않았습니다. "
                f"`ollama pull {model}`을 실행하세요."
            ),
            "model_available": False,
        }

    return {
        "status": server_status,
        "message": f"Ollama 정상 (모델: {model})"
        + (" — 서버를 새로 시작했습니다." if server_status == "started" else ""),
        "model_available": True,
    }


def _fetch_tags(base_url: str, timeout: int) -> list | None:
    """GET /api/tags 로 설치된 모델 목록을 가져옵니다. 실패 시 None 반환."""
    try:
        import httpx

        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{base_url.rstrip('/')}/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
    except Exception:
        return None


def _check_model(tags: list, model: str) -> bool:
    """tags 리스트에서 모델명 존재 여부를 확인합니다."""
    model_base = model.split(":")[0]
    for tag in tags:
        name = tag.get("name", "")
        if name == model or name.startswith(model_base + ":"):
            return True
    return False


def _try_start_ollama() -> bool:
    """ollama serve를 백그라운드로 시작합니다. ollama 바이너리가 없으면 False."""
    try:
        import shutil

        if not shutil.which("ollama"):
            return False
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False
