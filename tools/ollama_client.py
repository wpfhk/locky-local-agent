from typing import AsyncGenerator

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


class OllamaClient:
    """Ollama API 클라이언트"""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(
        self, messages: list, system: str = "", options: dict | None = None
    ) -> str:
        """
        동기 채팅 요청.

        Args:
            messages: [{"role": "user"|"assistant", "content": "..."}] 형식의 메시지 목록
            system: 시스템 프롬프트 (선택)
            options: Ollama 옵션 (temperature, num_predict, top_k 등)

        Returns:
            모델 응답 문자열
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def stream_chat(
        self, messages: list, system: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        비동기 스트리밍 채팅 요청.

        Args:
            messages: [{"role": "user"|"assistant", "content": "..."}] 형식의 메시지 목록
            system: 시스템 프롬프트 (선택)

        Yields:
            스트리밍 응답 토큰 문자열
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    import json

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done", False):
                        break

    def stream(
        self,
        messages: list,
        system: str = "",
        options: dict | None = None,
        timeout: int | None = None,
    ):
        """스트리밍 채팅. 토큰별 동기 제너레이터.

        Args:
            options: Ollama 옵션 (temperature, num_predict, top_k 등)
            timeout: 청크 간 타임아웃(초). None이면 무제한 대기 (CPU 추론 시 권장).
                     기본값은 self.timeout 사용.
        """
        import json

        payload = {"model": self.model, "messages": messages, "stream": True}
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        effective_timeout = timeout if timeout is not None else self.timeout
        with httpx.Client(timeout=effective_timeout) as client:
            with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        if token := data.get("message", {}).get("content", ""):
                            yield token
                        if data.get("done"):
                            break

    def health_check(self) -> bool:
        """
        Ollama 서버 상태 확인.

        Returns:
            서버가 정상이면 True, 그렇지 않으면 False
        """
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return True
        except Exception:
            return False
