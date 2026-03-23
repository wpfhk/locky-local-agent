<div align="center">

# 🔒 Locky

**100% 로컬 개발자 자동화 도구**

외부 클라우드 없이, 당신의 머신에서만 동작하는 개발 워크플로 자동화 CLI

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Chainlit](https://img.shields.io/badge/Chainlit-Web%20UI-FF6B35?style=for-the-badge)](https://chainlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[시작하기](#-빠른-시작) · [튜토리얼](TUTORIAL.md) · [명령어](#-명령어)

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
| 💻 | **REPL + CLI 지원** | 인터랙티브 세션 또는 단발 명령어 모두 지원 |

---

## 🛠 명령어

| 명령어 | 설명 |
|---|---|
| `locky commit` | AI가 git diff를 읽어 Conventional Commits 메시지 생성 후 커밋 |
| `locky format` | black + isort + flake8 자동 실행 |
| `locky test` | pytest 실행 및 결과 요약 |
| `locky todo` | 프로젝트 전체 TODO/FIXME/HACK 수집 |
| `locky scan` | OWASP 패턴 기반 보안 취약점 스캔 |
| `locky clean` | `__pycache__`, `.pyc`, `.pytest_cache` 등 정리 |
| `locky deps` | requirements.txt vs 설치된 패키지 버전 비교 |
| `locky env` | .env → .env.example 자동 생성 |

REPL 모드에서는 `/commit`, `/format`, `/test` 등 슬래시 명령으로 동일하게 사용합니다.

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

전역 설치 (`locky` 명령을 어디서든 사용) → [전역 설치 가이드](TUTORIAL.md#4-전역-설치--locky-명령-어디서든-사용)

### 3. 실행

```bash
# 인터랙티브 REPL (권장)
cd ~/myproject
locky

# 단발 명령어
locky commit          # AI 커밋 메시지 생성 및 커밋
locky format          # 코드 포매팅
locky scan            # 보안 스캔
locky todo            # TODO 수집

# Web UI
locky dashboard
```

실행 화면 (REPL):

```
╭──────────────── Locky ────────────────╮
│  버전        0.3.0                    │
│  모델        qwen2.5-coder:7b         │
│  워크스페이스 /Users/you/myproject     │
╰─ 개발자 귀찮은 작업 자동화 · /help ──╯

locky [/Users/you/myproject]> /scan
╭─ scan — issues_found ─╮
│ issues (3개):          │
│   [high] app.py:42 …  │
╰───────────────────────╯

locky [/Users/you/myproject]> /commit
╭─ commit — ok ────────────────────────╮
│ message: feat(auth): add jwt token…  │
│ committed: true                       │
╰───────────────────────────────────────╯
```

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
- [x] Chainlit Web UI
- [x] AI 커밋 메시지 (Conventional Commits)
- [ ] VS Code Extension
- [ ] GitHub Actions 통합
- [ ] 프로젝트 장기 메모리

---

## 📄 라이선스

MIT License

---

<div align="center">

No cloud. No keys. Just automation.

</div>
