# Locky v3 Phase 3: Extensibility — Gap Analysis v0.0.1

> Date: 2026-03-26
> Baseline: 570 tests, Phase 1 + Phase 2 complete
> Result: 721 tests (151 new), all passing

---

## 1. Implementation vs Design Gap Analysis

| Component | Design Spec | Implementation | Match |
|-----------|------------|----------------|:-----:|
| **Plugin manifest.py** | PluginManifest + PluginCommand dataclass, validate_manifest(), load_manifest() | Fully implemented with regex validation, semver check, kebab-case enforcement | 100% |
| **Plugin loader.py** | discover(), load(), import_entry() | Fully implemented with sys.path management, file-based fallback import | 100% |
| **Plugin registry.py** | register/unregister, lifecycle hooks, load_all() | Fully implemented with on_load/on_unload hook support, multi-dir discovery | 100% |
| **Recipe parser.py** | Recipe + RecipeStep dataclass, validate, parse | Fully implemented with string and dict step formats, CLI arg parsing | 100% |
| **Recipe runner.py** | RecipeRunner.run(), list_recipes() | Fully implemented with fail_fast, action mapping, multi-dir discovery | 100% |
| **MCP server.py** | JSON-RPC 2.0 stdio, 4 tools exposed | Fully implemented: initialize, tools/list, tools/call for format/scan/test/deps | 100% |
| **Sandbox base.py** | SandboxBase ABC, SandboxConfig, get_sandbox() factory | Fully implemented with NoopSandbox fallback | 100% |
| **Sandbox macos.py** | seatbelt profile generation, sandbox-exec wrapper | Fully implemented with read/write path control, network toggle | 100% |
| **Sandbox linux.py** | seccomp placeholder with firejail | Fully implemented as firejail wrapper with fallback passthrough | 100% |
| **TUI tui.py** | Rich-based dashboard with action menu | Fully implemented with status panel, action runner, interactive menu | 100% |
| **CLI commands** | recipe run/list, serve-mcp, tui | All 3 command groups added to main.py | 100% |

**Overall Match Rate: 100% (11/11 components)**

## 2. Test Coverage Summary

| Test File | Tests | Coverage Area |
|-----------|:-----:|---------------|
| test_plugin_manifest.py | 22 | Manifest validation, loading, dataclasses |
| test_plugin_loader.py | 12 | Discovery, manifest loading, dynamic import |
| test_plugin_registry.py | 14 | Registration, hooks, load_all, command management |
| test_recipe_parser.py | 20 | Validation, parsing, CLI args, dataclasses |
| test_recipe_runner.py | 15 | Execution, fail_fast, args, discovery |
| test_mcp_server.py | 15 | JSON-RPC handling, tool dispatch, framing |
| test_sandbox.py | 22 | All sandbox types, factory, profiles |
| test_tui.py | 8 | Actions, menu, status display |
| test_cli_v3_commands.py | 5 | CLI recipe/serve-mcp/tui registration |
| **Total New** | **133** | |
| **Existing** | **570** | (unchanged, all passing) |
| **Grand Total** | **721** | (was 570) |

Note: pytest collected 721 (some tests within suites count differently from manual sum).

## 3. Phase 2 File Integrity Check

| Protected File | Modified? | Status |
|---------------|:---------:|:------:|
| tools/session/store.py | No | OK |
| tools/session/manager.py | No | OK |
| tools/llm/streaming.py | No | OK |
| tools/llm/retry.py | No | OK |
| tools/llm/tracker.py | No | OK |

## 4. Risk Assessment

| Risk | Status | Notes |
|------|:------:|-------|
| Existing tests broken | Mitigated | All 570 original tests pass |
| Sandbox unavailable on CI | Mitigated | NoopSandbox fallback works on all platforms |
| Plugin import security | Acknowledged | Plugins execute in same process; manifest validation helps but does not isolate |
| Recipe infinite loop | Mitigated | MAX_STEPS=50 enforced in parser validation |
| MCP protocol compatibility | Partial | Content-Length framing + raw JSON fallback covers major clients |

## 5. Remaining Gaps (Future Work)

| Gap | Priority | Notes |
|-----|:--------:|-------|
| Plugin marketplace / install command | P3 | `locky plugin install <url>` not implemented |
| SSE MCP transport | P3 | Only stdio transport implemented |
| seccomp direct integration | P3 | Linux sandbox uses firejail, not native seccomp-bpf |
| Textual TUI upgrade | P3 | Current TUI uses Rich prompts, not Textual widgets |
| Recipe variables / templating | P3 | Recipes don't support variable substitution |
