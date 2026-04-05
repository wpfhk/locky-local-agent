# Locky

**Natural language to shell command. 100% local, 100% private.**

Locky converts natural language requests into executable shell commands using a local LLM (Gemma via Ollama). No cloud API, no telemetry, no data leaves your machine.

---

## Features

| Feature | Description |
|---------|-------------|
| **REPL** | Interactive session -- type naturally, get shell commands |
| **One-shot** | `locky -c "..."` for scripting and CI pipelines |
| **Autopilot** | `locky -a "..."` decomposes complex tasks into multi-step plans |
| **Read-Think-Write** | Autopilot can read files, compute diffs, and edit with user approval |
| **Session Memory** | Context-aware -- remembers your last 5 actions for smarter suggestions |
| **Self-Correction** | Failed commands get AI-powered fix suggestions automatically |
| **Real-time HUD** | Streaming token output with live speed meter (t/s) |
| **OS-Aware** | Auto-detects Windows PowerShell vs macOS/Linux shell |
| **Safe by Default** | Dangerous commands (`rm -rf /`, `DROP TABLE`) require explicit double confirmation |

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) running locally

```bash
ollama pull gemma3:12b
```

## Install

```bash
git clone https://github.com/dotoricode/locky.git
cd locky
pip install -e .
```

## Usage

### Interactive REPL

```bash
locky
```

```
locky [D:\project]> 현재 디렉토리의 파일 목록을 보여줘
╭─ Command to execute ──────────────────╮
│ ls -la                                │
╰───────────────────────────────────────╯
Execute? [y/N] y
```

### One-shot Mode

```bash
locky -c "find all Python files larger than 100KB"
# -> find . -name "*.py" -size +100k

locky -c "compress the logs folder" --json
# -> {"status": "ok", "command": "tar -czf logs.tar.gz logs/", "message": "..."}
```

Exit code: `0` on success, `1` on failure -- safe for scripting.

### Autopilot Mode

```bash
locky -a "find all .py files, run ruff lint, and save errors to report.txt"
```

Locky plans the task as multiple steps, shows you the plan, and executes each step with your approval:

```
╭─ Autopilot Plan ──────────────────────────────────────╮
│ Step │ Description          │ Command                  │
│  1   │ Find Python files    │ find . -name "*.py"      │
│  2   │ Run linter           │ ruff check .             │
│  3   │ Save error report    │ ruff check . > report.txt│
╰───────────────────────────────────────────────────────╯
Execute this 3-step plan? [y/N]
```

### REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear screen |
| `/reset` | Clear session memory |
| `/autopilot <task>` | Run multi-step autopilot |
| `/exit` | Quit |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `gemma3:12b` | Ollama model tag |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT` | `300` | Request timeout (seconds) |

## Architecture

```
locky_cli/
  main.py              CLI entry (REPL + one-shot + autopilot)
  repl.py              Interactive REPL with streaming HUD
  autopilot.py         Multi-step plan execution engine

actions/
  shell_command.py     Core: natural language -> shell command (Ollama)

tools/
  ollama_client.py     Ollama /api/chat client (sync + streaming)
  ollama_guard.py      Ollama health check + auto-start
  planner.py           Task decomposition into step-by-step plans
  editor.py            Safe file editing with backup + diff preview
  session_manager.py   JSON-based session memory
  indexer.py           AST-based code map generator

config.py              Environment variables (3 total)
```

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v      # 94 tests
ruff check .                    # lint
ruff format .                   # format
```

## License

MIT
