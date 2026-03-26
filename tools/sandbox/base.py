"""tools/sandbox/base.py — Sandbox ABC and factory."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""

    allowed_read: list[Path] = field(default_factory=list)
    allowed_write: list[Path] = field(default_factory=list)
    allow_network: bool = False
    allow_subprocess: bool = True


class SandboxBase(ABC):
    """Abstract base for OS-specific sandbox implementations."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this sandbox is available on the current system."""
        ...

    @abstractmethod
    def sandbox_command(
        self, cmd: list[str], config: SandboxConfig
    ) -> list[str]:
        """Wrap a command with sandbox restrictions.

        Args:
            cmd: Original command to execute
            config: Sandbox configuration

        Returns:
            Modified command list with sandbox wrapper
        """
        ...

    @abstractmethod
    def generate_profile(self, config: SandboxConfig) -> str:
        """Generate sandbox policy/profile content.

        Args:
            config: Sandbox configuration

        Returns:
            Policy file content as string
        """
        ...

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g., 'macos', 'linux')."""
        ...


class NoopSandbox(SandboxBase):
    """No-op sandbox for unsupported platforms."""

    def is_available(self) -> bool:
        return True

    def sandbox_command(
        self, cmd: list[str], config: SandboxConfig
    ) -> list[str]:
        return cmd  # passthrough

    def generate_profile(self, config: SandboxConfig) -> str:
        return "# No sandbox available on this platform"

    @property
    def platform_name(self) -> str:
        return "noop"


def get_sandbox() -> SandboxBase:
    """Factory: return the appropriate sandbox for the current OS.

    Returns:
        MacOSSandbox on macOS, LinuxSandbox on Linux, NoopSandbox otherwise
    """
    if sys.platform == "darwin":
        from .macos import MacOSSandbox

        sandbox = MacOSSandbox()
        if sandbox.is_available():
            return sandbox

    elif sys.platform.startswith("linux"):
        from .linux import LinuxSandbox

        sandbox = LinuxSandbox()
        if sandbox.is_available():
            return sandbox

    return NoopSandbox()
