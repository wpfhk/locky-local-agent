"""QA Validator — 단위 테스트 생성 및 실행 서브에이전트."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import List

from config import OLLAMA_MODEL
from locky_cli.fs_context import get_filesystem_root
from states.state import LockyGlobalState
from tools.mcp_filesystem import read_file, write_file
from tools.ollama_client import OllamaClient

_MAX_FILE_SIZE = 5000
_TESTS_DIR = "tests"


def _build_test_prompt(file_path: str, content: str) -> str:
    """단위 테스트 생성 프롬프트를 생성합니다."""
    return f"""당신은 Python 테스트 전문가입니다. 아래 코드에 대한 pytest 단위 테스트를 작성하세요.

## 대상 파일: {file_path}
```python
{content}
```

## 테스트 작성 원칙
- pytest 프레임워크 사용
- Happy path 테스트 (정상 케이스)
- Edge case 테스트 (경계값, 빈 입력 등)
- 에러 케이스 테스트 (예외 발생 검증)
- 외부 의존성은 unittest.mock으로 모킹
- 각 테스트 함수는 `test_`로 시작

## 출력 규칙
- 테스트 코드만 출력하세요 (설명 없이)
- import 문 포함 완전한 파이썬 파일로 작성하세요
"""


def _derive_test_path(file_path: str) -> str:
    """대상 파일 경로에서 테스트 파일 경로를 도출합니다."""
    p = Path(file_path)
    stem = p.stem  # 확장자 제외 파일명
    # tests/test_<모듈명>.py
    test_name = f"test_{stem}.py"
    return str(Path(_TESTS_DIR) / test_name)


def _extract_code(response: str) -> str:
    """응답에서 Python 코드 블록을 추출합니다."""
    # 코드 블록 파싱
    match = re.search(r"```(?:python)?\n([\s\S]+?)\n```", response)
    if match:
        return match.group(1).strip()
    # 코드 블록 없으면 전체 응답 사용
    return response.strip()


def _parse_pytest_output(output: str) -> dict:
    """pytest 출력을 파싱하여 pass/fail/error 수를 반환합니다."""
    result = {
        "passed": 0,
        "failed": 0,
        "error": 0,
        "failed_details": [],
        "raw_output": output[-3000:] if len(output) > 3000 else output,
    }

    # 요약 줄 파싱: "5 passed, 2 failed, 1 error"
    summary_match = re.search(
        r"(\d+) passed|(\d+) failed|(\d+) error",
        output,
        re.IGNORECASE,
    )

    passed_match = re.search(r"(\d+) passed", output)
    failed_match = re.search(r"(\d+) failed", output)
    error_match = re.search(r"(\d+) error", output)

    if passed_match:
        result["passed"] = int(passed_match.group(1))
    if failed_match:
        result["failed"] = int(failed_match.group(1))
    if error_match:
        result["error"] = int(error_match.group(1))

    # 실패한 테스트 이름 추출
    failed_tests = re.findall(r"FAILED\s+([\w/:.]+)", output)
    for test in failed_tests:
        result["failed_details"].append({
            "test_name": test,
            "error": "테스트 실패 (상세 내용은 raw_output 참조)",
            "file": test.split("::")[0] if "::" in test else test,
            "suggestion": "구현 코드 또는 테스트 로직 검토 필요",
        })

    return result


def validate_quality(state: LockyGlobalState) -> dict:
    """
    modified_files에 대해 단위 테스트를 생성하고 pytest로 실행합니다.

    Args:
        state: 전역 파이프라인 상태 (coder_output.modified_files 포함)

    Returns:
        tester_output에 test_results를 포함한 dict
    """
    coder_output = state.get("coder_output") or {}
    modified_files: List[str] = coder_output.get("modified_files", [])

    # 수정된 파일이 없으면 스킵
    if not modified_files:
        print("[QAValidator] 수정된 파일 없음 — 테스트 생성 생략")
        existing_tester = state.get("tester_output") or {}
        return {
            "tester_output": {
                **existing_tester,
                "test_results": [{"test": "unit_tests", "status": "pass", "passed": 0, "failed": 0, "error": 0, "failed_details": []}],
                "tests_written": 0,
                "pytest_summary": {"passed": 0, "failed": 0, "error": 0},
                "generated_test_files": [],
            }
        }

    # Python 파일만 테스트 생성 대상
    py_files = [f for f in modified_files if f.endswith(".py") and not f.startswith("test")]

    cmd = (state.get("coder_output") or {}).get("commit_message_draft", "") or ""
    _complex_keywords = ("리팩토링", "마이그레이션", "기존", "수정해", "변경해", "refactor", "migrate", "existing")
    _raw_cmd = state.get("cmd", "")
    is_simple = len(_raw_cmd) <= 150 and not any(kw in _raw_cmd for kw in _complex_keywords)

    if is_simple:
        print("[QAValidator] 단순 요청 — 테스트 생성 스킵")
        existing_tester = state.get("tester_output") or {}
        return {
            "tester_output": {
                **existing_tester,
                "test_results": [{"test": "unit_tests", "status": "pass", "passed": 0, "failed": 0, "error": 0, "failed_details": []}],
                "tests_written": 0,
                "pytest_summary": {"passed": 0, "failed": 0, "error": 0},
                "generated_test_files": [],
            }
        }

    client = OllamaClient(model=OLLAMA_MODEL)
    generated_tests: List[str] = []

    # tests 디렉토리 생성
    tests_path = get_filesystem_root() / _TESTS_DIR
    tests_path.mkdir(parents=True, exist_ok=True)

    # tests/__init__.py 생성
    init_path = tests_path / "__init__.py"
    if not init_path.exists():
        init_path.write_text("", encoding="utf-8")

    for file_path in py_files:
        print(f"[QAValidator] 테스트 생성 중: {file_path}")
        try:
            content = read_file(file_path)
        except (FileNotFoundError, ValueError) as e:
            print(f"[QAValidator] 읽기 실패 {file_path}: {e}")
            continue

        if not content.strip():
            continue

        prompt = _build_test_prompt(file_path, content[:_MAX_FILE_SIZE])
        messages = [{"role": "user", "content": prompt}]

        try:
            response = client.chat(messages)
            test_code = _extract_code(response)
        except Exception as e:
            print(f"[QAValidator] 테스트 생성 실패 {file_path}: {e}")
            continue

        if not test_code:
            continue

        test_path = _derive_test_path(file_path)
        try:
            write_file(test_path, test_code)
            generated_tests.append(test_path)
            print(f"[QAValidator]   테스트 저장: {test_path}")
        except Exception as e:
            print(f"[QAValidator] 테스트 저장 실패 {test_path}: {e}")

    # pytest 실행
    print(f"[QAValidator] pytest 실행 중 (생성된 테스트: {len(generated_tests)}개)...")
    pytest_result = {
        "passed": 0,
        "failed": 0,
        "error": 0,
        "failed_details": [],
        "raw_output": "테스트 파일 없음",
    }

    if generated_tests:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", _TESTS_DIR, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(get_filesystem_root()),
            )
            combined_output = proc.stdout + proc.stderr
            pytest_result = _parse_pytest_output(combined_output)
            print(
                f"[QAValidator] pytest 결과: "
                f"pass={pytest_result['passed']}, "
                f"fail={pytest_result['failed']}, "
                f"error={pytest_result['error']}"
            )
        except subprocess.TimeoutExpired:
            pytest_result["raw_output"] = "pytest 타임아웃 (120초 초과)"
            pytest_result["error"] = 1
        except Exception as e:
            pytest_result["raw_output"] = f"pytest 실행 오류: {e}"
            pytest_result["error"] = 1

    # 테스트 결과 구성
    test_results = [
        {
            "test": "unit_tests",
            "status": "pass" if pytest_result["failed"] == 0 and pytest_result["error"] == 0 else "fail",
            "passed": pytest_result["passed"],
            "failed": pytest_result["failed"],
            "error": pytest_result["error"],
            "failed_details": pytest_result["failed_details"],
        }
    ]

    existing_tester = state.get("tester_output") or {}

    return {
        "tester_output": {
            **existing_tester,
            "test_results": test_results,
            "tests_written": len(generated_tests),
            "pytest_summary": {
                "passed": pytest_result["passed"],
                "failed": pytest_result["failed"],
                "error": pytest_result["error"],
            },
            "generated_test_files": generated_tests,
        }
    }
