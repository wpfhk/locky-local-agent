# Locky 튜토리얼

Ollama 설치부터 실제 사용까지 단계별 안내입니다.

---

## 1. Ollama 설치 및 실행

> `locky commit` 명령만 Ollama가 필요합니다. 나머지 명령은 Ollama 없이 동작합니다.

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

## 2. 모델 다운로드 (`commit` 명령 사용 시만 필요)

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
pip install -e .
```

`pip install -e .`은 editable 설치로, 소스 수정이 재설치 없이 즉시 반영됩니다.

---

## 4. 전역 설치 — `locky` 명령 어디서든 사용

`locky`를 터미널 어디서든 쓰려면 아래 방법 중 하나를 선택하세요.

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

> **소스 수정 후 재설치:** `pipx install --force .`

### 방법 B — 셸 설정에 PATH 추가

이미 `.venv`가 만들어진 경우 가장 간단합니다.

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
locky commit
```

> **어느 방법이든 `locky`는 실행 시점의 현재 디렉터리를 작업 루트로 사용합니다.**
> 즉, `~/myproject`에서 실행하면 해당 프로젝트에서만 읽기·쓰기가 이뤄집니다.

---

## 5. CLI 사용법

### 인터랙티브 REPL (권장)

```bash
cd ~/myproject
locky
```

```
╭──────────────────────────────────────────────────────────╮
│  Locky                                                   │
│  버전        0.3.0                                       │
│  모델        qwen2.5-coder:7b                            │
│  워크스페이스 /Users/you/myproject                        │
╰─ 개발자 귀찮은 작업 자동화 · /help 로 명령 안내 ─────────╯

locky [/Users/you/myproject]> /scan
╭─ scan — issues_found ─────────────────╮
│ issues (2개):                         │
│   [high] app.py:42 — shell=True 사용  │
│   [low] utils.py:17 — SSL 검증 비활성 │
╰───────────────────────────────────────╯

locky [/Users/you/myproject]> /commit
╭─ commit — ok ───────────────────────────────╮
│ message: feat(auth): add jwt token verify   │
│ committed: true                             │
╰─────────────────────────────────────────────╯

locky [/Users/you/myproject]> exit
종료합니다.
```

#### REPL 슬래시 명령

| 명령 | 설명 |
|------|------|
| `/commit [--dry-run] [--push]` | AI 커밋 메시지 생성 및 커밋 |
| `/format [--check] [PATH...]` | black + isort + flake8 실행 |
| `/test [PATH] [-v]` | pytest 실행 |
| `/todo [--output FILE]` | TODO/FIXME 수집 |
| `/scan [--severity LEVEL]` | 보안 패턴 스캔 |
| `/clean [--force]` | 캐시/임시파일 정리 |
| `/deps` | 의존성 버전 확인 |
| `/env [--output FILE]` | .env.example 생성 |
| `/clear` | 화면 초기화 |
| `/help` | 명령 목록 |
| `exit` / `quit` | 종료 (슬래시 없이도 동작) |

> REPL에서 슬래시 없이 일반 텍스트를 입력하면 지원하는 명령 안내가 표시됩니다.

### 단발 명령어 (CLI 서브커맨드)

```bash
# 커밋 메시지 자동 생성 및 커밋
locky commit

# dry-run (커밋하지 않고 메시지만 확인)
locky commit --dry-run

# 커밋 후 push까지
locky commit --push

# 코드 포매팅
locky format

# 검사만 (실제 수정 안 함)
locky format --check

# 테스트 실행
locky test
locky test tests/test_api.py -v

# TODO 수집 및 파일 저장
locky todo
locky todo --output todos.md

# 보안 스캔
locky scan
locky scan --severity high      # high 이상만 표시

# 임시 파일 정리 (dry-run 먼저 확인)
locky clean
locky clean --force             # 실제 삭제

# 의존성 버전 확인
locky deps

# .env.example 생성
locky env
locky env --output .env.template
```

---

## 6. Web UI (Chainlit)

```bash
locky dashboard
# 또는
locky web
```

브라우저에서 `http://localhost:8000` 접속.

Web UI에서도 `/commit`, `/format`, `/scan` 등 동일한 자동화 명령을 사용할 수 있습니다.

---

## 7. 환경변수 설정

프로젝트 루트에 `.env` 파일을 만들거나, 셸에서 `export`로 설정합니다.

```bash
# .env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_TIMEOUT=300
MCP_FILESYSTEM_ROOT=/path/to/your/project
```

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | 사용할 모델 (`commit` 명령용) |
| `OLLAMA_TIMEOUT` | `300` | LLM 호출 타임아웃 (초) |
| `MCP_FILESYSTEM_ROOT` | 현재 디렉터리 | 파일 접근 루트 |

> `MCP_FILESYSTEM_ROOT`를 명시하지 않으면 `locky` 실행 시점의 현재 디렉터리가 루트로 사용됩니다.
> 보통은 설정하지 않고 원하는 프로젝트 디렉터리에서 `locky`를 실행하는 것이 자연스럽습니다.

---

## 8. 자주 묻는 질문

**Q: `locky: command not found` 가 나와요**

A: [전역 설치](#4-전역-설치--locky-명령-어디서든-사용) 섹션을 참고하세요.
가장 빠른 방법: `cd /path/to/locky-agent && pipx install . && pipx ensurepath && source ~/.zshrc`

---

**Q: Ollama가 응답하지 않아요**

A: `commit` 명령만 Ollama를 사용합니다. 나머지 명령은 Ollama 없이 동작합니다.
`commit` 사용 시 `ollama serve`가 실행 중인지 확인:

```bash
curl http://localhost:11434/api/tags
```

---

**Q: 모델 응답이 너무 느려요 (`commit` 명령)**

A: 더 작은 모델로 변경하거나 GPU 가속 여부를 확인하세요.

```bash
ollama ps                          # 현재 로드된 모델 확인
export OLLAMA_MODEL=codellama:7b   # 경량 모델로 변경
```

---

**Q: REPL에서 종료가 안 돼요**

A: `exit`, `quit`, `/exit`, `/quit` 중 하나를 입력하거나 `Ctrl+D`를 누르세요.

---

**Q: `locky format` 실행 시 `black not found` 오류가 나와요**

A: 포매팅 도구가 설치되어 있지 않습니다. 대상 프로젝트 환경에 설치하세요:

```bash
pip install black isort flake8
```

---

**Q: 특정 프로젝트에서만 사용하고 싶어요**

A: 해당 프로젝트 디렉터리에서 `locky`를 실행하면 됩니다.

```bash
cd ~/myproject && locky
```
