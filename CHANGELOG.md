# Changelog

All notable changes to Locky are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [1.0.0] - 2026-04-04

### Added
- Full codebase lint + format pass (ruff check + ruff format, 0 errors)
- Production-quality `README.md` with feature table, architecture diagram, usage examples

### Changed
- Version bumped to 1.0.0 (stable release)
- `CLAUDE.md` updated with full v1.0.0 structure map and interfaces
- `.omc/docs/roadmap.md` finalized: Phase 0-10 complete

---

## [0.7.0] - 2026-04-04

### Added
- Real-time streaming: REPL command generation streams tokens as they arrive with Live display
- HUD: token count + t/s speed shown during generation (`● Generating... 15 tok  8.2 t/s`)
- `transient=True`: streaming panel disappears cleanly before final command panel
- Graceful interrupt: `Ctrl+C` during streaming cancels generation and returns to prompt
- Autopilot: spinner HUD during plan generation and self-correction analysis
- `on_token` callback param added to `shell_command.run()`, `run_fix()`, `planner.generate_plan()`
- `ollama_client.stream()` now accepts `options` param (same as `chat()`)
- `tests/test_streaming.py` with 5 test cases

### Changed
- `locky_cli/repl.py`: `_handle_free_text()` uses Rich `Live` for streaming display
- `locky_cli/autopilot.py`: plan generation and evaluation use `console.status()` spinner
- `pyproject.toml`, `locky_cli/main.py`, `CLAUDE.md`: version bumped to 0.7.0

---

## [0.6.0] - 2026-04-04

### Added
- File editor (`tools/editor.py`): `read_file_range()`, `replace_in_file()` with auto-backup, `diff_markup()` for Rich display
- Autopilot `edit_file` tool: plan steps can now edit files directly with diff preview and user approval
- Autopilot `read_file` tool: plan steps can read files and pass content to subsequent steps
- Diff visualization: `+`(green) / `-`(red) Rich panel shown before applying any file edit
- Auto-backup: `.bak` file created before every file modification
- State tracking: `.omc/state/agent_state.json` updated at each autopilot step
- `evaluate_progress()`: post-plan LLM evaluation of goal achievement
- `tests/test_editor.py` with 10 test cases

### Changed
- `tools/planner.py`: system prompt updated with `edit_file`/`read_file` tool examples; `parse_plan()` preserves extra fields; `evaluate_progress()` added
- `locky_cli/autopilot.py`: routes `edit_file`/`read_file` steps; writes `.omc/state/`; calls `evaluate_progress()` at completion
- `pyproject.toml`, `locky_cli/main.py`, `CLAUDE.md`: version bumped to 0.6.0

---

## [0.5.0] - 2026-04-04

### Added
- Autopilot mode: `locky -a "complex task"` for multi-step autonomous execution
- Task planner (`tools/planner.py`): Gemma 3 decomposes requests into ≤7 shell command steps
- REPL command `/autopilot <task>` for inline multi-step planning
- Dangerous command detection: `rm -rf /`, `DROP TABLE`, etc. require explicit `yes` confirmation
- Per-step approval: `[y] Execute / [s] Skip / [q] Quit` for each plan step
- Self-correction integration: Phase 5 `run_fix()` invoked automatically on step failure
- Plan persistence: `.omc/plan.md` updated on each autopilot run
- `tests/test_planner.py` with 10 test cases

### Changed
- `locky_cli/main.py`: version bumped to 0.5.0, `--autopilot`/`-a` option added
- `locky_cli/repl.py`: `/autopilot` command added, help text updated
- `.omc/docs/roadmap.md`: Phase 7 marked complete, next items updated
- `.omc/docs/plan.md`: Phase 7 schema documented
- `pyproject.toml`: version bumped to 0.5.0

---

## [0.4.0] - 2026-04-04

### Added
- Session memory: JSON-based action history (`tools/session_manager.py`)
- Context-aware commands: LLM receives last 5 actions for contextual reasoning
- `/reset` REPL command to clear session memory
- Session persistence: `.omc/session.json` survives REPL restarts
- `tests/test_session_manager.py` with 10 test cases
- `history` parameter in `shell_command.run()` for session context injection

### Changed
- `repl.py`: records every execution result to session; passes history to LLM
- `/clear` only clears screen (session memory preserved)

---

## [0.3.0] - 2026-04-04

### Added
- Self-correction loop: `run_fix()` analyzes failed commands and suggests fixes
- REPL: press `f` after execution failure to get AI-powered fix suggestion
- Fix prompt with failure pattern classification (typo, permission, path, dependency, syntax)
- `tests/test_fix_logic.py` with 7 test cases

### Changed
- `repl.py`: execution failure now offers interactive fix suggestion
- `shell_command.py`: added `_FIX_SYSTEM_PROMPT` and `run_fix()` function

---

## [0.2.0] - 2026-04-04

### Added
- AST-based code map generator (`tools/indexer.py`)
- Auto-generated `.omc/repo_map.md` with 5-minute TTL cache
- Code map injected into LLM prompt for richer project context
- `tests/test_indexer.py` with 10 test cases
- `.omc/docs/` layered documentation (architecture, decisions, roadmap, plan)

### Changed
- `shell_command.run()` now includes project code map in prompt context
- `_scan_directory` augmented with `_get_code_map` for deeper project understanding

---

## [0.1.0] - 2026-04-04

### Added
- One-shot mode: `locky -c "natural language"` for non-interactive use
- JSON output: `--json` flag for machine-readable results
- Exit code: 0 (success) / 1 (failure) for scripting
- OS-aware prompt: auto-detects Windows PowerShell vs macOS/Linux
- Numeric-start CLI support: `7z`, `2to3`, `1password` now accepted
- `AGENTS.md` for OMC agent discovery
- `.omc/docs/` layered documentation (architecture, decisions, roadmap)

### Changed
- Default model: `qwen2.5-coder:7b` -> `gemma3:12b`
- `shell_command.run()` now uses `OllamaClient.chat()` instead of raw httpx
- `OllamaClient.chat()` accepts `options` parameter (temperature, num_predict, top_k)
- `num_predict`: 80 -> 150 for complex pipe/redirect commands
- `CLAUDE.md` slimmed to <60 lines (detail moved to `.omc/docs/`)
- `LICENSE` unified to MIT

### Removed
- `.cursorrules`, `.flake8`, `TUTORIAL.md`, `context/`, `scripts/install.sh`
- v1-v3 README content (rewritten for current single-purpose CLI)

---

## [0.0.1] - 2026-04-04

Project restarted from scratch for Gemma 3 integration.
