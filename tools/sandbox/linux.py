"""tools/sandbox/linux.py — Linux seccomp sandbox (placeholder)."""

from __future__ import annotations

import logging
import shutil

from .base import SandboxBase, SandboxConfig

logger = logging.getLogger(__name__)


class LinuxSandbox(SandboxBase):
    """Linux sandbox using seccomp-bpf (placeholder implementation).

    Full seccomp integration requires python-prctl or libseccomp bindings.
    This placeholder wraps commands with firejail if available,
    otherwise returns the command unchanged with a warning.
    """

    def is_available(self) -> bool:
        """Check if firejail is available as a sandboxing tool."""
        return shutil.which("firejail") is not None

    def sandbox_command(
        self, cmd: list[str], config: SandboxConfig
    ) -> list[str]:
        """Wrap command with firejail if available.

        Args:
            cmd: Original command
            config: Sandbox configuration

        Returns:
            Firejail-wrapped command or original command with warning
        """
        if not self.is_available():
            logger.warning(
                "Linux sandbox (firejail) not available. "
                "Running command without sandboxing."
            )
            return cmd

        firejail_args = ["firejail", "--quiet"]

        # Network restriction
        if not config.allow_network:
            firejail_args.append("--net=none")

        # Read-only paths
        for path in config.allowed_read:
            firejail_args.append(f"--read-only={path.resolve()}")

        # Writable paths
        for path in config.allowed_write:
            firejail_args.append(f"--read-write={path.resolve()}")

        # No subprocess forking restriction (firejail handles this differently)

        return firejail_args + ["--"] + cmd

    def generate_profile(self, config: SandboxConfig) -> str:
        """Generate a firejail profile.

        Args:
            config: Sandbox configuration

        Returns:
            Firejail profile content
        """
        lines = [
            "# Locky sandbox profile for firejail",
            "# Auto-generated — do not edit",
            "",
            "# Restrict capabilities",
            "caps.drop all",
            "",
        ]

        if not config.allow_network:
            lines.append("# Deny network")
            lines.append("net none")
            lines.append("")

        if not config.allow_subprocess:
            lines.append("# Restrict new process creation")
            lines.append("nonewprivs")
            lines.append("")

        for path in config.allowed_read:
            lines.append(f"read-only {path.resolve()}")

        for path in config.allowed_write:
            lines.append(f"read-write {path.resolve()}")

        return "\n".join(lines) + "\n"

    @property
    def platform_name(self) -> str:
        return "linux"
