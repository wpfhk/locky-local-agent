"""actions/commit.py — git diff를 읽어 Ollama로 커밋 메시지를 생성하고 커밋합니다."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def run(root: Path, dry_run: bool = False, push: bool = False) -> dict:
    """
    git diff를 읽어 Ollama로 Conventional Commits 형식 메시지를 생성하고 커밋합니다.

    Args:
        root: 프로젝트 루트 Path
        dry_run: True면 메시지만 출력하고 커밋하지 않음
        push: True면 커밋 후 push까지 수행

    Returns:
        {"status": "ok"|"error"|"nothing_to_commit", "message": str, "committed_files": [...]}
    """
    root = Path(root).resolve()

    try:
        # 현재 상태 확인
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if status_result.returncode != 0:
            return {
                "status": "error",
                "message": f"git status 실패: {status_result.stderr.strip()}",
                "committed_files": [],
            }

        status_lines = status_result.stdout.strip().splitlines()
        if not status_lines:
            return {
                "status": "nothing_to_commit",
                "message": "커밋할 변경 사항이 없습니다.",
                "committed_files": [],
            }

        # staged 파일 확인
        staged_result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        staged_files: List[str] = [
            f for f in staged_result.stdout.strip().splitlines() if f
        ]

        # staged 파일이 없으면 modified 파일 자동 stage
        if not staged_files:
            has_tracked_changes = any(
                line and not line.startswith("??") for line in status_lines
            )
            has_untracked = any(line.startswith("??") for line in status_lines)

            if not has_tracked_changes and not has_untracked:
                return {
                    "status": "nothing_to_commit",
                    "message": "커밋할 변경 사항이 없습니다.",
                    "committed_files": [],
                }

            # tracked 변경 파일(수정·삭제·rename 포함)은 git add -u로 일괄 스테이지
            # untracked 파일만 있는 경우 git add .으로 처리
            if has_tracked_changes:
                add_result = subprocess.run(
                    ["git", "add", "-u"],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            else:
                add_result = subprocess.run(
                    ["git", "add", "."],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            if add_result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"git add 실패: {add_result.stderr.strip()}",
                    "committed_files": [],
                }
            # git add 이후 실제 staged 파일 목록 재조회
            staged_result2 = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            staged_files = [f for f in staged_result2.stdout.strip().splitlines() if f]

        # diff 내용 가져오기
        diff_result = subprocess.run(
            ["git", "diff", "--cached"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        diff_text = diff_result.stdout.strip()

        # Ollama로 커밋 메시지 생성
        commit_message = _generate_commit_message(diff_text, staged_files)

        if dry_run:
            return {
                "status": "ok",
                "message": commit_message,
                "committed_files": staged_files,
                "dry_run": True,
            }

        # 커밋 실행
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if commit_result.returncode != 0:
            return {
                "status": "error",
                "message": f"git commit 실패: {commit_result.stderr.strip()}",
                "committed_files": staged_files,
            }

        # push 옵션
        if push:
            push_result = subprocess.run(
                ["git", "push"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if push_result.returncode != 0:
                return {
                    "status": "ok",
                    "message": commit_message,
                    "committed_files": staged_files,
                    "push_error": push_result.stderr.strip(),
                }

        return {
            "status": "ok",
            "message": commit_message,
            "committed_files": staged_files,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "git 명령 타임아웃",
            "committed_files": [],
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "committed_files": [],
        }


def _generate_commit_message(diff_text: str, staged_files: List[str]) -> str:
    """Ollama를 사용하여 Conventional Commits 형식의 커밋 메시지를 생성합니다."""
    try:
        import httpx

        from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

        # Ollama 서버 헬스체크 (미기동 시 자동 시작 시도)
        try:
            from tools.ollama_guard import ensure_ollama

            ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL)
        except Exception:
            pass  # guard 실패 시 그대로 진행 (기존 오류 처리에 위임)

        # diff가 너무 길면 자름
        max_diff_len = 4000
        if len(diff_text) > max_diff_len:
            diff_text = diff_text[:max_diff_len] + "\n... (truncated)"

        files_summary = ", ".join(staged_files[:10])
        if len(staged_files) > 10:
            files_summary += f" 외 {len(staged_files) - 10}개"

        prompt = (
            "다음 git diff를 보고 Conventional Commits 형식의 커밋 메시지를 작성하세요.\n"
            "형식: <type>(<scope>): <description>\n"
            "type: feat, fix, docs, style, refactor, test, chore 중 하나\n"
            "scope: 변경된 모듈/파일명 (선택)\n"
            "description: 변경 내용을 간결하게 (한국어 또는 영어)\n"
            "메시지만 한 줄로 출력하세요. 설명 없이.\n\n"
            f"변경된 파일: {files_summary}\n\n"
            f"diff:\n{diff_text}"
        )

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            message = data["message"]["content"].strip()
            # 첫 줄만 사용
            message = message.splitlines()[0].strip() if message else ""
            if message:
                return message

    except Exception:
        pass

    # Ollama 실패 시 기본 메시지
    files_part = staged_files[0] if staged_files else "files"
    if len(staged_files) > 1:
        files_part = f"{staged_files[0]} 외 {len(staged_files) - 1}개"
    return f"chore: update {files_part}"
