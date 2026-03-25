<div align="center">

# 🔒 Locky

**100% 로컬 개발자 자동화 도구**

외부 클라우드 없이, 당신의 머신에서만 동작하는 개발 워크플로 자동화 CLI

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Version](https://img.shields.io/badge/Version-2.0.1-blue?style=for-the-badge)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[![Tests](https://img.shields.io/badge/Tests-351%20passed-brightgreen?style=for-the-badge)](docs/evaluation/locky-quantitative-evaluation.md)
[![Coverage](https://img.shields.io/badge/Coverage-67%25-yellow?style=for-the-badge)](docs/evaluation/locky-quantitative-evaluation.md)
[![Match Rate](https://img.shields.io/badge/Design%20Match-98%25-brightgreen?style=for-the-badge)](docs/evaluation/locky-quantitative-evaluation.md)

[시작하기](#-빠른-시작) · [명령어](#-명령어) · [AI 에이전트](#-ai-에이전트-v2) · [Jira 통합](#-jira-통합) · [다언어 지원](#-다언어-포맷터)

</div>

---

> 커밋 메시지 작성, 코드 포매팅, 보안 스캔, 의존성 확인 — 반복적이고 귀찮은 개발 작업을 한 줄로.
> **인터넷 연결 없이. API 키 없이. 비용 없이.**

---

## ✨ 특징

| | 차별점 | 설명 |
|---|---|---|
| 🔒 | **완전한 데이터 주권** | 코드가 외부로 나가지 않음 |
| ⚡ | **빠른 자동화** | 포매팅·스캔·정리 명령은 LLM 없이 즉시 실행 |
| 🤖 | **AI 커밋 메시지** | Ollama 기반 Conventional Commits 자동 생성 |
| 🧠 | **AI 에이전트 (v2)** | `locky ask/edit/agent` — 코드 질의·편집·멀티스텝 에이전트 |
| 🌐 | **다언어 포맷터** | Python/JS/TS/Go/Rust/Kotlin/Swift 지원 |
| 🔗 | **pre-commit 훅** | format→test→scan 자동 파이프라인 |
| 📋 | **Jira 통합** | 이슈 조회·생성·상태 업데이트 (로컬 처리) |
| 💻 | **REPL + CLI 지원** | 인터랙티브 세션 또는 단발 명령어 모두 지원 |

---

## 📊 정량적 품질 지표 (v2.0.1)

| 지표 | 값 | 기준 |
|------|------|------|
| **테스트 통과율** | 351/351 (100%) | ≥ 95% ✅ |
| **코드 커버리지** | 67% | ≥ 60% ✅ |
| **설계 일치율** | 98% | ≥ 90% ✅ |
| **lint 오류** | 0개 (flake8) | 0 ✅ |
| **소스 코드 규모** | 5,732 lines | - |
| **테스트 코드 규모** | 3,884 lines | - |
| **CLI 명령어** | 15개 | - |
| **지원 언어** | 7개 | - |

> 전체 평가 보고서: [`docs/evaluation/locky-quantitative-evaluation.md`](docs/evaluation/locky-quantitative-evaluation.md)

---

## 🛠 명령어

### 기본 자동화 명령어

| 명령어 | 설명 |
|---|---|
| `locky commit [--dry-run] [--push]` | AI가 git diff를 읽어 Conventional Commits 메시지 생성 후 커밋 |
| `locky format [--check] [--lang LANG] [PATH...]` | 자동 언어 감지 후 포매터 실행 |
| `locky test [PATH] [-v]` | pytest 실행 및 결과 요약 |
| `locky todo [--output FILE]` | 프로젝트 전체 TODO/FIXME/HACK 수집 |
| `locky scan [--severity LEVEL]` | OWASP 패턴 기반 보안 취약점 스캔 |
| `locky clean [--force]` | `__pycache__`, `.pyc`, `.pytest_cache` 등 정리 |
| `locky deps` | requirements.txt/pyproject.toml/package.json/go.mod vs 설치 버전 비교 |
| `locky env [--output FILE]` | .env → .env.example 자동 생성 |

### 훅 및 파이프라인 명령어

| 명령어 | 설명 |
|---|---|
| `locky hook install [--steps STEPS]` | git pre-commit 훅 설치 (format→test→scan) |
| `locky hook uninstall` | 훅 제거 및 이전 훅 복원 |
| `locky hook status` | 훅 설치 여부 확인 |
| `locky run STEP [STEP...]` | 여러 명령을 순서대로 실행 (파이프라인) |
| `locky init [--hook/--no-hook]` | 프로젝트 초기화 및 설정 가이드 |

### 플러그인 명령어

| 명령어 | 설명 |
|---|---|
| `locky plugin list` | `~/.locky/plugins/` 에 설치된 플러그인 목록 |

REPL 모드에서는 `/commit`, `/format`, `/test` 등 슬래시 명령으로 동일하게 사용합니다.

---

## 🧠 AI 에이전트 (v2)

v2에서 추가된 Ollama 기반 AI 에이전트 명령어입니다. CPU 추론 환경에서도 안정적으로 동작합니다.

| 명령어 | 설명 |
|---|---|
| `locky ask "질문"` | 코드베이스에 대한 자연어 질의응답 |
| `locky edit FILE "지시사항" [--apply]` | unified diff 생성 및 자동 적용 |
| `locky agent "태스크"` | 멀티스텝 자율 에이전트 실행 |

```bash
# 코드 질의
locky ask "이 프로젝트에서 인증은 어떻게 처리하나요?"

# 파일 편집 (미리보기)
locky edit src/auth.py "JWT 토큰 만료 시간을 1시간으로 변경해줘"

# 파일 편집 (자동 적용)
locky edit src/auth.py "JWT 토큰 만료 시간을 1시간으로 변경해줘" --apply

# 멀티스텝 에이전트
locky agent "테스트 실패하는 함수를 찾아서 수정해줘"
```

> **CPU 추론 최적화**: `locky edit`는 streaming 방식으로 응답을 처리하여 CPU-only 환경에서도 타임아웃 없이 동작합니다.

---

## 📋 Jira 통합

로컬에서 Jira와 연동하여 이슈를 관리합니다.

```bash
# 이슈 목록 조회
locky jira list

# 이슈 생성
locky jira create --title "버그: 로그인 오류" --type Bug

# 이슈 상태 업데이트
locky jira status PROJ-123 --transition "In Progress"
```

Jira 설정은 프로젝트 루트의 `.env` 파일에 추가합니다:

```bash
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_USERNAME=your@email.com
JIRA_API_TOKEN=your_api_token
JIRA_PROJECT_KEY=PROJ
```

---

## 🌐 다언어 포맷터

`locky format`은 언어를 자동 감지하여 적합한 포매터를 실행합니다.

| 언어 | 포매터 |
|---|---|
| Python | black + isort + flake8 |
| JavaScript | prettier |
| TypeScript | prettier + eslint |
| Go | gofmt |
| Rust | rustfmt |
| Kotlin | ktlint |
| Swift | swiftformat |

```bash
# 자동 감지 (기본)
locky format

# 언어 지정
locky format --lang go
locky format --lang typescript

# 검사만 (파일 수정 없음)
locky format --check
```

---

## 🔗 pre-commit 훅

`locky hook install`로 git commit 전 자동으로 format → test → scan을 실행합니다.

```bash
# 훅 설치
locky hook install

# 커스텀 스텝 지정
locky hook install --steps format,test

# 훅 제거 (기존 훅 자동 복원)
locky hook uninstall
```

---

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.10+
- [Ollama](https://ollama.com/) 설치 및 실행 중 (`locky commit`, `locky ask/edit/agent` 명령에 필요)

### 1. Ollama + 모델 준비 (`commit`, `ask`, `edit`, `agent` 명령 사용 시만 필요)

```bash
# macOS
brew install ollama
ollama serve          # 백그라운드 실행 (별도 터미널)

# 모델 다운로드 (최초 1회)
ollama pull qwen2.5-coder:7b
```

### 2. Locky 설치

```bash
git clone https://github.com/your-username/locky-agent.git
cd locky-agent
pip install -e .
```

전역 설치 (`locky` 명령을 어디서든 사용):

```bash
pipx install -e .
```

### 3. 프로젝트 초기화

```bash
cd ~/myproject
locky init
```

### 4. 실행

```bash
# 인터랙티브 REPL (권장)
locky

# 단발 명령어
locky commit          # AI 커밋 메시지 생성 및 커밋
locky format          # 코드 포매팅 (언어 자동 감지)
locky scan            # 보안 스캔
locky todo            # TODO 수집

# AI 에이전트
locky ask "이 함수가 하는 일이 뭐야?"
locky edit main.py "에러 처리 추가해줘"

# 파이프라인 실행
locky run format test scan
```

---

## 📦 의존성 확인 (다중 포맷)

`locky deps`는 프로젝트의 의존성 파일을 자동 감지하여 설치된 버전과 비교합니다.

지원 형식 (우선순위 순):
1. `requirements.txt`
2. `pyproject.toml` (PEP 621 및 Poetry)
3. `package.json` (dependencies + devDependencies)
4. `go.mod`

---

## 🧠 지원 모델 (`commit`, `ask`, `edit`, `agent` 명령용)

| 모델 | 크기 | 특징 |
|---|---|---|
| `qwen2.5-coder:7b` | 4.7 GB | ⭐ 기본값 |
| `qwen2.5-coder:14b` | 9.0 GB | 고품질 |
| `codellama:7b` | 3.8 GB | 경량 |
| `deepseek-coder:6.7b` | 3.8 GB | 빠른 응답 |

```bash
# 모델 변경
export OLLAMA_MODEL=qwen2.5-coder:14b
locky commit
```

---

## ⚙️ 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | 사용할 Ollama 모델 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_TIMEOUT` | `300` | LLM 호출 타임아웃 (초) |
| `MCP_FILESYSTEM_ROOT` | 현재 디렉터리 | 작업 루트 경로 |
| `JIRA_BASE_URL` | - | Jira 서버 주소 |
| `JIRA_USERNAME` | - | Jira 사용자 이메일 |
| `JIRA_API_TOKEN` | - | Jira API 토큰 |
| `JIRA_PROJECT_KEY` | - | 기본 Jira 프로젝트 키 |

프로젝트 루트의 `.env` 파일에 저장하거나 셸에서 `export`로 설정합니다.

---

## 🗺 로드맵

- [x] 8개 자동화 명령어 (commit / format / test / todo / scan / clean / deps / env)
- [x] 인터랙티브 REPL (`locky`)
- [x] AI 커밋 메시지 (Conventional Commits)
- [x] 다언어 포맷터 (Python/JS/TS/Go/Rust/Kotlin/Swift)
- [x] pre-commit 훅 (format→test→scan)
- [x] 멀티스텝 파이프라인 (`locky run`)
- [x] Ollama 헬스체크 + 자동 시작
- [x] 플러그인 아키텍처 (`~/.locky/plugins/`)
- [x] 의존성 다중 포맷 파서 (requirements.txt/pyproject.toml/package.json/go.mod)
- [x] AI 에이전트 v2 (`locky ask` / `locky edit` / `locky agent`)
- [x] Jira 통합 (`locky jira list/create/status`)
- [x] CPU 추론 최적화 (streaming timeout=None)
- [x] 351개 테스트, 100% 통과율
- [ ] VS Code Extension
- [ ] GitHub Actions 통합
- [ ] `locky jira` CLI 서브커맨드 공식 통합

---

## 📄 라이선스

MIT License

---

<div align="center">

No cloud. No keys. Just automation.

</div>
