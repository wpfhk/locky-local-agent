from typing import List, Optional

from git import InvalidGitRepositoryError, Repo

from locky_cli.fs_context import get_filesystem_root


def _get_repo() -> Repo:
    """현재 MCP 파일시스템 루트 기준 Git 저장소 인스턴스를 반환합니다."""
    root = str(get_filesystem_root())
    try:
        return Repo(root, search_parent_directories=True)
    except InvalidGitRepositoryError:
        raise RuntimeError(f"'{root}'에서 유효한 Git 저장소를 찾을 수 없습니다.")


def get_status() -> dict:
    """
    현재 저장소의 변경 파일 목록을 반환합니다.

    Returns:
        {
            "staged": List[str],      # 스테이징된 파일
            "unstaged": List[str],    # 수정됐지만 스테이징되지 않은 파일
            "untracked": List[str],   # 추적되지 않는 새 파일
        }
    """
    repo = _get_repo()
    staged = [item.a_path for item in repo.index.diff("HEAD")]
    unstaged = [item.a_path for item in repo.index.diff(None)]
    untracked = repo.untracked_files
    return {
        "staged": staged,
        "unstaged": unstaged,
        "untracked": list(untracked),
    }


def get_diff(filepath: Optional[str] = None) -> str:
    """
    변경 사항의 diff 문자열을 반환합니다.

    Args:
        filepath: 특정 파일 경로 (None이면 전체 diff)

    Returns:
        diff 문자열
    """
    repo = _get_repo()
    if filepath:
        return repo.git.diff(filepath)
    return repo.git.diff()


def stage_files(files: List[str]) -> bool:
    """
    파일 목록을 스테이징 영역에 추가합니다.

    Args:
        files: 스테이징할 파일 경로 목록

    Returns:
        성공 시 True
    """
    repo = _get_repo()
    repo.index.add(files)
    return True


def commit(message: str) -> str:
    """
    스테이징된 변경 사항을 커밋합니다.

    Args:
        message: 커밋 메시지

    Returns:
        생성된 커밋의 해시 문자열
    """
    repo = _get_repo()
    commit_obj = repo.index.commit(message)
    return commit_obj.hexsha


def get_log(n: int = 10) -> List[dict]:
    """
    최근 커밋 로그를 반환합니다.

    Args:
        n: 반환할 커밋 수

    Returns:
        커밋 정보 딕셔너리 목록.
        각 항목: {"hash": str, "author": str, "date": str, "message": str}
    """
    repo = _get_repo()
    logs: List[dict] = []
    for commit_obj in repo.iter_commits(max_count=n):
        logs.append(
            {
                "hash": commit_obj.hexsha,
                "author": str(commit_obj.author),
                "date": commit_obj.committed_datetime.isoformat(),
                "message": commit_obj.message.strip(),
            }
        )
    return logs
