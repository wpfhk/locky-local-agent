from __future__ import annotations
from locky.core.session import LockySession


class CommitAgent:
    """커밋 메시지 자동 생성 에이전트."""

    def __init__(self, session: LockySession) -> None:
        self.session = session

    def run(self, dry_run: bool = True, push: bool = False) -> dict:
        """git diff 기반 Conventional Commits 메시지 생성 후 커밋."""
        from actions.commit import run
        result = run(self.session.workspace, dry_run=dry_run, push=push)
        self.session.add_history({"type": "commit", "dry_run": dry_run,
                                  "message": result.get("message", "")[:100]})
        return result
