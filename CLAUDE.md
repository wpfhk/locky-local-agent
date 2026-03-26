# Locky Agent -- CLAUDE.md

100% 로컬 CLI 도구 (v4.0.0). 자연어를 셸 명령으로 변환하여 확인 후 실행. Ollama 기반.

---

## 프로젝트 구조

```
locky-agent/
├── locky_cli/
│   ├── __init__.py       # 패키지 마커
│   ├── main.py           # Click CLI 진입점 (REPL만)
│   └── repl.py           # REPL 루프 (자연어 -> shell_command -> 확인 -> 실행)
├── actions/
│   ├── __init__.py       # shell_command만 export
│   └── shell_command.py  # 핵심: 자연어 -> 셸 명령 변환
├── tools/
│   ├── __init__.py       # OllamaClient만 export
│   ├── ollama_client.py  # Ollama /api/chat 동기/스트리밍 클라이언트
│   └── ollama_guard.py   # Ollama 헬스체크 + 자동 시작
├── config.py             # 환경변수 기반 단순 설정 (3개 변수)
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # pytest 공통 픽스처
│   └── test_shell_command.py  # 핵심 테스트
├── requirements.txt
└── pyproject.toml
```

---

## 핵심 아키텍처

### 단일 기능: 자연어 -> 셸 명령 변환

```
사용자 입력 (자연어)
  -> actions/shell_command.py (Ollama API 호출)
  -> 명령 추출 + 검증
  -> 사용자 확인 (y/N)
  -> subprocess.run (셸 실행)
  -> 결과 출력
```

### actions/shell_command.py

`run(root: Path, request: str) -> dict` 시그니처.

- 프롬프트: Few-shot 예시 포함, 코드 생성 거부 지시
- 검증: `_is_valid_command()` -- 한글 감지, 프로그래밍 코드 키워드 감지
- Ollama 직접 호출 (멀티 LLM 레지스트리 제거)
- `temperature=0`, `num_predict=80`, `top_k=1`

### CLI 사용법

```
locky              # REPL 진입 (자연어 입력)
locky -w /path     # 특정 디렉터리에서 시작
locky --help       # 도움말
```

### REPL 명령

```
/help   -- 도움말
/clear  -- 화면 초기화
/exit   -- 종료 (exit, quit도 가능)

자연어 입력 -> 셸 명령 변환 -> 확인 후 실행
```

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | 사용할 Ollama 모델 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_TIMEOUT` | `300` | LLM 호출 타임아웃 (초) |

---

## 설계 결정 사항

- **v4 전면 리라이트**: v3의 과도한 복잡도(멀티 LLM/MCP/session/sandbox/plugins/recipes)를 제거하고 shell_command 하나에 집중
- **Ollama 직접 호출**: LLM Registry 제거, httpx로 Ollama API 직접 호출
- **프롬프트 강화**: Few-shot 예시 + 코드 생성 거부 지시로 Python 코드 출력 방지
- **검증 로직 강화**: `import`, `class`, `def`, `function` 등 프로그래밍 키워드 감지로 잘못된 명령 거부
- **최소 의존성**: httpx, click, rich, prompt-toolkit 4개만

---

## 테스트

```bash
python -m pytest tests/test_shell_command.py -v
```

테스트 커버리지: actions/shell_command.py의 모든 공개 함수 + 통합 테스트 (Ollama mock)
