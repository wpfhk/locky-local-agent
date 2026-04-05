# AGENTS.md -- Locky Agent Guide

## Project

Natural language to shell command CLI. 100% local, powered by Ollama + Gemma 3.

## Structure

```
locky_cli/main.py         -- CLI entry (Click). REPL + one-shot + autopilot
locky_cli/repl.py         -- Interactive REPL (streaming HUD + self-fix)
locky_cli/autopilot.py    -- Autopilot engine (Read-Think-Write)
actions/shell_command.py   -- Core: natural language -> shell command (+ self-fix)
tools/ollama_client.py     -- Ollama /api/chat client (sync + streaming)
tools/ollama_guard.py      -- Ollama health check + auto-start
tools/planner.py           -- Multi-step task plan generator
tools/editor.py            -- Safe file editing (backup + diff preview)
tools/session_manager.py   -- JSON-based session memory
tools/indexer.py           -- AST-based code map generator
config.py                  -- Env-based config (3 vars)
tests/                     -- 94 tests (pytest)
```

## Commands

```bash
# REPL mode
locky

# One-shot mode (for agents / scripts)
locky -c "list files in current directory"
locky -c "show git log" --json

# Autopilot mode (multi-step)
locky -a "lint all .py files and save errors to report.txt"

# Test
python -m pytest tests/ -v

# Lint
ruff check .
```

## Key interfaces

- `actions.shell_command.run(root, request, history="", on_token=None) -> dict`
  Returns `{"status": "ok"|"error", "command": str, "message": str}`
- `actions.shell_command.run_fix(root, request, failed_command, error_msg, on_token=None) -> dict`
  Analyzes failed command and returns corrected version.
- `tools.planner.generate_plan(workspace, request, on_token=None) -> list[dict]`
  Decomposes complex requests into ≤7 shell command steps.
- `tools.ollama_client.OllamaClient.chat(messages, system, options) -> str`
- `tools.ollama_client.OllamaClient.stream(messages, system, options, timeout) -> Generator[str]`

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `gemma3:12b` | Ollama model tag |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT` | `300` | LLM call timeout (seconds) |
