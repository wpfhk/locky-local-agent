"""tools/sandbox/macos.py — macOS seatbelt sandbox."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .base import SandboxBase, SandboxConfig


class MacOSSandbox(SandboxBase):
    """macOS sandbox using sandbox-exec (seatbelt profiles)."""

    def is_available(self) -> bool:
        """Check if sandbox-exec is available."""
        return shutil.which("sandbox-exec") is not None

    def sandbox_command(
        self, cmd: list[str], config: SandboxConfig
    ) -> list[str]:
        """Wrap command with sandbox-exec.

        Args:
            cmd: Original command
            config: Sandbox configuration

        Returns:
            ['sandbox-exec', '-f', profile_path] + cmd
        """
        profile_content = self.generate_profile(config)

        # Write profile to temp file
        profile_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".sb",
            prefix="locky-sandbox-",
            delete=False,
        )
        profile_file.write(profile_content)
        profile_file.close()

        return ["sandbox-exec", "-f", profile_file.name] + cmd

    def generate_profile(self, config: SandboxConfig) -> str:
        """Generate a seatbelt (.sb) profile.

        Args:
            config: Sandbox configuration

        Returns:
            Seatbelt profile as string
        """
        lines = [
            "(version 1)",
            "(deny default)",
            "",
            "; Allow basic process execution",
            "(allow process-exec)",
            "(allow process-fork)",
            "(allow sysctl-read)",
            "(allow mach-lookup)",
            "",
            "; Allow reading system libraries and frameworks",
            '(allow file-read* (subpath "/usr/lib"))',
            '(allow file-read* (subpath "/usr/share"))',
            '(allow file-read* (subpath "/System"))',
            '(allow file-read* (subpath "/Library/Frameworks"))',
            '(allow file-read* (subpath "/usr/local"))',
            "",
            "; Allow temp directory access",
            '(allow file-read* (subpath "/tmp"))',
            '(allow file-write* (subpath "/tmp"))',
            '(allow file-read* (subpath "/private/tmp"))',
            '(allow file-write* (subpath "/private/tmp"))',
            "",
            "; Allow /dev access",
            '(allow file-read* (subpath "/dev"))',
            '(allow file-write* (subpath "/dev/null"))',
            '(allow file-write* (subpath "/dev/tty"))',
        ]

        # Read paths
        for path in config.allowed_read:
            resolved = str(path.resolve())
            lines.append(f'(allow file-read* (subpath "{resolved}"))')

        # Write paths
        for path in config.allowed_write:
            resolved = str(path.resolve())
            lines.append(f'(allow file-read* (subpath "{resolved}"))')
            lines.append(f'(allow file-write* (subpath "{resolved}"))')

        # Network
        if config.allow_network:
            lines.append("")
            lines.append("; Allow network access")
            lines.append("(allow network*)")
        else:
            lines.append("")
            lines.append("; Deny network access")

        # Subprocess
        if config.allow_subprocess:
            lines.append("")
            lines.append("; Allow subprocess execution")
            lines.append("(allow process-exec*)")

        return "\n".join(lines) + "\n"

    @property
    def platform_name(self) -> str:
        return "macos"
