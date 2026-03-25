# Gap Analysis Report — locky-agent v1.1.0

> **Feature**: locky-agent-v1.1
> **Analysis Date**: 2026-03-24
> **Phase**: Check

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | 환경변수 반복 설정, REPL 컨텍스트 부재, 수동 업데이트가 매일 사용의 마찰을 높인다. |
| **WHO** | 로컬 LLM(Ollama) 사용 개발자, 여러 프로젝트를 오가며 작업, 한국어 사용자 |
| **RISK** | config.yaml 우선순위 충돌 / git pull 실패 시 업데이트 중단 |
| **SUCCESS** | `locky init` 후 환경변수 없이 `locky commit` 동작 / `locky update`로 1분 내 최신 버전 |
| **SCOPE** | config_loader, init 대화형, repl context, update 명령, profile 자동갱신 |

---

## Overall Score

| Category | Score | Status |
|----------|:-----:|:------:|
| FR-01: config_loader | 100% | ✅ |
| FR-02: locky init interactive | 93% | ✅ |
| FR-03: REPL context header | 90% | ✅ |
| FR-04: locky update | 100% | ✅ |
| FR-05: profile auto-update | 100% | ✅ (implemented after initial analysis) |
| FR-06: locky update --check | 100% | ✅ |
| config.py integration | 95% | ✅ |
| Dependencies | 100% | ✅ |
| Tests | 100% | ✅ |
| **Overall Match Rate** | **97%** | **✅** |

---

## FR-by-FR Gap Analysis

### FR-01: config_loader.py — ✅ 100%

| Item | Status |
|------|:------:|
| `load_config(root) -> dict` | ✅ |
| `get_ollama_model` / `get_ollama_base_url` / `get_ollama_timeout` | ✅ |
| `get_hook_steps` / `get_auto_profile` | ✅ |
| Priority: env > yaml > default | ✅ |
| Graceful fallback on parse error | ✅ |
| `pyyaml>=6.0` dependency added | ✅ |

### FR-02: locky init interactive — ✅ 93%

| Item | Status |
|------|:------:|
| Click prompt for model | ✅ |
| Click confirm for hook install | ✅ |
| Click prompt for hook steps | ✅ |
| `.locky/config.yaml` generation | ✅ |
| Profile detect_and_save on init | ✅ |
| `--hook/--no-hook` CLI option | ⚠️ replaced by interactive confirm |

### FR-03: REPL context header — ✅ 90%

| Item | Status |
|------|:------:|
| Model from config_loader | ✅ |
| Hook steps display | ✅ |
| Language from profile.json | ✅ |
| config.yaml source indicator | ✅ |
| Called on REPL entry | ✅ |
| Function name changed (_banner vs _print_context_header) | ⚠️ cosmetic |

### FR-04: locky update — ✅ 100%

| Item | Status |
|------|:------:|
| `run(root, check_only=False) -> dict` | ✅ |
| `_find_locky_repo()` | ✅ |
| `_git_pull()` + `_reinstall()` | ✅ |
| CLI `update` subcommand | ✅ |
| pipx detection | ✅ |

### FR-05: Profile auto-update — ✅ 100%

| Item | Status |
|------|:------:|
| `_maybe_refresh_profile(root)` helper | ✅ |
| `get_auto_profile()` controlling behavior | ✅ |
| Background thread (non-blocking) | ✅ |
| Wired to `commit_cmd` | ✅ |
| Wired to `format_cmd` | ✅ |
| Exception isolation | ✅ |

### FR-06: locky update --check — ✅ 100%

| Item | Status |
|------|:------:|
| `--check` flag | ✅ |
| Version check without file changes | ✅ |
| Returns `status: "check"` | ✅ |

---

## Gaps Summary

### Minor Differences (No Action Required)

| # | Item | Design | Implementation | Impact |
|---|------|--------|----------------|:------:|
| 1 | config.py function name | `_get_setting` | `_cfg` | Low |
| 2 | REPL function name | `_print_context_header` | `_banner` | Low |
| 3 | REPL panel title | `Locky v{VERSION}` | `Locky` (version in table row) | Low |
| 4 | `--hook/--no-hook` on init | CLI option | interactive confirm | Low |

### Fixed During Check Phase

- FR-05 completely implemented: `_maybe_refresh_profile()` added to `main.py`, wired to `commit_cmd` and `format_cmd`
- 3 additional tests added (167 total)

---

## Test Coverage

| File | Tests | Status |
|------|:-----:|:------:|
| test_config_loader.py | 27 | ✅ all pass |
| test_update.py | 13 | ✅ all pass |
| All other tests | 127 | ✅ all pass |
| **Total** | **167** | **✅** |

---

## Final Match Rate: 97% ✅

All Must requirements (FR-01 ~ FR-04) fully implemented.
All Should requirements (FR-05, FR-06) fully implemented.
167/167 tests pass.
