# Locky v1.0.0

100% 로컬 CLI. 자연어 -> 셸 명령 변환. Ollama + Gemma 기반.

## Quick Commands

```bash
python -m pytest tests/ -v   # 전체 테스트 (94개)
ruff check . && ruff format . # 린트 + 포맷
locky                          # REPL (스트리밍 HUD)
locky -c "자연어"              # 원샷
locky -c "자연어" --json       # JSON 출력
locky -a "복잡한 작업"         # Autopilot (다단계)
```

## Structure

```
locky_cli/main.py         CLI 진입 (REPL + 원샷 + Autopilot)
locky_cli/repl.py         REPL 루프 (스트리밍 + HUD)
locky_cli/autopilot.py    Autopilot 실행 엔진 (Read-Think-Write)
actions/shell_command.py   핵심: 자연어 -> 셸 명령 (Ollama, 스트리밍)
tools/ollama_client.py     Ollama /api/chat 클라이언트 (sync + stream)
tools/planner.py           다단계 작업 계획 생성기
tools/editor.py            안전한 파일 편집 (backup + diff)
tools/session_manager.py   JSON 세션 메모리
tools/indexer.py           AST 코드 맵 생성기
tools/ollama_guard.py      Ollama 헬스체크 + 자동시작
config.py                  환경변수 3개 (MODEL, BASE_URL, TIMEOUT)
```

## Key Interfaces

`actions.shell_command.run(root, request, history="", on_token=None) -> dict`
- Returns `{"status": "ok"|"error", "command": str, "message": str}`
- `on_token`: 스트리밍 콜백 (None이면 blocking chat)
- OS 자동 감지, 한글 응답 거부, 코드 키워드 감지, Few-shot

`tools.planner.generate_plan(workspace, request, on_token=None) -> list[dict]`
- 복잡한 요청을 최대 7단계 셸 명령으로 분해
- `edit_file`/`read_file` 특수 도구 지원

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `gemma3:12b` | Ollama model tag |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_TIMEOUT` | `300` | Timeout (seconds) |

## Constraints

- 의존성 4개만: httpx, click, rich, prompt-toolkit
- 상세 아키텍처/결정사항: `.omc/docs/` 참조

<!-- afd:setup -->
## afd -- AI Token Optimizer & Self-Healing

This project uses [afd](https://www.npmjs.com/package/@dotoricode/afd) for token optimization and file protection.

### File Reading Rules
- **`afd_read` MCP 도구를 네이티브 Read 대신 사용하라.** 10KB 이상 파일은 자동으로 홀로그램(구조 스켈레톤)으로 압축되어 반환된다. 특정 구간이 필요하면 `startLine`/`endLine` 파라미터로 정밀 조회할 수 있다.
- **프로젝트 구조를 파악할 때는 `afd://workspace-map` MCP 리소스를 먼저 읽어라.** 파일 트리 + export 시그니처가 한 번에 제공된다.
- **대용량 파일(100줄+)의 구조를 파악할 때는 `afd_hologram` MCP 도구를 사용하라.** 타입 시그니처만 추출하여 80%+ 토큰을 절약한다.

### Self-Healing
- afd가 파일을 복구했다는 `[afd]` 메시지가 보이면, 해당 파일 편집을 중단하고 `afd_hologram`으로 구조를 먼저 파악하라.
<!-- afd:setup -->
