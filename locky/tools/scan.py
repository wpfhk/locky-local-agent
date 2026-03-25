from pathlib import Path
from locky.tools import BaseTool, ToolResult


class ScanTool(BaseTool):
    name = "scan"
    description = "OWASP 패턴 기반 보안 스캔"

    def run(self, root: Path, **opts) -> ToolResult:
        from actions.security_scan import run  # delegation
        return ToolResult.from_dict(run(root, **opts))
