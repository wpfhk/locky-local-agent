# Locky 튜토리얼

Locky 프로젝트의 사용 튜토리얼 문서입니다. Ollama 설치부터 실제 사용까지 단계별로 안내합니다.

---

## 1. 사전 준비 — Ollama 설치 및 실행

### macOS

```bash
brew install ollama
ollama serve   # 백그라운드 실행
```

또는 https://ollama.com/download 에서 앱 다운로드

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
systemctl start ollama   # systemd
# 또는
ollama serve
```

### Windows

https://ollama.com/download/windows 에서 설치 프로그램 다운로드

### 실행 확인

```bash
curl http://localhost:11434/api/tags
# {"models":[...]} 응답이 오면 정상
```

---

## 2. 코딩 특화 모델 다운로드

Locky 기본 모델: `qwen2.5-coder:7b` (코드 생성 특화, ~4.7GB)

```bash
ollama pull qwen2.5-coder:7b
```

### 대안 모델

| 모델명 | 크기 | 특징 |
|---|---|---|
| `qwen2.5-coder:7b` | 4.7GB | 기본값, 코드 품질 우수 |
| `qwen2.5-coder:14b` | 9.0GB | 더 높은 정확도 |
| `codellama:7b` | 3.8GB | Meta 코딩 모델 |
| `deepseek-coder:6.7b` | 3.8GB | 경량 코딩 모델 |
| `llama3.1:8b` | 4.7GB | 범용 (코드 포함) |

`config.py`의 `OLLAMA_MODEL` 환경변수로 변경 가능:

```bash
export OLLAMA_MODEL=qwen2.5-coder:14b
```

---

## 3. Locky 설치

```bash
git clone https://github.com/your-org/locky-agent
cd locky-agent
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 4. Locky 실행 — CLI

```bash
# 기본 실행 — 첫 번째 인자만 요구사항으로 받습니다 (`develop`은 서브커맨드가 아님)
python cli.py "사용자 인증 모듈에 JWT 토큰 기반 로그인 기능을 추가해줘"
```

실행 화면 예시:

```
╭─────────────────────────────────╮
│  🔒 Locky — Local AI Agent      │
│  Planner → Coder → Tester       │
╰─────────────────────────────────╯
⟳ [Planner] 코드베이스 분석 중...
✓ [Planner] 분석 완료: 5개 태스크 도출
⟳ [Coder] 코드 작성 중...
✓ [Coder] 구현 완료: 3개 파일 수정
⟳ [Tester] 품질 검증 중...
✓ [Tester] 검증 완료: PASS
```

---

## 5. Locky 실행 — Web UI (Chainlit)

```bash
chainlit run ui/app.py

# 브라우저에서 http://localhost:8000 접속
# 채팅창에 입력:
# /develop 결제 API에 환불 기능 추가해줘
```

### Web UI 기능

- 각 단계(Planner/Coder/Tester)를 Step으로 실시간 확인
- `/develop` 없이 일반 메시지 입력 시 Ollama와 직접 대화
- 대화 히스토리 유지

---

## 6. 환경변수 설정 (선택)

`.env` 파일 생성:

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_TIMEOUT=300
MCP_FILESYSTEM_ROOT=/path/to/your/project
MAX_RETRY_ITERATIONS=3
```

---

## 7. 파이프라인 흐름 설명

```
사용자 입력 (CMD)
      │
      ▼
┌─────────────┐
│  Planner    │  ← Context Analyzer: 코드베이스 분석
│  Team       │  ← Task Breaker: 원자 단위 태스크 분할
└──────┬──────┘
       │ task_list (JSON)
       ▼
┌─────────────┐
│  Coder      │  ← Core Developer: 코드 작성/수정
│  Team       │  ← Refactor Formatter: 컨벤션 적용
└──────┬──────┘
       │ modified_files
       ▼
┌─────────────┐    FAIL (최대 3회)
│  Tester     │─────────────────────┐
│  Team       │  ← QA Validator     │
└──────┬──────┘  ← Security Auditor │
       │ PASS                       │
       ▼                            ▼
    완료 ✅              Coder Team으로 피드백 🔄
```

---

## 8. 자주 묻는 질문 (FAQ)

**Q: Ollama가 응답하지 않아요**

A: `ollama serve` 가 실행 중인지 확인. 포트 11434가 방화벽에 막혀 있지 않은지 확인.

---

**Q: 모델 응답이 너무 느려요**

A: 더 작은 모델(`codellama:7b`) 사용 또는 GPU 가속 확인 (`ollama ps`).

---

**Q: 특정 프로젝트 디렉토리에서 실행하고 싶어요**

A: `MCP_FILESYSTEM_ROOT=/your/project/path python cli.py "..."`

---

**Q: 테스트가 계속 실패해요**

A: `MAX_RETRY_ITERATIONS=5` 로 재시도 횟수 늘리기. 또는 더 큰 모델 사용.

---

**Q: `python cli.py develop "..."` 실행 시 `Got unexpected extra argument` 가 나와요**

A: `develop`은 Click 서브커맨드가 아니라, 요구사항만 넘기면 됩니다.

```bash
python cli.py "로그인 API에 JWT 인증 추가해줘"
```

`develop`을 넣으면 첫 토큰이 요구사항으로 잡히고, 따옴표 안 문장이 “남는 인자”로 처리되어 위 오류가 납니다.
