<div align="center">

# 🔒 Locky

**100% 로컬 AI 개발 에이전트**

외부 클라우드 없이, 당신의 머신에서만 동작하는 자율 개발 파이프라인

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Chainlit](https://img.shields.io/badge/Chainlit-Web%20UI-FF6B35?style=for-the-badge)](https://chainlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![100% Local](https://img.shields.io/badge/100%25-LOCAL-brightgreen?style=for-the-badge&logo=shield&logoColor=white)]()

[시작하기](#-빠른-시작) · [튜토리얼](TUTORIAL.md) · [아키텍처](#-아키텍처)

</div>

---

> `/develop "기능 추가해줘"` 한 마디면, Planner가 설계하고, Coder가 구현하고, Tester가 검증합니다.
> **인터넷 연결 없이, API 키 없이, 비용 없이.**

---

## ✨ Why Locky?

| | 차별점 | 설명 |
|---|---|---|
| 🔒 | **완전한 데이터 주권** | 코드가 외부로 나가지 않음. 당신의 코드는 당신의 것 |
| 🤖 | **계층적 AI 파이프라인** | Planner → Coder → Tester 자율 실행 |
| 🔄 | **자기 수정 피드백 루프** | 테스트 실패 시 자동으로 코드 재작성 (최대 3회) |
| 💻 | **100% 로컬** | Ollama 기반, 외부 API 제로, 무제한 무료 사용 |

---

## 🏗 아키텍처

```
┌──────────────────────────────────────────────────────┐
│                    🔒 Locky Pipeline                  │
│                                                      │
│  /develop "CMD"                                      │
│       │                                              │
│       ▼                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │ Planner  │───▶│  Coder   │───▶│  Tester  │       │
│  │  Team    │    │  Team    │    │  Team    │       │
│  │          │    │          │    │          │       │
│  │Context   │    │Core Dev  │    │QA Valid  │       │
│  │Analyzer  │    │Refactor  │    │Security  │       │
│  │Task Break│    │Formatter │    │Auditor   │       │
│  └──────────┘    └──────────┘    └────┬─────┘       │
│                       ▲          FAIL │              │
│                       └──────────────┘ (max 3x)     │
│                                   │ PASS             │
│                                   ▼                  │
│                               ✅ Complete             │
└──────────────────────────────────────────────────────┘
```

각 팀은 **LangGraph 상태 머신** 위에서 동작하며, 실패 시 자동으로 이전 단계로 되돌아가 자기 수정을 수행합니다.

---

## 🚀 빠른 시작

### 사전 요구사항

- macOS / Linux
- Python 3.10+
- [Ollama](https://ollama.com/) 설치됨

### 설치

```bash
# 1. Ollama 설치 및 모델 다운로드
brew install ollama && ollama serve
ollama pull qwen2.5-coder:7b

# 2. Locky 설치
git clone https://github.com/your-username/locky-agent.git
cd locky-agent
pip install -r requirements.txt

# 3. 실행 — CLI
python cli.py develop "로그인 API에 JWT 인증 추가해줘"

# 3-b. 실행 — Web UI (Chainlit)
chainlit run app.py
```

### 첫 번째 명령 실행

```bash
$ python cli.py develop "사용자 프로필 CRUD API를 FastAPI로 만들어줘"

🔒 Locky Starting...
🧠 [Planner]   요구사항 분석 중...
🧠 [Planner]   태스크 5개로 분해 완료
💻 [Coder]     코드 생성 중... (1/5)
💻 [Coder]     코드 생성 중... (5/5)
🧪 [Tester]    테스트 실행 중...
🧪 [Tester]    보안 감사 완료
✅ Pipeline Complete — 12 files modified, 0 errors
```

---

## 🤖 에이전트 팀 소개

| 팀 | Lead | Sub-agents | 역할 |
|:---:|---|---|---|
| 🧠 **Planner** | Strategic Planner | Context Analyzer, Task Breaker | 요구사항 분석 & 태스크 설계 |
| 💻 **Coder** | Tech Lead | Core Developer, Refactor Formatter | 코드 작성 & 품질 개선 |
| 🧪 **Tester** | QA Lead | QA Validator, Security Auditor | 테스트 & 보안 검증 |

### 🔄 피드백 루프

Tester가 실패를 감지하면 **자동으로 Coder 팀에 재작업을 요청**합니다.
최대 3회 재시도 후에도 실패하면 상세 리포트와 함께 종료됩니다.

```
Tester FAIL → Coder (retry 1) → Tester FAIL → Coder (retry 2) → Tester PASS ✅
```

---

## 🛠 기술 스택

| 구성 | 기술 | 역할 |
|---|---|---|
| LLM 엔진 | [Ollama](https://ollama.com/) | 로컬 LLM 실행 |
| 오케스트레이션 | [LangGraph](https://github.com/langchain-ai/langgraph) | 상태 기반 워크플로우 |
| 파일시스템 | MCP Filesystem | 코드 읽기/쓰기 |
| 버전 관리 | MCP Git / GitPython | 자동 커밋 |
| Web UI | [Chainlit](https://chainlit.io/) | 채팅 인터페이스 |
| CLI | Click + Rich | 터미널 인터페이스 |

---

## 🧠 지원 모델

Ollama에서 실행 가능한 모든 코딩 특화 모델을 지원합니다.

| 모델 | 크기 | 추천 용도 |
|---|---|---|
| `qwen2.5-coder:7b` | 4.7 GB | ⭐ 기본값 (균형) |
| `qwen2.5-coder:14b` | 9.0 GB | 고품질 코드 |
| `codellama:7b` | 3.8 GB | 경량 환경 |
| `deepseek-coder:6.7b` | 3.8 GB | 빠른 응답 |

모델 변경:

```bash
python cli.py develop "기능 추가" --model qwen2.5-coder:14b
```

---

## ⚙️ 설정

```yaml
# config.yaml
model: qwen2.5-coder:7b
ollama_host: http://localhost:11434
max_retries: 3
workspace: ./workspace
```

---

## 🗺 로드맵

- [x] LangGraph 파이프라인 기본 구조
- [x] Planner / Coder / Tester 3팀 구조
- [x] Feedback Loop (자동 재시도)
- [x] Chainlit Web UI
- [ ] VS Code Extension
- [ ] 멀티 모델 앙상블
- [ ] 프로젝트 메모리 (장기 컨텍스트)

---

## 🤝 기여하기

PR과 이슈는 언제나 환영합니다!

```bash
git clone https://github.com/your-username/locky-agent.git
cd locky-agent
pip install -r requirements-dev.txt
pre-commit install
```

---

## 📄 라이선스

MIT License — 자유롭게 사용, 수정, 배포하세요.

---

<div align="center">

Made with ❤️ and 🔒 — No cloud. No keys. Just code.

</div>
