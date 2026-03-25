# locky-v2-overhaul — Gap Analysis

> **Feature**: locky-v2-overhaul
> **Date**: 2026-03-25
> **Design**: docs/02-design/features/locky-v2-overhaul.design.md
> **Analyzer**: bkit:gap-detector

---

## Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Architecture Compliance | 98% | ✅ |
| Module Match | 97% | ✅ |
| CLI Integration | 95% | ✅ |
| Test Coverage | 129% (67/52) | ✅ |
| **Weighted Match Rate** | **88%** | ⚠️ |

---

## Module-by-Module Match

| Design Section | 구현 파일 | Match |
|----------------|----------|:-----:|
| 3.1 `core/agent.py` | `locky/core/agent.py` | ✅ 100% |
| 3.2 `core/session.py` | `locky/core/session.py` | ✅ 100% |
| 3.3 `core/context.py` | `locky/core/context.py` | ✅ 99% (`sys.executable` 개선) |
| 3.4 `tools/__init__.py` | `locky/tools/__init__.py` | ✅ 100% |
| 3.5 `tools/format.py` | `locky/tools/format.py` | ✅ 100% |
| 3.6 `tools/git.py` | `locky/tools/git.py` | ✅ 99% (미사용 import 제거) |
| 3.7 `tools/file.py` | `locky/tools/file.py` | ✅ 99% (`import re` 모듈 레벨) |
| 3.8 `agents/ask_agent.py` | `locky/agents/ask_agent.py` | ✅ 100% |
| 3.9 `agents/edit_agent.py` | `locky/agents/edit_agent.py` | ✅ 100% |
| 3.10 `runtime/local.py` | `locky/runtime/local.py` | ✅ 100% |
| `tools/test.py` | `locky/tools/test.py` | ✅ 100% |
| `tools/scan.py` | `locky/tools/scan.py` | ✅ 100% |
| `tools/commit.py` | `locky/tools/commit.py` | ✅ 100% |
| 7.2 `locky/__init__.py` | `locky/__init__.py` | ✅ 100% |
| 4.1 `ask_cmd` | `locky_cli/main.py` | ✅ 98% |
| 4.1 `edit_cmd` | `locky_cli/main.py` | ✅ 98% |
| 4.1 `agent_cmd` | `locky_cli/main.py` | ✅ 95% |
| 4.2 REPL `/ask` | `locky_cli/repl.py` | ✅ 90% |
| 4.2 REPL `/edit` | `locky_cli/repl.py` | ✅ 95% |
| Section 6 `stream()` | `tools/ollama_client.py` | ✅ 100% |

---

## Gaps (Missing / Critical)

| # | 항목 | 심각도 | 설명 |
|---|------|:------:|------|
| G1 | `pyproject.toml` packages.find | **High** | `"locky*"` 미포함 → `pip install` 시 v2 패키지 누락 |
| G2 | `pyproject.toml` version | **Medium** | `"1.1.0"` → `"2.0.0"` 미반영 |
| G3 | `locky/agents/commit_agent.py` | **Medium** | 설계 패키지 구조에 명시됐으나 미구현 |
| G4 | `tests/test_tools_format.py` | **Low** | 위임 패턴 검증 테스트 3개 누락 |
| G5 | pytest `--cov=locky` | **Low** | locky/ 커버리지 미측정 |

---

## Bonus (설계 외 추가 구현)

| 항목 | 파일 | 설명 |
|------|------|------|
| `stream_chat()` async | `tools/ollama_client.py` | 기존 비동기 스트리밍 유지 |
| `test_ollama_stream.py` | `tests/` | stream() 전용 4개 테스트 |
| `test_cli_v2_commands.py` | `tests/` | CLI 통합 8개 테스트 |
| REPL 파일 파싱 개선 | `locky_cli/repl.py` | 파일/질문 자동 분리 |
| agent 명령 스피너 | `locky_cli/main.py` | 실행 중 상태 표시 |

---

## 권장 수정 순서

| 우선순위 | 항목 | 파일 |
|:--------:|------|------|
| 1 | packages.find에 `locky*` 추가 | `pyproject.toml` |
| 2 | version `2.0.0` 으로 변경 | `pyproject.toml` |
| 3 | `--cov=locky` 추가 | `pyproject.toml` |
| 4 | `commit_agent.py` 구현 또는 설계 문서에서 제거 | TBD |
| 5 | `test_tools_format.py` 생성 | `tests/` |
