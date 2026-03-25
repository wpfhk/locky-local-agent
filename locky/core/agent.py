from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from locky.core.session import LockySession
    from locky.tools import BaseTool

MAX_ITERATIONS = 5
AGENT_TIMEOUT = 60  # seconds


@dataclass
class ActionPlan:
    """Ollama가 생성한 실행 계획."""
    task: str
    steps: list[str]
    tool_calls: list[dict]   # [{"tool": "edit", "file": "...", "instruction": "..."}]
    reasoning: str


@dataclass
class AgentResult:
    """에이전트 실행 결과."""
    status: str              # "ok" | "error" | "partial" | "dry_run"
    output: str
    actions_taken: list[str] = field(default_factory=list)
    iterations: int = 0
    verified: bool = False


class BaseAgent:
    """locky v2 에이전트 기반 클래스.

    plan → execute → verify 루프로 태스크를 수행합니다.
    Ollama 없는 환경에서는 올바른 에러 메시지를 반환합니다.
    """

    def __init__(
        self,
        session: LockySession,
        tools: list[BaseTool],
        max_iterations: int = MAX_ITERATIONS,
    ) -> None:
        self.session = session
        self.tools = {t.name: t for t in tools}
        self.max_iterations = max_iterations

    def run(self, task: str) -> AgentResult:
        """태스크를 실행합니다. 최대 max_iterations 반복."""
        for i in range(1, self.max_iterations + 1):
            plan = self._plan(task)
            if plan is None:
                return AgentResult(status="error", output="계획 생성 실패 (Ollama 연결 확인)", iterations=i)

            result = self._execute(plan)
            verified = self._verify(result, plan)

            result.iterations = i
            result.verified = verified

            self.session.add_history({"type": "agent_run", "task": task,
                                      "result": result.status, "iter": i})
            if verified or result.status in ("ok", "dry_run"):
                return result

        return AgentResult(status="partial", output=f"최대 반복({self.max_iterations}회) 도달",
                           iterations=self.max_iterations)

    def _plan(self, task: str) -> ActionPlan | None:
        """Ollama로 실행 계획 생성. 실패 시 None 반환."""
        from tools.ollama_guard import ensure_ollama
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL

        if not ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL):
            return None

        from tools.ollama_client import OllamaClient
        client = OllamaClient()

        context_summary = self.session.context_summary()
        system = (
            "당신은 개발자 워크플로 자동화 에이전트입니다. "
            "주어진 태스크를 수행하기 위한 구체적인 단계를 JSON으로 반환하세요.\n"
            f"현재 컨텍스트: {context_summary}"
        )
        prompt = (
            f"태스크: {task}\n\n"
            "다음 JSON 형식으로 응답하세요:\n"
            '{"steps": ["step1", ...], "tool_calls": [{"tool": "edit|format|test", '
            '"file": "...", "instruction": "..."}], "reasoning": "..."}'
        )

        try:
            response = client.chat([{"role": "user", "content": prompt}], system=system)
            import json
            data = json.loads(response)
            return ActionPlan(task=task, **data)
        except Exception:
            return ActionPlan(task=task, steps=[task], tool_calls=[], reasoning="fallback")

    def _execute(self, plan: ActionPlan) -> AgentResult:
        """계획된 tool_calls를 순서대로 실행."""
        actions = []
        for call in plan.tool_calls:
            tool_name = call.get("tool", "")
            tool = self.tools.get(tool_name)
            if not tool:
                continue

            result = tool.run(self.session.workspace, **{k: v for k, v in call.items() if k != "tool"})
            actions.append(f"{tool_name}: {result.status}")

            if result.status == "error":
                return AgentResult(status="error", output=result.message, actions_taken=actions)

        return AgentResult(status="ok", output="\n".join(actions), actions_taken=actions)

    def _verify(self, result: AgentResult, plan: ActionPlan) -> bool:
        """결과 검증. 기본 구현은 status 확인."""
        return result.status in ("ok", "dry_run")
