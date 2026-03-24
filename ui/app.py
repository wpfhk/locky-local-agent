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
from tools.ollama_client import OllamaClient


def _resolve_web_mcp_root() -> Path:
    """웹 UI용 MCP 루트 경로를 반환합니다."""
    return Path(os.environ.get("MCP_FILESYSTEM_ROOT", os.getcwd())).resolve()


@cl.on_chat_start
async def on_chat_start() -> None:
    """세션 시작 시 대시보드 정보 표시."""
    root = _resolve_web_mcp_root()
    cl.user_session["mcp_root"] = str(root)

    await cl.Message(
        content=(
            "## Locky 자동화 도구\n\n"
            f"| 항목 | 값 |\n|------|-----|\n"
            f"| 버전 | `0.3.0` |\n"
            f"| 모델 | `{OLLAMA_MODEL}` |\n"
            f"| 루트 | `{root}` |\n\n"
            "사용 가능한 명령:\n"
            "- `/commit [--dry-run] [--push]` — 커밋 메시지 자동 생성 후 커밋\n"
            "- `/format [--check]` — black/isort/flake8 실행\n"
            "- `/test [PATH]` — pytest 실행\n"
            "- `/todo [--output FILE]` — TODO/FIXME 수집\n"
            "- `/scan [--severity LEVEL]` — 보안 패턴 스캔\n"
            "- `/clean [--force]` — 캐시/임시파일 정리\n"
            "- `/deps` — 의존성 버전 확인\n"
            "- `/env [--output FILE]` — .env.example 생성\n\n"
            "일반 메시지를 입력하면 Ollama에 직접 질문합니다."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """메시지 수신 및 명령 분기."""
    content = message.content.strip()
    root = Path(cl.user_session.get("mcp_root", os.getcwd()))

    if content.startswith("/commit"):
        args = content[len("/commit"):].strip().split()
        dry_run = "--dry-run" in args
        push = "--push" in args
        await _run_action("commit", root, dry_run=dry_run, push=push)
        return

    if content.startswith("/format"):
        args = content[len("/format"):].strip().split()
        check_only = "--check" in args
        await _run_action("format", root, check_only=check_only)
        return

    if content.startswith("/test"):
        args = content[len("/test"):].strip().split()
        path_args = [a for a in args if not a.startswith("-")]
        verbose = "-v" in args or "--verbose" in args
        test_path = path_args[0] if path_args else None
        await _run_action("test", root, path=test_path, verbose=verbose)
        return

    if content.startswith("/todo"):
        args = content[len("/todo"):].strip().split()
        output_file = None
        if "--output" in args:
            idx = args.index("--output")
            if idx + 1 < len(args):
                output_file = args[idx + 1]
        await _run_action("todo", root, output_file=output_file)
        return

    if content.startswith("/scan"):
        args = content[len("/scan"):].strip().split()
        severity = None
        if "--severity" in args:
            idx = args.index("--severity")
            if idx + 1 < len(args):
                severity = args[idx + 1]
        await _run_action("scan", root, severity_filter=severity)
        return

    if content.startswith("/clean"):
        args = content[len("/clean"):].strip().split()
        force = "--force" in args
        await _run_action("clean", root, dry_run=not force)
        return

    if content.startswith("/deps"):
        await _run_action("deps", root)
        return

    if content.startswith("/env"):
        args = content[len("/env"):].strip().split()
        output_file = ".env.example"
        if "--output" in args:
            idx = args.index("--output")
            if idx + 1 < len(args):
                output_file = args[idx + 1]
        await _run_action("env", root, output=output_file)
        return

    # 일반 메시지 → Ollama 직접 대화
    await _direct_chat(content)


async def _run_action(action_name: str, root: Path, **kwargs) -> None:
    """actions/ 모듈을 실행하고 결과를 Chainlit으로 표시합니다."""
    action_map = {
        "commit": ("actions.commit", "run"),
        "format": ("actions.format_code", "run"),
        "test": ("actions.test_runner", "run"),
        "todo": ("actions.todo_collector", "run"),
        "scan": ("actions.security_scan", "run"),
        "clean": ("actions.cleanup", "run"),
        "deps": ("actions.deps_check", "run"),
        "env": ("actions.env_template", "run"),
    }

    if action_name not in action_map:
        await cl.Message(content=f"알 수 없는 명령: /{action_name}").send()
        return

    module_path, func_name = action_map[action_name]

    await cl.Message(content=f"**/{action_name}** 실행 중...").send()

    try:
        import importlib
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        def _invoke():
            return func(root, **kwargs)

        async with cl.Step(name=action_name, type="tool") as step:
            step.input = f"root={root}, {kwargs}"
            result = await asyncio.get_event_loop().run_in_executor(None, _invoke)
            step.output = str(result)

        # 결과 포맷팅
        md = _format_result_md(action_name, result)
        await cl.Message(content=md).send()

    except Exception as exc:
        await cl.Message(
            content=f"**오류:** `{action_name}` 실행 실패\n```\n{exc}\n```"
        ).send()


def _format_result_md(action_name: str, result: dict) -> str:
    """결과 dict를 마크다운으로 포맷합니다."""
    status = result.get("status", "unknown")
    icon = "✅" if status in ("ok", "pass", "clean") else ("⚠️" if status == "nothing_to_commit" else "❌")

    lines = [f"## {icon} /{action_name} — `{status}`\n"]

    for key, value in result.items():
        if key == "status":
            continue
        if isinstance(value, list):
            lines.append(f"**{key}** ({len(value)}개):")
            for item in value[:15]:
                if isinstance(item, dict):
                    sev = item.get("severity", "")
                    file_ = item.get("file", item.get("path", ""))
                    line_ = item.get("line", "")
                    desc = item.get("text", item.get("description", ""))
                    if sev:
                        lines.append(f"- `[{sev}]` `{file_}:{line_}` {desc}")
                    else:
                        lines.append(f"- `{file_}:{line_}` {desc}"[:120])
                else:
                    lines.append(f"- {str(item)[:100]}")
            if len(value) > 15:
                lines.append(f"- ... 외 {len(value) - 15}개")
        elif isinstance(value, dict):
            sub = ", ".join(f"`{k}={v}`" for k, v in value.items())
            lines.append(f"**{key}**: {sub}")
        else:
            val_str = str(value)
            if len(val_str) > 500:
                val_str = val_str[:500] + "..."
            lines.append(f"**{key}**: {val_str}")

    return "\n".join(lines)


async def _direct_chat(content: str) -> None:
    """일반 메시지를 Ollama에 직접 전달하여 응답합니다."""
    ollama = OllamaClient()

    if not ollama.health_check():
        await cl.Message(
            content=(
                "❌ **Ollama 서버에 연결할 수 없습니다.**\n"
                "`ollama serve` 명령으로 서버를 시작하세요."
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
