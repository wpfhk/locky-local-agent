# Locky

**Natural language to shell command. 100% local, 100% private.**

Locky converts natural language requests into executable shell commands using a local LLM (Gemma 3 via Ollama). No cloud API, no telemetry -- all data stays on your machine.

```
locky [my-project]> find files larger than 100KB
╭─ Command ─────────────────────────────────╮
│ find . -type f -size +100k               │
╰───────────────────────────────────────────╯
● Generating...  12 tok  38.4 t/s
Execute? [y/N]
```

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
| **Streaming HUD** | Real-time token output with live speed meter (t/s) |
| **OS-Aware** | Auto-detects Windows PowerShell vs macOS/Linux shell |
| **Safe by Default** | Dangerous commands (`rm -rf /`, `DROP TABLE`) require double confirmation |

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
locky                    # start in current directory
locky -w /path/to/dir    # specify workspace
```

```
locky [my-project]> show recent git log
╭─ Command ─────────────────────────────────╮
│ git log --oneline -5                      │
╰───────────────────────────────────────────╯
● Generating...  8 tok  42.1 t/s
Execute? [y/N] y

╭─ Result -- ok (exit 0) ──────────────────╮
│ a1b2c3d fix: handle null response        │
│ d4e5f6g feat: add streaming support      │
│ ...                                      │
╰──────────────────────────────────────────╯
```

### One-shot Mode

For scripting and pipelines. Returns exit code `0` (success) / `1` (failure).

```bash
# Print command only
locky -c "show current branch name"
# -> git branch --show-current

# JSON output (for programmatic use)
locky -c "compress the logs folder" --json
# -> {"status": "ok", "command": "tar -czf logs.tar.gz logs/", "message": "..."}

# Use in a pipeline
locky -c "show disk usage" | bash
```

### Autopilot Mode

Decomposes complex tasks into multi-step plans and executes each step with user approval.

```bash
locky -a "lint all .py files and save errors to report.txt"
```

```
╭─ Autopilot Plan ─────────────────────────────────────────╮
│ Step │ Action           │ Command                         │
│  1   │ Run linter       │ ruff check .                    │
│  2   │ Save report      │ ruff check . > report.txt 2>&1  │
╰──────────────────────────────────────────────────────────╯
Execute this 2-step plan? [y/N]
```

Autopilot also supports `read_file` and `edit_file` special tools.
File edits auto-create backups and show diffs before applying.

### Self-Correction

When a command fails, Locky analyzes the error and suggests a fix:

```
locky [my-project]> check python version
╭─ Command ─────────────────────╮
│ python --version              │
╰───────────────────────────────╯
Execute? [y/N] y

╭─ Result -- error (exit 1) ───────────────────────╮
│ 'python' is not recognized as an internal or     │
│ external command                                 │
╰──────────────────────────────────────────────────╯
Press f for fix suggestion, or Enter to skip
[f/Enter] f

╭─ Suggested fix ──────────────╮
│ python3 --version            │
╰──────────────────────────────╯
Execute fix? [y/N] y

╭─ Fix result -- ok (exit 0) ──╮
│ Python 3.12.4                │
╰──────────────────────────────╯
```

### REPL Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear screen |
| `/reset` | Clear session memory |
| `/autopilot <task>` | Run multi-step autopilot |
| `/exit` | Quit (or type `exit`, `quit`) |

### CLI Options

```
locky [OPTIONS]

Options:
  -w, --workspace PATH    Workspace root (default: current directory)
  -c, --command TEXT      One-shot mode: convert and exit
  --json                  JSON output (use with -c)
  -a, --autopilot TEXT    Autopilot mode: multi-step execution
  -h, --help              Show help
  --version               Show version
```

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
  repl.py              Interactive REPL (streaming HUD + self-fix)
  autopilot.py         Autopilot engine (Read-Think-Write)

actions/
  shell_command.py     Core: natural language -> shell command (+ self-fix)

tools/
  ollama_client.py     Ollama /api/chat client (sync + streaming)
  ollama_guard.py      Ollama health check + auto-start
  planner.py           Multi-step task plan generator
  editor.py            Safe file editing (backup + diff preview)
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
