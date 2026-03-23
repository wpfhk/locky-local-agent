# Locky 튜토리얼

Ollama 설치부터 실제 사용까지 단계별 안내입니다.

---

## 1. Ollama 설치 및 실행

### macOS

```bash
brew install ollama
ollama serve          # 별도 터미널에서 실행 (포트 11434)
```

또는 [ollama.com/download](https://ollama.com/download) 에서 앱 설치 (GUI 포함).

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
# 또는 systemd 환경: systemctl enable --now ollama
```

### Windows

[ollama.com/download/windows](https://ollama.com/download/windows) 에서 설치 프로그램 다운로드.

### 실행 확인

```bash
curl http://localhost:11434/api/tags
# {"models":[...]} 가 반환되면 정상
```

---

## 2. 모델 다운로드

```bash
# 기본값 (추천)
ollama pull qwen2.5-coder:7b

# 더 높은 품질 (RAM 16GB 이상)
ollama pull qwen2.5-coder:14b
```

| 모델 | 크기 | 특징 |
|---|---|---|
| `qwen2.5-coder:7b` | 4.7 GB | 기본값, 코드 품질 우수 |
| `qwen2.5-coder:14b` | 9.0 GB | 더 높은 정확도 |
| `codellama:7b` | 3.8 GB | 경량 환경 |
| `deepseek-coder:6.7b` | 3.8 GB | 빠른 응답 |

---

## 3. Locky 설치

```bash
git clone https://github.com/your-username/locky-agent.git
cd locky-agent
./scripts/install.sh
```

`install.sh`는 `.venv` 가상환경을 생성하고 `pip install -e .`로 editable 설치합니다.
소스 수정이 재설치 없이 즉시 반영됩니다.

---

## 4. 전역 설치 — `locky` 명령 어디서든 사용

`install.sh` 실행 후 `locky`를 터미널 어디서든 쓰려면 아래 방법 중 하나를 선택하세요.

### 방법 A — pipx (권장)

[pipx](https://pipx.pypa.io/)는 Python 도구를 독립 환경으로 전역 설치합니다.

```bash
# 1. pipx 설치 (없는 경우)
brew install pipx          # macOS

# 2. locky-agent 저장소 디렉터리 안에서 실행
cd /path/to/locky-agent   # 클론한 실제 경로로 변경
pipx install .

# 3. PATH 등록 (최초 1회 — 설치 후 경고가 나오면 반드시 실행)
pipx ensurepath
source ~/.zshrc             # 또는 터미널 재시작

# 4. 확인
locky --version
```

> `pipx install .` 후 `zsh: command not found: locky` 가 나오면 `~/.local/bin`이 PATH에 없는 것입니다.
> `pipx ensurepath && source ~/.zshrc` 로 해결됩니다.

이 방법은 가상환경 활성화 없이 어느 디렉터리에서나 `locky` 명령이 동작합니다.

> **소스 수정 후 업데이트:** `pipx install --force .`
> **이미 `install.sh`로 설치한 경우** 방법 B(PATH 추가)가 더 간단합니다.

### 방법 B — 셸 설정에 PATH 추가

`install.sh`로 이미 `.venv`가 만들어진 경우 가장 간단합니다.

```bash
# ~/.zshrc 또는 ~/.bashrc 에 아래 줄 추가 (실제 경로로 변경)
export PATH="/Users/yourname/locky-agent/.venv/bin:$PATH"

# 현재 셸에 즉시 적용
source ~/.zshrc

# 확인
locky --version
```

### 방법 C — 가상환경 활성화

매번 사용하기 전에 활성화:

```bash
source /path/to/locky-agent/.venv/bin/activate
locky run "..."
```

> **어느 방법이든 `locky`는 실행 시점의 현재 디렉터리를 작업 루트로 사용합니다.**
> 즉, `~/myproject`에서 `locky run "..."` 을 실행하면 해당 프로젝트에서만 읽기·쓰기가 이뤄집니다.

---

## 5. CLI 사용법

### 인터랙티브 REPL (권장)

```bash
cd ~/myproject
locky
```

```
╭─────────────────────────────────────────────────────╮
│  Locky                                              │
│  모델   qwen2.5-coder:7b                            │
│  워크스페이스  /Users/you/myproject                  │
│  권한   workspace (이 디렉터리 이하)                  │
│  Planner → Coder → Tester · /help 로 명령 안내      │
╰─────────────────────────────────────────────────────╯

locky [/Users/you/myproject]> 파이썬으로 덧셈 프로그램 만들어줘

[Planner] ─── Stage 1: Planning ───
[ContextAnalyzer] 단순 요청 감지 — 빠른 분석 모드
[Planner] 분석 완료: 1개 태스크 도출 — 총 1.2s

[Coder] ─── Stage 2: Coding ───
[CoreDeveloper]   저장: addition.py
[Coder] 구현 완료: 1개 파일 수정 — 총 18.4s

[Tester] ─── Stage 3: Testing ───
[Tester] 검증 완료: ✓ PASS — 총 3.1s

locky [/Users/you/myproject]> exit
종료합니다.
```

#### REPL 내부 명령

| 명령 | 설명 |
|------|------|
| `exit` 또는 `quit` | 종료 (슬래시 없이도 동작) |
| `/exit` 또는 `/quit` | 동일 |
| `/develop [요구사항]` | 개발 파이프라인 명시적 실행 |
| `/mode workspace` | 현재 디렉터리 이하만 접근 (기본) |
| `/mode full` | 로컬 전체 접근 (확인 프롬프트) |
| `/permissions` | 현재 권한 모드와 루트 표시 |
| `/clear` | 화면 재출력 |
| `/help` | 명령 목록 |
| `Ctrl+C` / `Ctrl+D` | 즉시 종료 |

> REPL에서 슬래시 없이 일반 텍스트를 입력하면 자동으로 파이프라인이 실행됩니다.

### 원샷 실행

```bash
# 현재 디렉터리 기준
locky run "로그인 API에 JWT 인증 추가해줘"

# 특정 프로젝트 지정
locky run "버그 수정해줘" --workspace ~/myproject

# 로컬 전체 접근 (확인 프롬프트 표시)
locky run "..." --full
```

---

## 6. Web UI (Chainlit)

```bash
locky dashboard
# 또는
locky web
```

브라우저에서 `http://localhost:8000` 접속.

- `/develop [요구사항]` — 파이프라인 실행
- 일반 텍스트 입력 — Ollama와 직접 대화 (파이프라인 미실행)

---

## 7. 환경변수 설정

프로젝트 루트에 `.env` 파일을 만들거나, 셸에서 `export`로 설정합니다.

```bash
# .env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_TIMEOUT=300
OLLAMA_TASK_TIMEOUT=60
MCP_FILESYSTEM_ROOT=/path/to/your/project
MAX_RETRY_ITERATIONS=3
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | 사용할 모델 |
| `OLLAMA_TIMEOUT` | `300` | LLM 호출 타임아웃 (초) |
| `OLLAMA_TASK_TIMEOUT` | `60` | 태스크 분할 전용 타임아웃 (초) |
| `MCP_FILESYSTEM_ROOT` | 현재 디렉터리 | 파이프라인 파일 접근 루트 |
| `MAX_RETRY_ITERATIONS` | `3` | Coder-Tester 피드백 최대 반복 횟수 |

> `MCP_FILESYSTEM_ROOT`를 명시하지 않으면 `locky` 실행 시점의 현재 디렉터리가 루트로 사용됩니다.
> 보통은 설정하지 않고 원하는 프로젝트 디렉터리에서 `locky`를 실행하는 것이 자연스럽습니다.

---

## 8. 파이프라인 흐름

```
사용자 입력 (cmd)
      │
      ▼
┌─────────────┐
│  Planner    │  ← ContextAnalyzer: 코드베이스 분석
│             │    (단순 요청은 Ollama 없이 빠른 분석)
│             │  ← TaskBreaker: 원자 단위 태스크 JSON 생성
└──────┬──────┘
       │ task_list
       ▼
┌─────────────┐
│  Coder      │  ← CoreDeveloper: Ollama 코드 생성 → 파일 저장
│             │  ← RefactorFormatter: PEP8 정리
└──────┬──────┘
       │ modified_files
       ▼
┌─────────────┐   FAIL → (최대 3회 재시도)
│  Tester     │  ← QAValidator: pytest 생성·실행
│             │  ← SecurityAuditor: OWASP 패턴 스캔
└──────┬──────┘
       │ PASS
       ▼
     완료 ✅
```

---

## 9. 자주 묻는 질문

**Q: `locky: command not found` 가 나와요**

A: [전역 설치](#4-전역-설치--locky-명령-어디서든-사용) 섹션을 참고하세요.
가장 빠른 방법은 `pipx install /path/to/locky-agent` 입니다.

---

**Q: Ollama가 응답하지 않아요**

A: `ollama serve`가 실행 중인지, 포트 11434가 열려 있는지 확인하세요.

```bash
curl http://localhost:11434/api/tags
```

---

**Q: 모델 응답이 너무 느려요**

A: 더 작은 모델로 변경하거나 GPU 가속 여부를 확인하세요.

```bash
ollama ps                          # 현재 로드된 모델 확인
export OLLAMA_MODEL=codellama:7b   # 경량 모델로 변경
```

---

**Q: 특정 프로젝트 디렉터리에서만 작동하게 하고 싶어요**

A: 두 가지 방법이 있습니다.

```bash
# 방법 1: 해당 디렉터리에서 실행
cd ~/myproject && locky run "..."

# 방법 2: --workspace 옵션
locky run "..." --workspace ~/myproject
```

---

**Q: 테스트가 계속 실패해요**

A: 재시도 횟수를 늘리거나 더 큰 모델을 사용하세요.

```bash
export MAX_RETRY_ITERATIONS=5
export OLLAMA_MODEL=qwen2.5-coder:14b
locky run "..."
```

---

**Q: REPL에서 종료가 안 돼요**

A: `exit`, `quit`, `/exit`, `/quit` 중 하나를 입력하거나 `Ctrl+D`를 누르세요.
