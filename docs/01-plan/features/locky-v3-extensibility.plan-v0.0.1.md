# Locky v3 Phase 3: Extensibility — Plan v0.0.1

> Date: 2026-03-26
> Feature: locky-v3-extensibility
> Baseline: Phase 1 (core-infra) + Phase 2 (ux-reliability) complete, 570 tests passing
> Architecture: Option C (Pragmatic Balance)

---

## 1. Scope

| # | Component | Description | New Files |
|---|-----------|-------------|-----------|
| 1 | Plugin System v2 | Declarative plugin.yaml manifest, discovery, lifecycle hooks | `tools/plugins/{__init__,manifest,loader,registry}.py` |
| 2 | Recipes | YAML workflow templates, `locky recipe run/list` | `tools/recipes/{__init__,parser,runner}.py` |
| 3 | MCP Server Export | Expose format/scan/test/deps as MCP stdio server | `tools/mcp/server.py` |
| 4 | Security Sandboxing | OS-aware macOS seatbelt / Linux seccomp | `tools/sandbox/{__init__,base,macos,linux}.py` |
| 5 | Web UI (TUI) | Textual/Rich TUI as secondary to CLI | `ui/tui.py` |

## 2. Constraints

- Python only, local-first, CLI-first
- 570 existing tests must remain passing
- DO NOT modify Phase 2 files: `tools/session/`, `tools/llm/streaming.py`, `tools/llm/retry.py`, `tools/llm/tracker.py`
- Match rate >= 90%
- All new modules follow `run(root, **opts) -> dict` pattern where applicable

## 3. Dependencies

| Component | Depends On | External Deps |
|-----------|-----------|---------------|
| Plugin System v2 | config_loader, CLI main | PyYAML (already present) |
| Recipes | actions/pipeline, config_loader | PyYAML |
| MCP Server Export | actions/* | None (stdlib json) |
| Security Sandboxing | None | None (OS-level) |
| TUI | actions/*, Rich | `textual` (optional) |

## 4. Milestones

| Step | Deliverable | Tests |
|------|-------------|-------|
| 1 | `tools/plugins/` — manifest + loader + registry | ~30 tests |
| 2 | `tools/recipes/` — parser + runner | ~20 tests |
| 3 | `tools/mcp/server.py` — MCP stdio export | ~15 tests |
| 4 | `tools/sandbox/` — base + macos + linux | ~20 tests |
| 5 | `ui/tui.py` — TUI skeleton | ~10 tests |
| 6 | CLI integration — `recipe`, `serve-mcp` commands | ~10 tests |

## 5. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| seatbelt/seccomp unavailable on CI | Sandbox runs in dry-run mode when not on supported OS |
| textual not installed | TUI gracefully degrades to `rich.console` output |
| Plugin loading security | Plugins run in same process but with validation; no arbitrary exec |
| Recipe infinite loop | Max step count (50) enforced |
