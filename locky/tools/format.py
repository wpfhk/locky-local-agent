from pathlib import Path
from locky.tools import BaseTool, ToolResult


class FormatTool(BaseTool):
    name = "format"
    description = "다언어 코드 포매터 (black, prettier, gofmt 등)"

    def run(self, root: Path, **opts) -> ToolResult:
        from actions.format_code import run  # delegation
        return ToolResult.from_dict(run(root, **opts))
