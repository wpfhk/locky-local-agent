"""Locky Chainlit 웹 UI."""

from __future__ import annotations

import sys
import os

# 프로젝트 루트를 sys.path에 추가 (locky-agent 루트에서 실행 가정)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import chainlit as cl

from graph import run
from tools.ollama_client import OllamaClient


@cl.on_chat_start
async def on_chat_start() -> None:
    """세션 시작 시 초기화."""
    await cl.Message(
        content=(
            "🔒 **Locky** — 로컬 AI 개발 에이전트가 준비되었습니다.\n"
            "`/develop [요구사항]` 으로 시작하세요."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """메시지 수신 및 파이프라인 실행."""
    content = message.content.strip()

    # /develop 명령 처리
    if content.startswith("/develop"):
        cmd = content[len("/develop"):].strip()
        if not cmd:
            await cl.Message(
                content="사용법: `/develop [요구사항]`\n예) `/develop FastAPI로 TODO API를 만들어줘`"
            ).send()
            return

        await _run_pipeline(cmd)
        return

    # 일반 메시지 → Ollama에 직접 질문
    await _direct_chat(content)


async def _run_pipeline(cmd: str) -> None:
    """Locky 개발 파이프라인을 실행하고 결과를 단계별로 표시합니다."""
    ollama = OllamaClient()
    if not ollama.health_check():
        await cl.Message(
            content=(
                "❌ **Ollama 서버에 연결할 수 없습니다.**\n"
                "Ollama가 실행 중인지 확인하세요:\n"
                "```bash\nollama serve\n```"
            )
        ).send()
        return

    await cl.Message(content=f"**요구사항:** {cmd}\n\n파이프라인을 시작합니다...").send()

    try:
        # Planning 단계 Step
        async with cl.Step(name="Planner", type="tool") as planner_step:
            planner_step.input = cmd
            # 실제 그래프 실행 (동기 → 스레드 풀에서 실행)
            import asyncio

            result = await asyncio.get_event_loop().run_in_executor(None, run, cmd)

            planner_output = result.get("planner_output") or {}
            planner_step.output = (
                f"태스크 수: {len(planner_output.get('task_list', []))}개\n"
                f"요약: {planner_output.get('codebase_summary', '')[:300]}"
            )

        # Coding 단계 Step
        async with cl.Step(name="Coder", type="tool") as coder_step:
            coder_output = result.get("coder_output") or {}
            coder_step.input = f"태스크: {coder_output.get('current_task', {})}"
            coder_step.output = (
                f"수정된 파일: {', '.join(coder_output.get('modified_files', [])) or '없음'}\n"
                f"커밋: {coder_output.get('commit_message_draft', '')}"
            )

        # Testing 단계 Step
        async with cl.Step(name="Tester", type="tool") as tester_step:
            tester_output = result.get("tester_output") or {}
            verdict = tester_output.get("verdict", "unknown")
            tester_step.input = f"검증 중... (iteration {result.get('retry_count', 0)})"
            tester_step.output = (
                f"판정: {verdict.upper()}\n"
                f"테스트 결과: {len(tester_output.get('test_results', []))}개\n"
                f"보안 이슈: {len(tester_output.get('security_issues', []))}개"
            )

        # 최종 결과 렌더링
        verdict = (result.get("tester_output") or {}).get("verdict", "unknown")
        verdict_icon = "✅" if verdict == "pass" else "❌"
        retry_count = result.get("retry_count", 0)
        final_report = result.get("final_report", "")
        messages = result.get("messages", [])
        feedback = (result.get("tester_output") or {}).get("feedback", "")

        md_lines = [
            f"## {verdict_icon} 파이프라인 완료",
            f"",
            f"| 항목 | 내용 |",
            f"|------|------|",
            f"| 판정 | **{verdict.upper()}** |",
            f"| 반복 횟수 | {retry_count} |",
            f"| 최종 보고 | {final_report} |",
            f"",
        ]

        if messages:
            md_lines.append("### 실행 로그")
            for msg in messages:
                md_lines.append(f"- {msg}")
            md_lines.append("")

        if feedback:
            md_lines.append("### 피드백")
            md_lines.append(feedback)

        await cl.Message(content="\n".join(md_lines)).send()

    except Exception as exc:
        await cl.Message(
            content=(
                f"❌ **파이프라인 실행 중 오류가 발생했습니다.**\n\n"
                f"```\n{exc}\n```\n\n"
                "Ollama 서버 상태와 모델 설정을 확인해주세요."
            )
        ).send()


async def _direct_chat(content: str) -> None:
    """일반 메시지를 Ollama에 직접 전달하여 응답합니다."""
    ollama = OllamaClient()

    if not ollama.health_check():
        await cl.Message(
            content=(
                "❌ **Ollama 서버에 연결할 수 없습니다.**\n"
                "`/develop` 명령 또는 Ollama 서버 실행 후 다시 시도해주세요."
            )
        ).send()
        return

    try:
        response_msg = cl.Message(content="")
        await response_msg.send()

        # 스트리밍 응답
        full_response = ""
        async for token in ollama.stream_chat(
            messages=[{"role": "user", "content": content}]
        ):
            full_response += token
            await response_msg.stream_token(token)

        await response_msg.update()

    except Exception as exc:
        await cl.Message(
            content=f"❌ **응답 생성 중 오류가 발생했습니다:**\n```\n{exc}\n```"
        ).send()
