# Locky

**자연어를 셸 명령으로. 100% 로컬, 100% 프라이빗.**

Locky는 자연어 요청을 실행 가능한 셸 명령으로 변환하는 로컬 CLI 도구입니다.
Ollama + Gemma 기반으로 동작하며, 클라우드 API 호출 없이 모든 데이터가 내 컴퓨터 안에서 처리됩니다.

```
locky [my-project]> 현재 디렉토리에서 100KB 넘는 파일 찾아줘
╭─ Command ─────────────────────────────────╮
│ find . -type f -size +100k               │
╰───────────────────────────────────────────╯
● Generating...  12 tok  38.4 t/s
Execute? [y/N]
```

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **REPL** | 대화형 세션 — 자연어로 입력하면 셸 명령으로 변환 |
| **원샷 모드** | `locky -c "..."` — 스크립트/CI에서 사용 가능 |
| **Autopilot** | `locky -a "..."` — 복잡한 작업을 여러 단계로 분해하여 순차 실행 |
| **Read-Think-Write** | Autopilot이 파일 읽기, diff 계산, 편집까지 사용자 승인 하에 수행 |
| **세션 메모리** | 최근 5개 작업을 기억하여 문맥 기반 명령 생성 |
| **자가 수정** | 명령 실패 시 AI가 에러를 분석하고 수정된 명령 제안 |
| **스트리밍 HUD** | 토큰 생성 과정을 실시간 표시 (토큰 수 + 속도) |
| **OS 자동 감지** | Windows PowerShell / macOS / Linux 셸 자동 판별 |
| **안전 장치** | 위험한 명령(`rm -rf /`, `DROP TABLE`)은 이중 확인 필요 |

## 사전 준비

- Python 3.10+
- [Ollama](https://ollama.com/) 로컬 실행

```bash
ollama pull gemma3:12b
```

## 설치

```bash
git clone https://github.com/dotoricode/locky.git
cd locky
pip install -e .
```

## 사용법

### 대화형 REPL

```bash
locky                    # 현재 디렉토리에서 시작
locky -w /path/to/dir    # 특정 디렉토리 지정
```

```
locky [my-project]> git 로그 최근 5개만 보여줘
╭─ Command ─────────────────────────────────╮
│ git log --oneline -5                      │
╰───────────────────────────────────────────╯
● Generating...  8 tok  42.1 t/s
Execute? [y/N] y

╭─ Result -- ok (exit 0) ──────────────────╮
│ a1b2c3d fix: handle null response        │
│ d4e5f6g feat: add streaming support      │
│ ...                                      │
╰──────────────────────────────────────────╯
```

### 원샷 모드

스크립트나 파이프라인에서 사용할 수 있습니다. 종료 코드 `0`(성공) / `1`(실패)을 반환합니다.

```bash
# 명령만 출력
locky -c "현재 브랜치 이름 알려줘"
# -> git branch --show-current

# JSON 출력 (프로그래밍 연동용)
locky -c "logs 폴더 압축해줘" --json
# -> {"status": "ok", "command": "tar -czf logs.tar.gz logs/", "message": "..."}

# 파이프라인에서 활용
locky -c "디스크 사용량 보여줘" | bash
```

### Autopilot 모드

복잡한 작업을 여러 단계로 분해하여 계획을 세우고, 각 단계를 사용자 승인 하에 실행합니다.

```bash
locky -a "py 파일 린트 돌리고 에러를 report.txt에 저장해줘"
```

```
╭─ Autopilot Plan ─────────────────────────────────────────╮
│ Step │ Action           │ Command                         │
│  1   │ Run linter       │ ruff check .                    │
│  2   │ Save report      │ ruff check . > report.txt 2>&1  │
╰──────────────────────────────────────────────────────────╯
Execute this 2-step plan? [y/N]
```

Autopilot은 `read_file`(파일 읽기)과 `edit_file`(파일 편집) 특수 도구도 지원합니다.
편집 시 자동으로 백업 파일을 생성하고, diff를 미리 보여준 뒤 승인을 받습니다.

REPL 안에서도 `/autopilot` 명령으로 사용할 수 있습니다:

```
locky [my-project]> /autopilot 테스트 파일 생성하고 pytest 실행해줘
```

### 자가 수정 (Self-Fix)

명령이 실패하면 Locky가 에러를 분석하고 수정된 명령을 제안합니다.

```
locky [my-project]> 파이썬 버전 확인해줘
╭─ Command ─────────────────────╮
│ python --version              │
╰───────────────────────────────╯
Execute? [y/N] y

╭─ Result -- error (exit 1) ───────────────────────╮
│ 'python' is not recognized as an internal or     │
│ external command                                 │
╰──────────────────────────────────────────────────╯
Press f for fix suggestion, or Enter to skip
[f/Enter] f

╭─ Suggested fix ──────────────╮
│ python3 --version            │
╰──────────────────────────────╯
Execute fix? [y/N] y

╭─ Fix result -- ok (exit 0) ──╮
│ Python 3.12.4                │
╰──────────────────────────────╯
```

### REPL 명령어

| 명령 | 설명 |
|------|------|
| `/help` | 도움말 표시 |
| `/clear` | 화면 지우기 |
| `/reset` | 세션 메모리 초기화 |
| `/autopilot <작업>` | 다단계 Autopilot 실행 |
| `/exit` | 종료 (또는 `exit`, `quit`) |

### CLI 옵션

```
locky [OPTIONS]

Options:
  -w, --workspace PATH    작업 디렉토리 지정 (기본: 현재 디렉토리)
  -c, --command TEXT      원샷 모드: 변환 결과 출력 후 종료
  --json                  JSON 형식 출력 (-c와 함께 사용)
  -a, --autopilot TEXT    Autopilot 모드: 다단계 작업 실행
  -h, --help              도움말
  --version               버전 정보
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | `gemma3:12b` | Ollama 모델 태그 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 URL |
| `OLLAMA_TIMEOUT` | `300` | 요청 타임아웃 (초) |

## 구조

```
locky_cli/
  main.py              CLI 진입점 (REPL + 원샷 + Autopilot)
  repl.py              대화형 REPL (스트리밍 HUD + 자가 수정)
  autopilot.py         Autopilot 실행 엔진 (Read-Think-Write)

actions/
  shell_command.py     핵심: 자연어 → 셸 명령 변환 (+ 자가 수정)

tools/
  ollama_client.py     Ollama /api/chat 클라이언트 (동기 + 스트리밍)
  ollama_guard.py      Ollama 헬스체크 + 자동 시작
  planner.py           다단계 작업 계획 생성기
  editor.py            안전한 파일 편집 (백업 + diff 미리보기)
  session_manager.py   JSON 기반 세션 메모리
  indexer.py           AST 기반 코드 맵 생성기

config.py              환경 변수 3개
```

## 개발

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v      # 테스트
ruff check .                    # 린트
ruff format .                   # 포맷
```

## 라이선스

MIT
