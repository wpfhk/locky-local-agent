<div align="center">

# 🔒 Locky

**100% 로컬 개발자 자동화 도구**

외부 클라우드 없이, 당신의 머신에서만 동작하는 개발 워크플로 자동화 CLI

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=for-the-badge)](CHANGELOG.md)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[시작하기](#-빠른-시작) · [명령어](#-명령어) · [다언어 지원](#-다언어-포맷터)

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
| 🌐 | **다언어 포맷터** | Python/JS/TS/Go/Rust/Kotlin/Swift 지원 |
| 🔗 | **pre-commit 훅** | format→test→scan 자동 파이프라인 |
| 💻 | **REPL + CLI 지원** | 인터랙티브 세션 또는 단발 명령어 모두 지원 |

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
- [Ollama](https://ollama.com/) 설치 및 실행 중 (`locky commit` 명령에 필요)

### 1. Ollama + 모델 준비 (`commit` 명령 사용 시만 필요)

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

## 🧠 지원 모델 (`commit` 명령용)

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
- [ ] VS Code Extension
- [ ] GitHub Actions 통합
- [ ] `.locky/config.yaml` 프로젝트 설정

---

## 📄 라이선스

MIT License

---

<div align="center">

No cloud. No keys. Just automation.

</div>
