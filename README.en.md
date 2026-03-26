<div align="center">

# Locky

**100% Local-First Developer Automation Platform**

Not a code generation agent — a developer workflow automation platform.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-3.0.0-blue?style=for-the-badge)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[![Tests](https://img.shields.io/badge/Tests-721%20passed-brightgreen?style=for-the-badge)](#-quality-metrics)
[![Coverage](https://img.shields.io/badge/Coverage-72%25-green?style=for-the-badge)](#-quality-metrics)
[![Providers](https://img.shields.io/badge/LLM%20Providers-75%2B-orange?style=for-the-badge)](#-multi-provider-llm)

**[한국어](README.md)**

[Quick Start](#-quick-start) · [Commands](#-commands) · [MCP Support](#-mcp-support) · [Plugins](#-plugins-v2) · [Recipes](#-recipes)

</div>

---

> **Locky v3** — From Ollama-only to 75+ LLM providers, native MCP extensions, session management, and sandboxing.
> Keeping the local-first philosophy while achieving Goose/Aider-level extensibility.

---

## What Makes Locky Different

| | Goose | Aider | Claude Code | **Locky** |
|---|:-:|:-:|:-:|:-:|
| **Positioning** | General AI agent | Code gen pair programmer | Premium CLI (paid) | **Workflow automation platform** |
| **Automation commands** | - | - | - | **11** (format/scan/test/deps/hook...) |
| **Multi-lang formatter** | - | - | - | **7 languages** |
| **Security scan** | - | - | - | **OWASP patterns** |
| **Pre-commit hooks** | - | - | - | **format→test→scan** |
| **LLM providers** | 25+ | 75+ (litellm) | Anthropic only | **75+** (litellm optional) |
| **MCP support** | Native | - | Native | **stdio client + server** |
| **Local-first** | Partial | Partial | Cloud | **100% local capable** |
| **Cost** | Free | Free | Paid | **Free** |

---

## What's New in v3

### Phase 1: Core Infrastructure

- **Multi-Provider LLM** — Built-in Ollama, OpenAI, Anthropic + litellm for 75+ providers
- **MCP stdio Client** — Register external MCP servers as tools
- **Repo Map** — AST-based codebase indexing with query-based context selection

### Phase 2: UX + Reliability

- **Session Management** — SQLite-backed conversation history with save/resume/export
- **Unified Streaming** — Provider-agnostic streaming across all LLM calls
- **Error Recovery** — Exponential backoff + model fallback + auto-switch to local
- **Lead/Worker** — Automatic model routing by task complexity
- **Token/Cost Tracking** — Per-call token count and cost display
- **Enhanced Init** — Auto-detect providers, config validation

### Phase 3: Extensibility

- **Plugin v2** — Declarative `plugin.yaml` manifest system
- **Recipes** — YAML-based reusable workflow templates
- **MCP Server Export** — Expose Locky capabilities as MCP server
- **Security Sandboxing** — macOS seatbelt / Linux seccomp
- **TUI** — Rich/Textual terminal dashboard

---

## Quality Metrics

| Metric | v2.0.1 | **v3.0.0** |
|--------|:------:|:----------:|
| Tests | 351 | **721** |
| Coverage | 67% | **72%** |
| CLI Commands | 15 | **20+** |
| LLM Providers | 1 | **75+** |
| Formatter Languages | 7 | 7 |

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) (for local LLM usage)

### Installation

```bash
git clone https://github.com/wpfhk/locky-local-agent.git
cd locky-local-agent
pip install -e .

# Or global install
pipx install -e .

# With litellm (75+ providers)
pip install -e ".[litellm]"
```

### Project Setup

```bash
cd ~/myproject
locky init
```

`locky init` automatically detects:
- Whether Ollama is running
- Available OpenAI/Anthropic API keys
- Project language and recommended MCP servers

### Configuration (.locky/config.yaml)

```yaml
llm:
  provider: ollama                    # ollama | openai | anthropic | litellm
  model: qwen2.5-coder:7b
  fallback:
    provider: ollama
    model: qwen2.5-coder:3b
  lead:                               # Complex reasoning
    provider: anthropic
    model: claude-sonnet-4-6
  worker:                             # Simple tasks
    provider: ollama
    model: qwen2.5-coder:7b

mcp_servers:
  - name: filesystem
    command: ["npx", "@modelcontextprotocol/server-filesystem", "/path"]
  - name: github
    command: ["npx", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

---

## Commands

### Automation (No LLM Required)

| Command | Description |
|---------|-------------|
| `locky format [--check] [--lang LANG]` | Auto-detect and format (7 languages) |
| `locky test [PATH] [-v]` | Run pytest with summary |
| `locky scan [--severity LEVEL]` | OWASP security scan |
| `locky todo [--output FILE]` | Collect TODO/FIXME/HACK |
| `locky clean [--force]` | Clean caches and temp files |
| `locky deps` | Compare dependency versions |
| `locky env [--output FILE]` | Generate .env.example from .env |

### AI Agents (LLM Required)

| Command | Description |
|---------|-------------|
| `locky commit [--dry-run] [--push]` | AI commit message generation |
| `locky ask "question"` | Natural language codebase query |
| `locky edit FILE "instruction" [--apply]` | AI code editing |
| `locky agent "task"` | Multi-step autonomous agent |

### Session Management (v3)

| Command | Description |
|---------|-------------|
| `locky session list` | List previous sessions |
| `locky session resume <id>` | Resume session with context |
| `locky session export <id>` | Export as markdown |

### Hooks & Pipelines

| Command | Description |
|---------|-------------|
| `locky hook install [--steps STEPS]` | Install pre-commit hooks |
| `locky hook uninstall` | Remove hooks (restore originals) |
| `locky run STEP [STEP...]` | Multi-step pipeline |

### Recipes (v3)

| Command | Description |
|---------|-------------|
| `locky recipe run <name>` | Execute YAML workflow |
| `locky recipe list` | List available recipes |

### Plugins & Extensions (v3)

| Command | Description |
|---------|-------------|
| `locky plugin list` | List installed plugins |
| `locky serve-mcp` | Run Locky as MCP server |
| `locky tui` | Terminal dashboard |

### Jira Integration

| Command | Description |
|---------|-------------|
| `locky jira list` | List issues |
| `locky jira create --title "title"` | Create issue |
| `locky jira status PROJ-123` | Update issue status |

---

## Multi-Provider LLM

Locky v3 ships with 3 built-in providers and supports 75+ via litellm.

| Provider | Install | Local | API Key |
|----------|:-------:|:-----:|:-------:|
| **Ollama** | Built-in | Yes | No |
| **OpenAI** | Built-in | No | Yes |
| **Anthropic** | Built-in | No | Yes |
| **litellm** | `pip install locky-agent[litellm]` | - | Per-provider |

```bash
# Switch providers
export LOCKY_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
locky ask "Explain this function"
```

### Lead/Worker Strategy

Complex tasks (ask, edit, agent) use the Lead model; simple tasks (commit messages, summaries) use the Worker model.

```yaml
llm:
  lead:
    provider: anthropic
    model: claude-sonnet-4-6
  worker:
    provider: ollama
    model: qwen2.5-coder:7b
```

### Token/Cost Tracking

```
locky ask "What does this function do?"
[...response...]
--- Tokens: 1,234 in / 567 out | Cost: $0.003 ---
```

---

## MCP Support

### Client — Connect External MCP Servers

```yaml
# .locky/config.yaml
mcp_servers:
  - name: github
    command: ["npx", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

Registered MCP server tools are automatically available in ask/edit/agent.

### Server — Expose Locky as MCP Server

```bash
locky serve-mcp
```

Other agents (Goose, Claude Code, etc.) can use Locky's capabilities as MCP tools.

| MCP Tool | Description |
|----------|-------------|
| `locky_format` | Multi-language code formatting |
| `locky_scan` | OWASP security scan |
| `locky_test` | pytest execution |
| `locky_deps` | Dependency check |

---

## Plugins v2

### Declarative Manifest

```yaml
# ~/.locky/plugins/my-plugin/plugin.yaml
name: my-custom-linter
version: 1.0.0
description: "Custom linting rules"
commands:
  - name: lint
    description: "Run custom linter"
    entry: my_plugin.lint:run
hooks:
  post_format: my_plugin.hooks:after_format
```

### Plugin Management

```bash
locky plugin list              # List installed plugins
```

---

## Recipes

Reusable YAML workflow templates.

```yaml
# ~/.locky/recipes/pr-ready.yaml
name: PR Ready Check
description: Full verification pipeline before PR
steps:
  - format --check
  - test
  - scan --severity high
  - deps
  - commit --dry-run
```

```bash
locky recipe run pr-ready      # Execute recipe
locky recipe list              # List available recipes
```

---

## Repo Map

AST-based automatic indexing of functions, classes, and import graphs.

- Python: `ast` module (no external dependencies)
- Cache: `.locky/repo-map.json` (invalidated by git hash)
- Incremental: Only re-indexes changed files

Automatically provides relevant context to ask/edit/agent calls.

---

## Multi-Language Formatter

| Language | Formatter |
|----------|-----------|
| Python | black + isort + flake8 |
| JavaScript | prettier |
| TypeScript | prettier + eslint |
| Go | gofmt |
| Rust | rustfmt |
| Kotlin | ktlint |
| Swift | swiftformat |

```bash
locky format                   # Auto-detect
locky format --lang typescript # Specify language
locky format --check           # Check only
```

---

## Security

### Sandboxing

```yaml
# .locky/config.yaml
sandbox:
  enabled: true
  allow_network: false
  allow_paths:
    - /home/user/project
```

| OS | Method |
|----|--------|
| macOS | seatbelt (`sandbox-exec`) |
| Linux | seccomp + namespaces |

### Security Scanning

```bash
locky scan                     # Full scan
locky scan --severity high     # Filter by severity
```

Static analysis based on OWASP Top 10 patterns, detecting SQL Injection, XSS, Hardcoded Secrets, and more.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Ollama model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_TIMEOUT` | `300` | LLM timeout (seconds) |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `LOCKY_LLM_PROVIDER` | `ollama` | Default provider |
| `JIRA_BASE_URL` | - | Jira server URL |
| `JIRA_API_TOKEN` | - | Jira API token |

---

## Project Structure

```
locky-agent/
├── locky_cli/              # Click CLI package (20+ subcommands)
├── actions/                # Automation modules (no LLM needed)
├── tools/
│   ├── llm/                # Multi-provider LLM (v3)
│   │   ├── base.py         # ABC interface
│   │   ├── ollama.py       # Ollama client
│   │   ├── openai.py       # OpenAI client
│   │   ├── anthropic.py    # Anthropic client
│   │   ├── registry.py     # Provider factory + Lead/Worker
│   │   ├── retry.py        # Exponential backoff + fallback
│   │   ├── streaming.py    # Unified streaming
│   │   └── tracker.py      # Token/cost tracking
│   ├── mcp/                # MCP client + server (v3)
│   ├── session/            # SQLite session management (v3)
│   ├── plugins/            # Plugin v2 system (v3)
│   ├── recipes/            # Workflow templates (v3)
│   ├── sandbox/            # OS-level sandboxing (v3)
│   └── repo_map.py         # Codebase indexing (v3)
├── ui/tui.py               # Terminal dashboard (v3)
├── tests/                  # 721 tests
└── docs/                   # PDCA documents
```

---

## Roadmap

- [x] 11 automation commands
- [x] 7-language formatter
- [x] AI agents (ask/edit/agent)
- [x] OWASP security scan
- [x] Pre-commit hook pipeline
- [x] Jira integration
- [x] Multi-provider LLM (75+)
- [x] MCP stdio client + server
- [x] Repo Map (AST-based)
- [x] SQLite session management
- [x] Lead/Worker multi-model
- [x] Token/cost tracking
- [x] Plugin v2 (declarative manifest)
- [x] Recipes (YAML workflows)
- [x] Security sandboxing
- [x] TUI dashboard
- [ ] MCP SSE/Streamable HTTP support
- [ ] Plugin marketplace
- [ ] VS Code Extension
- [ ] GitHub Actions integration

---

## License

MIT License

---

<div align="center">

**No cloud. No keys. Just automation.**

Model-agnostic. Local-first. Extensible.

</div>
