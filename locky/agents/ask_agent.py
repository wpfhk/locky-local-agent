from __future__ import annotations
from locky.core.context import ContextCollector
from locky.core.session import LockySession


class AskAgent:
    """코드 Q&A 에이전트 — 파일 컨텍스트 기반 질의응답."""

    def __init__(self, session: LockySession) -> None:
        self.session = session

    def run(self, question: str, files: list[str] | None = None) -> str:
        """질문에 답변. 파일 지정 시 해당 파일 컨텍스트 포함."""
        root = self.session.workspace
        collector = ContextCollector(root)
        ctx = collector.collect(files=files or [])

        from tools.ollama_guard import ensure_ollama
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        if not ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL):
            return "Ollama 서버를 시작할 수 없습니다. `ollama serve` 실행 후 재시도하세요."

        from tools.ollama_client import OllamaClient
        client = OllamaClient()

        system = (
            "당신은 친절한 코드 어시스턴트입니다. "
            "주어진 코드 컨텍스트를 바탕으로 질문에 답변하세요. "
            "코드 변경이나 편집은 하지 않습니다."
        )
        prompt = f"{ctx.to_prompt_context()}\n\n질문: {question}"

        answer = client.chat([{"role": "user", "content": prompt}], system=system)

        self.session.add_history({"type": "ask", "question": question[:100],
                                  "files": files or []})
        return answer

    def stream(self, question: str, files: list[str] | None = None):
        """스트리밍 답변 제너레이터."""
        root = self.session.workspace
        collector = ContextCollector(root)
        ctx = collector.collect(files=files or [])

        from tools.ollama_guard import ensure_ollama
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        if not ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL):
            yield "Ollama 서버를 시작할 수 없습니다."
            return

        from tools.ollama_client import OllamaClient
        client = OllamaClient()
        system = "당신은 친절한 코드 어시스턴트입니다. 코드 변경 없이 질문에 답변하세요."
        prompt = f"{ctx.to_prompt_context()}\n\n질문: {question}"

        yield from client.stream([{"role": "user", "content": prompt}], system=system)
