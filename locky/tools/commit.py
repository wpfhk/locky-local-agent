from pathlib import Path

from locky.tools import BaseTool, ToolResult


class CommitTool(BaseTool):
    name = "commit"
    description = "AI 커밋 메시지 생성 및 git commit"

    def run(self, root: Path, **opts) -> ToolResult:
        from actions.commit import run  # delegation

        return ToolResult.from_dict(run(root, **opts))
