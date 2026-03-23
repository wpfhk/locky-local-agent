"""Locky Chainlit 웹 UI."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (locky-agent 루트에서 실행 가정)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import chainlit as cl

from config import OLLAMA_MODEL
from graph import run_with_root
from locky_cli.fs_context import default_full_access_root
from tools.ollama_client import OllamaClient


def _resolve_web_mcp_root() -> tuple[Path, str | None]:
    """
    웹 UI용 MCP 루트와 (필요 시) 경고 문구.
    full 모드는 기본 차단 — LOCKY_WEB_ALLOW_FULL=1 일 때만 전역 루트 사용.
    그 외에는 workspace(MCP_FILESYSTEM_ROOT 또는 cwd)로 폴백합니다.
    """
    mode = os.environ.get("LOCKY_PERMISSION_MODE", "workspace").lower().strip()
    base = Path(os.environ.get("MCP_FILESYSTEM_ROOT", os.getcwd())).resolve()
    if mode == "full":
        allow = os.environ.get("LOCKY_WEB_ALLOW_FULL", "").lower().strip()
        if allow in ("1", "true", "yes", "on"):
            return default_full_access_root(), None
        warn = (
            "`LOCKY_PERMISSION_MODE=full` 이지만 웹에서는 기본 차단되어 "
            "**현재 워크스페이스**로만 동작합니다. "
            "전역 접근이 필요하면 `LOCKY_WEB_ALLOW_FULL=1` (위험)을 설정하세요."
        )
        return base, warn
    return base, None


@cl.on_chat_start
async def on_chat_start() -> None:
    """세션 시작 시 대시보드 정보 표시."""
    root, warn = _resolve_web_mcp_root()

    cl.user_session["mcp_root"] = str(root)
    cl.user_session["run_history"] = cl.user_session.get("run_history") or []

    warn_block = f"\n\n> ⚠️ {warn}\n" if warn else ""
    mode_label = (
        "full (로컬 전역)"
        if os.environ.get("LOCKY_PERMISSION_MODE", "").lower().strip() == "full"
        and os.environ.get("LOCKY_WEB_ALLOW_FULL", "").lower().strip() in ("1", "true", "yes", "on")
        else "workspace (이 디렉터리 이하)"
    )

    await cl.Message(
        content=(
            "## Locky 대시보드\n\n"
            f"| 항목 | 값 |\n|------|-----|\n"
            f"| 모델 | `{OLLAMA_MODEL}` |\n"
            f"| MCP 루트 | `{root}` |\n"
            f"| 권한 | {mode_label} |\n"
            f"{warn_block}\n"
            "`/develop [요구사항]` 으로 파이프라인을 실행하거나, 일반 메시지로 Ollama에 질문하세요."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """메시지 수신 및 파이프라인 실행."""
    content = message.content.strip()

    if content.startswith("/develop"):
        cmd = content[len("/develop") :].strip()
        if not cmd:
            await cl.Message(
                content="사용법: `/develop [요구사항]`\n예) `/develop FastAPI로 TODO API를 만들어줘`"
            ).send()
            return

        await _run_pipeline(cmd)
        return

    await _direct_chat(content)


async def _run_pipeline(cmd: str) -> None:
    """Locky 개발 파이프라인을 실행하고 결과를 단계별로 표시합니다."""
    root, _warn = _resolve_web_mcp_root()

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

        def _invoke() -> dict:
            return run_with_root(cmd, root)

        async with cl.Step(name="Planner", type="tool") as planner_step:
            planner_step.input = cmd
            result = await asyncio.get_event_loop().run_in_executor(None, _invoke)

            planner_output = result.get("planner_output") or {}
            planner_step.output = (
                f"태스크 수: {len(planner_output.get('task_list', []))}개\n"
                f"요약: {planner_output.get('codebase_summary', '')[:300]}"
            )

        async with cl.Step(name="Coder", type="tool") as coder_step:
            coder_output = result.get("coder_output") or {}
            coder_step.input = f"태스크: {coder_output.get('current_task', {})}"
            coder_step.output = (
                f"수정된 파일: {', '.join(coder_output.get('modified_files', [])) or '없음'}\n"
                f"커밋: {coder_output.get('commit_message_draft', '')}"
            )

        async with cl.Step(name="Tester", type="tool") as tester_step:
            tester_output = result.get("tester_output") or {}
            verdict = tester_output.get("verdict", "unknown")
            tester_step.input = f"검증 중... (iteration {result.get('retry_count', 0)})"
            tester_step.output = (
                f"판정: {verdict.upper()}\n"
                f"테스트 결과: {len(tester_output.get('test_results', []))}개\n"
                f"보안 이슈: {len(tester_output.get('security_issues', []))}개"
            )

        verdict = (result.get("tester_output") or {}).get("verdict", "unknown")
        verdict_icon = "✅" if verdict == "pass" else "❌"
        retry_count = result.get("retry_count", 0)
        final_report = result.get("final_report", "")
        messages = result.get("messages", [])
        feedback = (result.get("tester_output") or {}).get("feedback", "")

        md_lines = [
            f"## {verdict_icon} 파이프라인 완료",
            "",
            "| 항목 | 내용 |",
            "|------|------|",
            f"| 판정 | **{verdict.upper()}** |",
            f"| 반복 횟수 | {retry_count} |",
            f"| 최종 보고 | {final_report} |",
            "",
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

        hist = cl.user_session.get("run_history") or []
        hist.append(
            {
                "cmd": cmd[:200],
                "verdict": verdict,
                "retries": retry_count,
            }
        )
        cl.user_session["run_history"] = hist[-15:]

        if hist:
            recent = "\n".join(
                f"- `{h.get('cmd', '')[:80]}` → {h.get('verdict', '')}"
                for h in cl.user_session["run_history"][-5:]
            )
            await cl.Message(
                content=f"### 세션 최근 실행 (최대 15건)\n{recent}",
            ).send()

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
