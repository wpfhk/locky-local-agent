# Locky v3 Phase 2: UX & Reliability — Plan v0.0.1

> Date: 2026-03-26
> Feature: locky-v3-ux-reliability
> Phase: Phase 2 (P1 — Should Have)
> Option: C (Pragmatic Balance)

---

## 1. Scope

Phase 2 builds on the Phase 1 multi-provider LLM + MCP + RepoMap infrastructure to add:

| # | Item | PRD Ref | Est |
|---|------|---------|-----|
| 1 | Session management (SQLite) | 3.4 | 1 week |
| 2 | Streaming output (unified) | 3.5 | 3 days |
| 3 | `locky init` enhancement | 3.6 | 3 days |
| 4 | Error recovery / retry | 3.7 | 1 week |
| 5 | Lead/Worker multi-model | 3.8 | 1 week |
| 6 | Token/cost tracking | 3.9 | 2 days |

## 2. Module Map

```
tools/
├── session/
│   ├── __init__.py        # exports
│   ├── store.py           # SQLite DAL (sessions, messages tables)
│   └── manager.py         # SessionManager (create, resume, export)
├── llm/
│   ├── streaming.py       # UnifiedStreamer (provider-agnostic)
│   ├── retry.py           # RetryHandler (backoff + fallback)
│   └── tracker.py         # TokenTracker + CostCalculator
```

### CLI additions (locky_cli/main.py)

```
locky session list
locky session resume <id>
locky session export <id> [--output FILE]
locky init  (enhanced: provider auto-detect, config validation)
```

## 3. Dependencies

- **New**: None. SQLite is stdlib. All LLM code uses httpx (already present).
- **No new pip packages required.**

## 4. Constraints

- Python only, local-first
- 461 existing tests must pass (no regression)
- Match rate >= 90%
- DO NOT modify: tools/plugins/, tools/recipes/, tools/mcp/server.py, tools/sandbox/, ui/tui.py

## 5. Implementation Order

1. `tools/llm/retry.py` — foundation for reliability
2. `tools/llm/tracker.py` — token/cost tracking (used by streaming)
3. `tools/llm/streaming.py` — unified streaming with tracker integration
4. `tools/session/store.py` — SQLite storage
5. `tools/session/manager.py` — session lifecycle
6. Update `locky_cli/main.py` — session CLI commands + init enhancement
7. Update `tools/llm/registry.py` — lead/worker support
8. Update `locky_cli/config_loader.py` — lead/worker config parsing
9. Tests for all new modules

## 6. Success Criteria

| Metric | Target |
|--------|--------|
| All 461 existing tests pass | Yes |
| New test count | 80+ |
| Session CRUD operations | SQLite-backed |
| Streaming works for all 4 providers | Yes |
| Retry with exponential backoff | 3 attempts default |
| Fallback chain | primary -> fallback provider |
| Lead/Worker config | config.yaml driven |
| Token tracking | prompt + completion tokens per call |
| Cost estimation | Per-provider pricing table |
