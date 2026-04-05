# AGENTS.md -- Locky Agent Guide

## Project

Natural language to shell command CLI. 100% local, powered by Ollama.

## Structure

```
locky_cli/main.py        -- CLI entry (Click). REPL + one-shot mode
locky_cli/repl.py        -- Interactive REPL loop
actions/shell_command.py  -- Core: natural language -> shell command via Ollama
tools/ollama_client.py    -- Ollama /api/chat client (sync/async/stream)
tools/ollama_guard.py     -- Ollama health check + auto-start
tools/indexer.py          -- AST-based code map generator
config.py                 -- Env-based config (3 vars)
tests/test_shell_command.py -- 42 tests
tests/test_indexer.py     -- 10 tests
```

## Commands

```bash
# REPL mode
locky

# One-shot mode (for agents / scripts)
locky -c "list files in current directory"
locky -c "show git log" --json

# Generate code map
python tools/indexer.py

# Test
python -m pytest tests/ -v

# Lint
ruff check .
```

## One-shot mode

`locky -c "text"` converts and prints the command, then exits.
- Exit 0 = success, Exit 1 = failure.
- Add `--json` for machine-readable output: `{"status": "ok", "command": "ls -la", "message": "..."}`

## Key interfaces

- `actions.shell_command.run(root: Path, request: str) -> dict`
  Returns `{"status": "ok"|"error", "command": str, "message": str}`
- `tools.ollama_client.OllamaClient.chat(messages, system, options) -> str`

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `gemma3:12b` | Ollama model tag |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT` | `300` | LLM call timeout (seconds) |
