<div align="center">

# Locky

**100% 로컬 우선 개발자 자동화 플랫폼**

코드 생성 에이전트가 아닌, 개발 워크플로 자동화 플랫폼

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-3.0.0-blue?style=for-the-badge)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[![Tests](https://img.shields.io/badge/Tests-721%20passed-brightgreen?style=for-the-badge)](#-품질-지표)
[![Coverage](https://img.shields.io/badge/Coverage-72%25-green?style=for-the-badge)](#-품질-지표)
[![Providers](https://img.shields.io/badge/LLM%20Providers-75%2B-orange?style=for-the-badge)](#-멀티-프로바이더-llm)

**[English](README.en.md)**

[빠른 시작](#-빠른-시작) · [명령어](#-명령어) · [MCP 지원](#-mcp-지원) · [플러그인](#-플러그인-v2) · [레시피](#-레시피)

</div>

---

> **Locky v3** — Ollama-only에서 75+ LLM 프로바이더, MCP 네이티브 확장, 세션 관리, 샌드박싱까지.
> 로컬 우선 철학은 유지하면서 Goose/Aider 급 확장성을 확보했습니다.

---

## Locky가 다른 점

| | Goose | Aider | Claude Code | **Locky** |
|---|:-:|:-:|:-:|:-:|
| **포지셔닝** | 범용 AI 에이전트 | 코드 생성 페어프로그래머 | 프리미엄 CLI (유료) | **워크플로 자동화 플랫폼** |
| **자동화 명령** | - | - | - | **11개** (format/scan/test/deps/hook...) |
| **다언어 포맷터** | - | - | - | **7개 언어** |
| **보안 스캔** | - | - | - | **OWASP 패턴** |
| **pre-commit 훅** | - | - | - | **format→test→scan** |
| **LLM 프로바이더** | 25+ | 75+ (litellm) | Anthropic only | **75+** (litellm optional) |
| **MCP 지원** | 네이티브 | - | 네이티브 | **stdio 클라이언트 + 서버** |
| **로컬 우선** | 부분 | 부분 | 클라우드 | **100% 로컬 가능** |
| **비용** | 무료 | 무료 | 유료 | **무료** |

---

## v3 주요 변경사항

### Phase 1: Core Infra

- **멀티 프로바이더 LLM** — Ollama, OpenAI, Anthropic 내장 + litellm으로 75+ 프로바이더 확장
- **MCP stdio 클라이언트** — 외부 MCP 서버를 도구로 등록하여 활용
- **Repo Map** — AST 기반 코드베이스 자동 인덱싱, 쿼리 기반 컨텍스트 선택

### Phase 2: UX + Reliability

- **세션 관리** — SQLite 기반 대화 이력 저장/재개/내보내기
- **통합 스트리밍** — 모든 LLM 호출에 프로바이더 무관 스트리밍
- **에러 복구** — Exponential backoff + 모델 fallback + 로컬 자동 전환
- **Lead/Worker** — 복잡도별 모델 자동 분리 (Lead: 추론, Worker: 단순작업)
- **토큰/비용 추적** — 호출별 토큰 수 및 비용 표시
- **init 개선** — 프로바이더 자동 감지, config 검증

### Phase 3: Extensibility

- **플러그인 v2** — 선언적 `plugin.yaml` 매니페스트 시스템
- **레시피** — YAML 기반 재사용 워크플로 템플릿
- **MCP 서버 내보내기** — Locky 기능을 MCP 서버로 노출
- **보안 샌드박싱** — macOS seatbelt / Linux seccomp
- **TUI** — Rich/Textual 기반 터미널 대시보드

---

## 품질 지표

| 지표 | v2.0.1 | **v3.0.0** |
|------|:------:|:----------:|
| 테스트 | 351 | **721** |
| 커버리지 | 67% | **72%** |
| CLI 명령어 | 15 | **20+** |
| LLM 프로바이더 | 1 | **75+** |
| 지원 언어 (포맷터) | 7 | 7 |

---

## 빠른 시작

### 사전 요구사항

- Python 3.10+
- [Ollama](https://ollama.com/) (로컬 LLM 사용 시)

### 설치

```bash
git clone https://github.com/wpfhk/locky-local-agent.git
cd locky-local-agent
pip install -e .

# 또는 전역 설치
pipx install -e .

# litellm 포함 (75+ 프로바이더)
pip install -e ".[litellm]"
```

### 프로젝트 초기화

```bash
cd ~/myproject
locky init
```

`locky init`이 자동으로 감지합니다:
- Ollama 실행 중인지
- OpenAI/Anthropic API 키가 설정되어 있는지
- 프로젝트 언어 및 적합한 MCP 서버 추천

### 설정 (.locky/config.yaml)

```yaml
llm:
  provider: ollama                    # ollama | openai | anthropic | litellm
  model: qwen2.5-coder:7b
  fallback:
    provider: ollama
    model: qwen2.5-coder:3b
  lead:                               # 복잡한 추론용
    provider: anthropic
    model: claude-sonnet-4-6
  worker:                             # 단순 작업용
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

## 명령어

### 자동화 (LLM 불필요)

| 명령어 | 설명 |
|--------|------|
| `locky format [--check] [--lang LANG]` | 7개 언어 자동 감지 포매팅 |
| `locky test [PATH] [-v]` | pytest 실행 및 결과 요약 |
| `locky scan [--severity LEVEL]` | OWASP 패턴 보안 스캔 |
| `locky todo [--output FILE]` | TODO/FIXME/HACK 수집 |
| `locky clean [--force]` | 캐시 및 임시 파일 정리 |
| `locky deps` | 의존성 버전 비교 |
| `locky env [--output FILE]` | .env → .env.example 생성 |

### AI 에이전트 (LLM 필요)

| 명령어 | 설명 |
|--------|------|
| `locky commit [--dry-run] [--push]` | AI 커밋 메시지 생성 |
| `locky ask "질문"` | 코드베이스 자연어 질의 |
| `locky edit FILE "지시" [--apply]` | AI 코드 편집 |
| `locky agent "태스크"` | 멀티스텝 자율 에이전트 |

### 세션 관리 (v3)

| 명령어 | 설명 |
|--------|------|
| `locky session list` | 이전 세션 목록 |
| `locky session resume <id>` | 세션 재개 (컨텍스트 복원) |
| `locky session export <id>` | 마크다운 내보내기 |

### 훅 및 파이프라인

| 명령어 | 설명 |
|--------|------|
| `locky hook install [--steps STEPS]` | pre-commit 훅 설치 |
| `locky hook uninstall` | 훅 제거 (원본 복원) |
| `locky run STEP [STEP...]` | 멀티스텝 파이프라인 |

### 레시피 (v3)

| 명령어 | 설명 |
|--------|------|
| `locky recipe run <name>` | YAML 워크플로 실행 |
| `locky recipe list` | 등록된 레시피 목록 |

### 플러그인 및 확장 (v3)

| 명령어 | 설명 |
|--------|------|
| `locky plugin list` | 설치된 플러그인 목록 |
| `locky serve-mcp` | Locky 기능을 MCP 서버로 실행 |
| `locky tui` | 터미널 대시보드 |

### Jira 통합

| 명령어 | 설명 |
|--------|------|
| `locky jira list` | 이슈 목록 조회 |
| `locky jira create --title "제목"` | 이슈 생성 |
| `locky jira status PROJ-123` | 이슈 상태 업데이트 |

---

## 멀티 프로바이더 LLM

Locky v3는 3개 프로바이더를 내장하고, litellm으로 75+를 지원합니다.

| 프로바이더 | 설치 | 로컬 | API 키 필요 |
|-----------|:----:|:----:|:----------:|
| **Ollama** | 내장 | O | X |
| **OpenAI** | 내장 | X | O |
| **Anthropic** | 내장 | X | O |
| **litellm** | `pip install locky-agent[litellm]` | - | 프로바이더별 |

```bash
# 프로바이더 전환
export LOCKY_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
locky ask "이 함수 설명해줘"

# 또는 config.yaml에서 설정
```

### Lead/Worker 전략

복잡한 작업(ask, edit, agent)은 Lead 모델이, 단순 작업(commit 메시지, 요약)은 Worker 모델이 처리합니다.

```yaml
llm:
  lead:
    provider: anthropic
    model: claude-sonnet-4-6
  worker:
    provider: ollama
    model: qwen2.5-coder:7b
```

### 토큰/비용 추적

```
locky ask "이 함수 뭐 하는 거야?"
[...응답...]
--- 토큰: 1,234 입력 / 567 출력 | 비용: $0.003 ---
```

---

## MCP 지원

### 클라이언트 — 외부 MCP 서버 연결

```yaml
# .locky/config.yaml
mcp_servers:
  - name: github
    command: ["npx", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

등록된 MCP 서버의 도구를 ask/edit/agent에서 자동 활용합니다.

### 서버 — Locky를 MCP 서버로 노출

```bash
locky serve-mcp
```

다른 에이전트(Goose, Claude Code 등)에서 Locky의 format/scan/test/deps 기능을 MCP 도구로 사용할 수 있습니다.

| MCP 도구 | 설명 |
|----------|------|
| `locky_format` | 다언어 코드 포매팅 |
| `locky_scan` | OWASP 보안 스캔 |
| `locky_test` | pytest 실행 |
| `locky_deps` | 의존성 확인 |

---

## 플러그인 v2

### 선언적 매니페스트

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

### 플러그인 관리

```bash
locky plugin list              # 설치된 플러그인 목록
```

---

## 레시피

재사용 가능한 YAML 워크플로 템플릿입니다.

```yaml
# ~/.locky/recipes/pr-ready.yaml
name: PR Ready Check
description: PR 전 전체 검증 파이프라인
steps:
  - format --check
  - test
  - scan --severity high
  - deps
  - commit --dry-run
```

```bash
locky recipe run pr-ready      # 레시피 실행
locky recipe list              # 등록된 레시피 목록
```

---

## Repo Map

AST 기반으로 코드베이스의 함수/클래스/import 관계를 자동 인덱싱합니다.

- Python: `ast` 모듈 (외부 의존성 없음)
- 캐시: `.locky/repo-map.json` (git hash 기반 무효화)
- 증분 업데이트: 변경된 파일만 재인덱싱

ask/edit/agent 호출 시 자동으로 관련 컨텍스트를 선택하여 제공합니다.

---

## 다언어 포맷터

| 언어 | 포매터 |
|------|--------|
| Python | black + isort + flake8 |
| JavaScript | prettier |
| TypeScript | prettier + eslint |
| Go | gofmt |
| Rust | rustfmt |
| Kotlin | ktlint |
| Swift | swiftformat |

```bash
locky format                   # 자동 감지
locky format --lang typescript # 언어 지정
locky format --check           # 검사만
```

---

## 보안

### 샌드박싱

```yaml
# .locky/config.yaml
sandbox:
  enabled: true
  allow_network: false
  allow_paths:
    - /home/user/project
```

| OS | 방식 |
|----|------|
| macOS | seatbelt (`sandbox-exec`) |
| Linux | seccomp + 네임스페이스 |

### 보안 스캔

```bash
locky scan                     # 전체 스캔
locky scan --severity high     # 심각도 필터
```

OWASP Top 10 패턴 기반 정적 분석으로 SQL Injection, XSS, Hardcoded Secrets 등을 탐지합니다.

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Ollama 모델 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_TIMEOUT` | `300` | LLM 타임아웃 (초) |
| `OPENAI_API_KEY` | - | OpenAI API 키 |
| `ANTHROPIC_API_KEY` | - | Anthropic API 키 |
| `LOCKY_LLM_PROVIDER` | `ollama` | 기본 프로바이더 |
| `JIRA_BASE_URL` | - | Jira 서버 주소 |
| `JIRA_API_TOKEN` | - | Jira API 토큰 |

---

## 프로젝트 구조

```
locky-agent/
├── locky_cli/              # Click CLI 패키지 (20+ 서브커맨드)
├── actions/                # 자동화 명령 모듈 (LLM 불필요)
├── tools/
│   ├── llm/                # 멀티 프로바이더 LLM (v3)
│   │   ├── base.py         # ABC 인터페이스
│   │   ├── ollama.py       # Ollama 클라이언트
│   │   ├── openai.py       # OpenAI 클라이언트
│   │   ├── anthropic.py    # Anthropic 클라이언트
│   │   ├── registry.py     # 프로바이더 팩토리 + Lead/Worker
│   │   ├── retry.py        # Exponential backoff + fallback
│   │   ├── streaming.py    # 통합 스트리밍
│   │   └── tracker.py      # 토큰/비용 추적
│   ├── mcp/                # MCP 클라이언트 + 서버 (v3)
│   ├── session/            # SQLite 세션 관리 (v3)
│   ├── plugins/            # 플러그인 v2 시스템 (v3)
│   ├── recipes/            # 워크플로 템플릿 (v3)
│   ├── sandbox/            # OS 수준 샌드박싱 (v3)
│   └── repo_map.py         # 코드베이스 인덱싱 (v3)
├── ui/tui.py               # 터미널 대시보드 (v3)
├── tests/                  # 721개 테스트
└── docs/                   # PDCA 문서
```

---

## 로드맵

- [x] 11개 자동화 명령어
- [x] 7개 언어 포맷터
- [x] AI 에이전트 (ask/edit/agent)
- [x] OWASP 보안 스캔
- [x] pre-commit 훅 파이프라인
- [x] Jira 통합
- [x] 멀티 프로바이더 LLM (75+)
- [x] MCP stdio 클라이언트 + 서버
- [x] Repo Map (AST 기반)
- [x] SQLite 세션 관리
- [x] Lead/Worker 멀티모델
- [x] 토큰/비용 추적
- [x] 플러그인 v2 (선언적 매니페스트)
- [x] 레시피 (YAML 워크플로)
- [x] 보안 샌드박싱
- [x] TUI 대시보드
- [ ] MCP SSE/Streamable HTTP 지원
- [ ] 플러그인 마켓플레이스
- [ ] VS Code Extension
- [ ] GitHub Actions 통합

---

## 라이선스

MIT License

---

<div align="center">

**No cloud. No keys. Just automation.**

Model-agnostic. Local-first. Extensible.

</div>
