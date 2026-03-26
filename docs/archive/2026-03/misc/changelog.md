# locky-agent Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.1] - 2026-03-25 (Postfix)

### Fixed

- **Streaming Policy Change** — `tools/ollama_client.py`
  - Added `stream(prompt, timeout=None)` method for per-chunk timeout
  - Fixes CPU-only Ollama timeout on large token inference (300s per chunk, not total)
  - Used by EditAgent and AskAgent for robust LLM calls

- **Test Mock Synchronization** — `tests/test_agents_edit.py`
  - Updated mock target from `OllamaClient.chat()` to `OllamaClient.stream()`
  - Fixed 6 edit agent tests to return `list[str]` instead of `str`
  - All tests now pass (351/351)

- **Error Handling in EditAgent** — `locky/agents/edit_agent.py`
  - Added try/except for `httpx.ReadTimeout`
  - Graceful error response: `{"status": "error", "message": "...", "code": "timeout"}`
  - Prevents unhandled exceptions in agent loop

- **Pathspec Parsing in Commit** — `actions/commit.py`
  - Replaced `line[3:]` index-based parsing with `git add -u` / `git add .` logic
  - Correctly handles rename, delete, and modify files
  - Fixes IndexError on non-standard git status output

### Test Results

- **351 tests passed** (0 failed)
- Regression test: 0 failures
- Coverage increase: +2% (locky/) to 76%
- Design match rate: 97% → 98%

### Related

- Parent feature: [locky-v2-overhaul](../../../archive/2026-03/locky-v2-overhaul/) (v2.0.0, 97% match)
- Report: [locky-v2-postfix.report.md](./features/locky-v2-postfix.report.md)
- PR: [#3 — locky-v2 postfix](https://github.com/wpfhk/locky-local-agent/pull/3)

---

## [2.0.0] - 2026-03-25

### Added

- **Agent-Based Architecture** — `locky/` package (4-layer design)
  - **Core**: `BaseAgent`, `LockySession`, `ContextCollector` for agent loop infrastructure
  - **Tools**: `BaseTool`, `ToolResult` for action wrapper interface
  - **Agents**: `AskAgent`, `EditAgent`, `CommitAgent` for AI-specialized workflows
  - **Runtime**: `LocalRuntime` for subprocess-based local execution

- **AI Commands** — Extended `locky_cli/main.py`
  - `locky ask [--verbose] "question" [FILE...]` — Code Q&A with context
  - `locky edit [--dry-run|--apply] "instruction" [FILE]` — LLM-powered code editing
  - `locky agent run "complex task"` — Multi-step agent workflow execution

- **REPL Slash Commands** — `locky_cli/repl.py` integration
  - `/ask` — Interactive ask within REPL context
  - `/edit` — Code editing suggestions in REPL
  - Full session context carry-over between commands

- **Streaming Support** — `tools/ollama_client.py`
  - `stream(prompt, timeout=None)` method for streaming token generation
  - Per-chunk timeout support (each chunk waits up to timeout, not total)
  - Generator-based API for memory efficiency

- **Test Suite** — 70 new tests (263 total)
  - `test_agents_core.py` (18 tests)
  - `test_agents_ask.py` (15 tests)
  - `test_agents_edit.py` (6 tests)
  - `test_agents_commit.py` (10 tests)
  - `test_agents_runtime.py` (12 tests)
  - All existing 193 tests maintained (backward compatible)

### Changed

- **Architecture Redesign** — Delegation-First pattern
  - `locky/tools/` wraps existing `actions/` without replacement
  - Zero breaking changes to existing CLI commands
  - AI-optional: all BaseTool work without Ollama

- **Fail-Safe Default** — `--dry-run` is default for new commands
  - `locky edit --dry-run "fix bug"` shows diff preview
  - `locky edit --apply` required for actual file modification
  - Safer UX for LLM-assisted changes

### Fixed

- **High-Level Architecture** — Replaced LangGraph pipeline
  - Removed `agents/` directory (legacy pipeline remnants)
  - Removed `states/state.py` (unused LockyGlobalState)
  - Replaced with simpler dataclass-driven agent loop

### Infrastructure

- **Package Configuration** — `pyproject.toml`
  - Added `packages.find()` to discover `locky*` namespace
  - Version bumped to 2.0.0
  - All 263 tests pass with pytest

- **Design Match Rate**: 97% (5 gaps found in Check, 1 iteration to 100%)
- **Test Coverage**: 74% (locky/) + 68% (overall)

### Related

- Plan: [locky-v2-overhaul.plan.md](../../../archive/2026-03/locky-v2-overhaul/locky-v2-overhaul.plan.md)
- Design: [locky-v2-overhaul.design.md](../../../archive/2026-03/locky-v2-overhaul/locky-v2-overhaul.design.md)
- Analysis: [locky-v2-overhaul.analysis.md](../../../archive/2026-03/locky-v2-overhaul/locky-v2-overhaul.analysis.md)
- Report: [locky-v2-overhaul.report.md](../../../archive/2026-03/locky-v2-overhaul/locky-v2-overhaul.report.md)

---

## [1.0.0] - 2026-03-24

### Added

- **Context Cache** — `.locky/profile.json` for session-persistent project metadata
  - Language detection (primary + all)
  - Commit style tracking (conventional, Korean)
  - Last run history
- **Pre-commit Hook Management** — `locky hook install/uninstall`
  - Safe backup of existing hooks (`.locky-backup`)
  - Automatic restoration on uninstall
  - Configurable execution steps (format, test, scan)
- **Language Auto-Detection** — `locky_cli/lang_detect.py`
  - 20+ file extension mappings
  - `git ls-files` based analysis
  - Fallback to `glob()` for non-git directories
- **Multi-Language Formatter** — Extended `actions/format_code.py`
  - Python: black + isort + ruff
  - JavaScript/TypeScript: prettier + eslint
  - Go: gofmt
  - Rust: rustfmt
  - Ruby, Java, Kotlin support (additional)
- **Pipeline Chaining** — `locky run "format test commit"`
  - Sequential execution of multiple commands
  - `fail_fast` mode (default)
  - `partial` status for partial completion
- **Ollama Health Guard** — `tools/ollama_guard.py`
  - Automatic health checks on Ollama endpoint
  - Auto-start `ollama serve` if down
  - Model availability checking
  - Integrated into `commit.py` and `shell_command.py`
- **Plugin Architecture** — `~/.locky/plugins/`
  - Dynamic plugin discovery via `importlib`
  - Standard `run(root: Path, **opts) -> dict` interface
  - Custom action loading
- **Project Initialization** — `locky init`
  - Interactive setup guide
  - Environment configuration check
  - Installation status verification
- **Test Suite** — 101 tests with 89% coverage
  - `test_hook.py` (21 tests, 100% coverage)
  - `test_context.py` (8 tests, 80% coverage)
  - `test_lang_detect.py` (9 tests, 92% coverage)
  - `test_format_code.py` (16 tests, 90%+ coverage)
  - `test_pipeline.py` (14 tests, 100% coverage)
  - `test_ollama_guard.py` (14 tests, 95%+ coverage)
  - `test_shell_command.py` (17 tests, 89% coverage)
  - `test_commit.py` (2 tests, 90%+ coverage)

### Changed

- **Multi-Language Formatter** — `actions/format_code.py`
  - Extended from Python-only to 6+ languages
  - Dynamic formatter selection based on detected language
  - Graceful skip with warnings for missing formatters
- **CLI Main** — `locky_cli/main.py`
  - Added `hook` subcommand with `--steps` option
  - Added `run` subcommand for pipeline chaining
  - Added `init` subcommand for project setup
  - Added `--lang/-l` option to `format` command
- **Commit Integration** — `actions/commit.py`
  - Integrated Ollama health guard (`ensure_ollama()`)
  - Better error handling for unavailable Ollama
- **Shell Command Integration** — `actions/shell_command.py`
  - Integrated Ollama health guard
  - Context-aware free-text command execution

### Fixed

- **Legacy Module Cleanup** — Complete removal of:
  - `agents/` directory (LangGraph pipeline remnants)
  - `states/state.py` (LockyGlobalState, unused)
  - `graph.py` (migration shim)
  - `pipeline/` directory (external /develop skill dependency)
- **gitignore Update** — Added `.locky/` to prevent caching local state in version control
- **Format Command Options** — Added `--lang/-l` option for explicit language specification

### Infrastructure

- **Testing Foundation** — `pytest` + `pytest-cov`
  - `tests/conftest.py` for shared fixtures
  - `pytest.ini` configuration
  - CI/CD compatibility matrix (Python 3.10+)
- **Code Quality** — Zero critical issues
  - All security considerations addressed (path injection, command injection prevention)
  - Comprehensive error handling with graceful degradation
  - Mock-based testing for external dependencies

---

## [0.3.0] - 2026-02-XX

### Added

- REPL mode with slash commands (`/commit`, `/format`, `/test`, etc.)
- Free-text natural language to shell command conversion via Ollama
- Shell command whitelist for safety
- 8 core automation commands (commit, format, test, scan, etc.)

### Fixed

- Configuration management for Ollama integration
- Import organization and module structure

---

## [0.2.0] and Earlier

See git history for details.

---

## Unreleased (v1.1.0 Roadmap)

### Planned

- [ ] **Config Override** — `.locky/config.yaml` support
  - User-customizable language mapping
  - Custom formatter definitions per language
- [ ] **Dependency Parser Expansion** — FR-10
  - `pyproject.toml` (Python)
  - `package.json` (Node.js)
  - `go.mod` (Go)
  - `Cargo.toml` (Rust)
- [ ] **REPL Context Integration** — Full context.py usage in interactive mode
  - `/commit` now includes project context
  - Better command suggestions based on last run
- [ ] **Sample Plugin** — prettier wrapper example
  - Demonstrates plugin structure
  - Best practices documentation
- [ ] **Integration Tests** — Hook lifecycle testing
  - Actual git repository testing
  - Pre-commit hook execution flow validation

---

## Notes

### Backward Compatibility

- v1.0.0 is fully backward compatible with v0.3.0
- Removal of `agents/`, `states/`, `graph.py`, `pipeline/` does not affect CLI commands
- Legacy code that depended on these modules must be updated (not in core locky-agent)

### Version Progression

**v0.4.0** (within v1.0.0):
- Context cache + hook management + legacy cleanup + testing foundation

**v0.5.0** (within v1.0.0):
- Multi-language detection and formatting + pipeline chaining

**v1.0.0** (Release):
- Plugin architecture + Ollama health guard + project initialization
- **Status**: Production-ready, global installation ready

### Test Coverage Statistics

| Module | Tests | Coverage |
|--------|:-----:|:--------:|
| context.py | 8 | 80% |
| hook.py | 21 | 100% |
| lang_detect.py | 9 | 92% |
| format_code.py | 16 | 90%+ |
| pipeline.py | 14 | 100% |
| ollama_guard.py | 14 | 95%+ |
| shell_command.py | 17 | 89% |
| commit.py | 2 | 90%+ |
| **Total** | **101** | **~89%** |

### Architecture Metrics

- New modules: 6 (context.py, lang_detect.py, hook.py, pipeline.py, ollama_guard.py + tests)
- Total new code: ~1,080 LOC
- Test code: ~600 LOC
- Legacy removed: 4 directories/files
- Dependencies added: 0 (all standard library + existing)
- Design match rate: 93% (71% → 93% after iteration)

---

**Latest Update**: 2026-03-24 (v1.0.0 Release)
