<div align="center">

# 🔒 Locky

**100% 로컬 AI 개발 에이전트**

외부 클라우드 없이, 당신의 머신에서만 동작하는 자율 개발 파이프라인

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Chainlit](https://img.shields.io/badge/Chainlit-Web%20UI-FF6B35?style=for-the-badge)](https://chainlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[시작하기](#-빠른-시작) · [튜토리얼](TUTORIAL.md) · [아키텍처](#-아키텍처)

</div>

---

> 요구사항 한 마디면 Planner가 설계하고, Coder가 구현하고, Tester가 검증합니다.
> **인터넷 연결 없이. API 키 없이. 비용 없이.**

---

## ✨ 특징

| | 차별점 | 설명 |
|---|---|---|
| 🔒 | **완전한 데이터 주권** | 코드가 외부로 나가지 않음 |
| 🤖 | **계층적 AI 파이프라인** | Planner → Coder → Tester 자율 실행 |
| 🔄 | **자기 수정 피드백 루프** | 테스트 실패 시 자동 재작성 (최대 3회) |
| 💻 | **100% 로컬** | Ollama 기반, API 키 불필요 |

---

## 🏗 아키텍처

```
locky run "요구사항"   또는   locky (REPL 세션)
         │
         ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Planner    │───▶│   Coder     │───▶│   Tester    │
│             │    │             │    │             │
│ Context     │    │ Core Dev    │    │ QA Valid    │
│ Analyzer    │    │ Refactor    │    │ Security    │
│ Task Breaker│    │ Formatter   │    │ Auditor     │
└─────────────┘    └─────────────┘    └──────┬──────┘
                          ▲            FAIL  │ (max 3x)
                          └───────────────────┘
                                       │ PASS
                                       ▼
                                   완료 ✅
```

---

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.10+
- [Ollama](https://ollama.com/) 설치 및 실행 중

### 1. Ollama + 모델 준비

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
./scripts/install.sh
```

설치 후 **`locky` 명령을 어디서든 쓰는 방법** → [전역 설치 가이드](TUTORIAL.md#4-전역-설치--locky-명령-어디서든-사용)

### 3. 실행

```bash
# 인터랙티브 REPL (권장)
locky

# 원샷 실행
locky run "로그인 API에 JWT 인증 추가해줘"

# 특정 프로젝트 디렉터리 지정
locky run "버그 수정해줘" --workspace ~/myproject

# Web UI
locky dashboard
```

실행 화면:

```
요구사항: 파이썬으로 덧셈 프로그램 만들어줘
MCP 루트: /Users/you/myproject

────────────── 파이프라인 시작 ──────────────

[Planner] ─── Stage 1: Planning ───
[ContextAnalyzer] 단순 요청 감지 — 빠른 분석 모드
[Planner] 컨텍스트 분석 완료 (0.1s)
[Planner] 분석 완료: 1개 태스크 도출 — 총 1.2s

[Coder] ─── Stage 2: Coding ───
[CoreDeveloper] 태스크 T001 구현 중: 덧셈 프로그램 구현
[CoreDeveloper]   저장: addition.py
[Coder] 구현 완료: 1개 파일 수정 — 총 18.4s

[Tester] ─── Stage 3: Testing ───
[SecurityAuditor] 위험 패턴 스캔 중 (1개 파일)...
[Tester] 검증 완료: ✓ PASS — 총 3.1s

──────── 완료 — 총 22.7s ────────
```

---

## 🤖 에이전트 팀

| 팀 | 서브에이전트 | 역할 |
|:---:|---|---|
| 🧠 **Planner** | Context Analyzer, Task Breaker | 코드베이스 분석 & 원자 단위 태스크 설계 |
| 💻 **Coder** | Core Developer, Refactor Formatter | 코드 구현 & PEP8/컨벤션 정리 |
| 🧪 **Tester** | QA Validator, Security Auditor | pytest 실행 & OWASP 정적 분석 |

---

## 🛠 기술 스택

| 구성 | 기술 |
|---|---|
| LLM 엔진 | [Ollama](https://ollama.com/) — 로컬 추론 |
| 오케스트레이션 | [LangGraph](https://github.com/langchain-ai/langgraph) — 상태 기반 파이프라인 |
| CLI | Click + Rich + prompt_toolkit |
| Web UI | [Chainlit](https://chainlit.io/) |
| 파일 I/O | MCP Filesystem (경로 순회 방지 포함) |
| Git | GitPython |

---

## 🧠 지원 모델

| 모델 | 크기 | 특징 |
|---|---|---|
| `qwen2.5-coder:7b` | 4.7 GB | ⭐ 기본값 |
| `qwen2.5-coder:14b` | 9.0 GB | 고품질 |
| `codellama:7b` | 3.8 GB | 경량 |
| `deepseek-coder:6.7b` | 3.8 GB | 빠른 응답 |

```bash
# 모델 변경
export OLLAMA_MODEL=qwen2.5-coder:14b
locky run "..."
```

---

## ⚙️ 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | 사용할 Ollama 모델 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_TIMEOUT` | `300` | LLM 호출 타임아웃 (초) |
| `OLLAMA_TASK_TIMEOUT` | `60` | 태스크 분할 전용 타임아웃 (초) |
| `MCP_FILESYSTEM_ROOT` | 현재 디렉터리 | 파이프라인이 읽기·쓰기 가능한 루트 |
| `MAX_RETRY_ITERATIONS` | `3` | Coder-Tester 피드백 최대 반복 횟수 |

프로젝트 루트의 `.env` 파일에 저장하거나 셸에서 `export`로 설정합니다.

---

## 🗺 로드맵

- [x] LangGraph 파이프라인 (Planner / Coder / Tester)
- [x] 피드백 루프 (자동 재시도)
- [x] 인터랙티브 REPL (`locky`)
- [x] Chainlit Web UI
- [ ] VS Code Extension
- [ ] 멀티 모델 앙상블
- [ ] 프로젝트 장기 메모리

---

## 📄 라이선스

MIT License

---

<div align="center">

No cloud. No keys. Just code.

</div>
