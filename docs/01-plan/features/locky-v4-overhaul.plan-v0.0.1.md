# locky-v4-overhaul Plan v0.0.1

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | v3는 LLM/MCP/session/sandbox/plugins/recipes 등 과도한 레이어가 추가되어 핵심 기능조차 불안정 (shell_command가 Python 코드를 셸 명령으로 출력) |
| **Solution** | 완전 리라이트 — shell_command(자연어→셸 명령 변환+실행) 하나만 남기고 나머지 전부 제거, 프롬프트 엔지니어링 및 검증 로직 강화 |
| **Functional UX Effect** | `locky` REPL에서 자연어를 입력하면 반드시 올바른 셸 명령이 생성되고 안전하게 실행됨 |
| **Core Value** | "하나를 제대로" — 자연어 → 셸 명령 변환에 집중, 신뢰할 수 있는 로컬 CLI 도구 |

## Context Anchor

| 항목 | 내용 |
|------|------|
| **WHY** | v3 복잡도 폭증으로 핵심 기능이 깨짐. 단순함이 신뢰성을 만든다. |
| **WHO** | 터미널에서 자연어로 셸 명령을 빠르게 실행하고 싶은 개발자 |
| **RISK** | Ollama 모델 품질 의존성 — 나쁜 모델은 여전히 잘못된 명령 생성 가능 |
| **SUCCESS** | 자연어 입력 시 유효한 셸 명령 생성률 ≥ 95%, Python/의사코드 출력 0건 |
| **SCOPE** | REPL + shell_command action 만 유지, 나머지 전부 제거 |

---

## 1. 요구사항

### 1.1 유지할 것 (Scope IN)

| 기능 | 설명 |
|------|------|
| **REPL (`locky` 진입점)** | 자연어 입력 → shell_command 호출 → 확인 → 실행 |
| **shell_command action** | 자연어 → 올바른 셸 명령 변환 (프롬프트 강화) |
| **Ollama 연동** | 로컬 Ollama 전용 (멀티 LLM 제거) |
| **ollama_guard** | Ollama 헬스체크 + 자동 시작 |

### 1.2 제거할 것 (Scope OUT)

| 제거 대상 | 이유 |
|-----------|------|
| `locky commit/format/scan/test/hook/pipeline/todo/clean/deps/env/run/init` | v4 범위 외 |
| `locky ask/edit/agent` | AI 에이전트 명령 — 제거 |
| `locky jira` | 외부 서비스 연동 — 제거 |
| `locky session/recipe/serve-mcp/tui/web/dashboard/update` | v3 신규 — 제거 |
| `tools/llm/` (멀티 LLM 레지스트리) | Ollama 직접 호출로 대체 |
| `tools/mcp/` | 제거 |
| `tools/plugins/` | 제거 |
| `tools/recipes/` | 제거 |
| `tools/session/` | 제거 |
| `tools/sandbox/` | 제거 |
| `tools/repo_map.py` | 제거 |
| `tools/jira_client.py` | 제거 |
| `locky/agents/`, `locky/core/`, `locky/runtime/` | 제거 |
| `actions/` (commit, format, hook, pipeline, test, todo, scan, cleanup, deps, env, update) | 제거 |
| `locky_cli/config_loader.py` (복잡한 설정 체계) | 환경변수 + 단순 config로 대체 |
| `locky_cli/context.py`, `locky_cli/lang_detect.py`, `locky_cli/fs_context.py`, `locky_cli/permissions.py` | 불필요 |
| `ui/app.py` (Chainlit) | 제거 |
| `pipeline/`, `agents/`, `states/`, `graph.py` | 레거시 전부 제거 |

---

## 2. 핵심 버그 분석: shell_command가 Python 코드를 반환하는 문제

### 증상
```
Request: 파이썬 덧셈 프로그램을 /temp 디렉토리 생성해줘 구현해줘
Output: import os   ← Python 코드
Error: /bin/sh: import: command not found
```

### 원인
1. **프롬프트 부족**: "Output ONLY a single executable shell command" 지시를 Ollama(qwen2.5-coder)가 무시하고 Python 코드 생성
2. **_is_valid_command 검증 미흡**: `import os`는 알파벳으로 시작하고 한글이 없으므로 통과됨
3. **요청 자체가 "프로그램 구현"** — 코드 작성 요청을 셸 명령으로 변환하려 한 것 자체가 모호

### 해결 방향
1. **프롬프트 강화**: Few-shot 예시 추가, 코드 작성 요청 거부 지시
2. **검증 강화**: 위험 키워드(`import`, `class `, `def `, `function `) 포함 시 invalid 처리
3. **요청 분류**: 코드 작성/구현 요청은 shell_command 범위 외로 거부
4. **temperature=0 + 짧은 max_tokens**: 모델이 긴 코드를 생성하지 못하도록 제한

---

## 3. 목표 아키텍처 (v4)

```
locky-agent/
├── locky_cli/
│   ├── main.py          # CLI 진입점 (REPL만)
│   └── repl.py          # REPL 루프
├── actions/
│   └── shell_command.py # 자연어 → 셸 명령 (핵심)
├── tools/
│   ├── ollama_client.py # Ollama HTTP 클라이언트
│   └── ollama_guard.py  # Ollama 헬스체크
├── config.py            # 환경변수 기반 단순 설정
├── tests/
│   └── test_shell_command.py  # 핵심 테스트
├── requirements.txt
└── pyproject.toml
```

---

## 4. 구현 우선순위

| 순서 | 작업 | 중요도 |
|------|------|--------|
| 1 | 불필요한 파일/디렉터리 전부 삭제 | Critical |
| 2 | shell_command.py 프롬프트 강화 + 검증 로직 개선 | Critical |
| 3 | repl.py 단순화 (슬래시 명령 전부 제거, 자연어만 처리) | Critical |
| 4 | main.py 단순화 (REPL 진입점만 유지) | Critical |
| 5 | config.py 단순화 (Ollama 설정만) | High |
| 6 | requirements.txt 정리 | High |
| 7 | 테스트 정리 (shell_command 테스트만 유지) | High |
| 8 | CLAUDE.md 업데이트 | Medium |

---

## 5. 성공 기준

| 지표 | 목표 |
|------|------|
| 자연어 → 유효 셸 명령 변환 성공률 | ≥ 95% |
| Python/의사코드 출력 건수 | 0건 |
| "프로그램 구현" 요청 시 적절한 거부 메시지 | 100% |
| 전체 코드량 | v3 대비 80% 감소 |
| 테스트 통과율 | 100% |
