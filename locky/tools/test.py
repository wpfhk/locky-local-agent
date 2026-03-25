from pathlib import Path

from locky.tools import BaseTool, ToolResult


class TestTool(BaseTool):
    name = "test"
    description = "pytest 테스트 실행"

    def run(self, root: Path, **opts) -> ToolResult:
        from actions.test_runner import run  # delegation

        return ToolResult.from_dict(run(root, **opts))
