"""tests/test_sandbox.py — Security sandboxing tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.sandbox.base import NoopSandbox, SandboxConfig, get_sandbox
from tools.sandbox.macos import MacOSSandbox
from tools.sandbox.linux import LinuxSandbox


# ---------------------------------------------------------------------------
# SandboxConfig tests
# ---------------------------------------------------------------------------


class TestSandboxConfig:
    def test_defaults(self):
        cfg = SandboxConfig()
        assert cfg.allowed_read == []
        assert cfg.allowed_write == []
        assert cfg.allow_network is False
        assert cfg.allow_subprocess is True

    def test_custom(self):
        cfg = SandboxConfig(
            allowed_read=[Path("/tmp")],
            allowed_write=[Path("/tmp/out")],
            allow_network=True,
            allow_subprocess=False,
        )
        assert len(cfg.allowed_read) == 1
        assert cfg.allow_network is True


# ---------------------------------------------------------------------------
# NoopSandbox tests
# ---------------------------------------------------------------------------


class TestNoopSandbox:
    def test_is_available(self):
        assert NoopSandbox().is_available() is True

    def test_passthrough(self):
        cmd = ["python", "-c", "print('hello')"]
        result = NoopSandbox().sandbox_command(cmd, SandboxConfig())
        assert result == cmd

    def test_generate_profile(self):
        profile = NoopSandbox().generate_profile(SandboxConfig())
        assert "No sandbox" in profile

    def test_platform_name(self):
        assert NoopSandbox().platform_name == "noop"


# ---------------------------------------------------------------------------
# MacOSSandbox tests
# ---------------------------------------------------------------------------


class TestMacOSSandbox:
    def test_platform_name(self):
        assert MacOSSandbox().platform_name == "macos"

    @patch("shutil.which", return_value="/usr/bin/sandbox-exec")
    def test_is_available_yes(self, _):
        assert MacOSSandbox().is_available() is True

    @patch("shutil.which", return_value=None)
    def test_is_available_no(self, _):
        assert MacOSSandbox().is_available() is False

    def test_generate_profile_basic(self):
        cfg = SandboxConfig()
        profile = MacOSSandbox().generate_profile(cfg)
        assert "(version 1)" in profile
        assert "(deny default)" in profile
        assert "Deny network" in profile

    def test_generate_profile_with_network(self):
        cfg = SandboxConfig(allow_network=True)
        profile = MacOSSandbox().generate_profile(cfg)
        assert "(allow network*)" in profile

    def test_generate_profile_read_paths(self, tmp_path):
        cfg = SandboxConfig(allowed_read=[tmp_path])
        profile = MacOSSandbox().generate_profile(cfg)
        assert str(tmp_path.resolve()) in profile
        assert "file-read*" in profile

    def test_generate_profile_write_paths(self, tmp_path):
        cfg = SandboxConfig(allowed_write=[tmp_path])
        profile = MacOSSandbox().generate_profile(cfg)
        assert "file-write*" in profile

    @patch("shutil.which", return_value="/usr/bin/sandbox-exec")
    def test_sandbox_command(self, _, tmp_path):
        cfg = SandboxConfig(allowed_read=[tmp_path])
        cmd = ["python", "-c", "print('hi')"]
        result = MacOSSandbox().sandbox_command(cmd, cfg)

        assert result[0] == "sandbox-exec"
        assert "-f" in result
        assert result[-3:] == cmd

    def test_generate_profile_subprocess(self):
        cfg = SandboxConfig(allow_subprocess=True)
        profile = MacOSSandbox().generate_profile(cfg)
        assert "(allow process-exec*)" in profile


# ---------------------------------------------------------------------------
# LinuxSandbox tests
# ---------------------------------------------------------------------------


class TestLinuxSandbox:
    def test_platform_name(self):
        assert LinuxSandbox().platform_name == "linux"

    @patch("shutil.which", return_value="/usr/bin/firejail")
    def test_is_available_yes(self, _):
        assert LinuxSandbox().is_available() is True

    @patch("shutil.which", return_value=None)
    def test_is_available_no(self, _):
        assert LinuxSandbox().is_available() is False

    @patch("shutil.which", return_value=None)
    def test_sandbox_command_unavailable(self, _):
        cmd = ["ls", "-la"]
        result = LinuxSandbox().sandbox_command(cmd, SandboxConfig())
        assert result == cmd  # passthrough

    @patch("shutil.which", return_value="/usr/bin/firejail")
    def test_sandbox_command_no_network(self, _):
        cmd = ["python", "test.py"]
        cfg = SandboxConfig(allow_network=False)
        result = LinuxSandbox().sandbox_command(cmd, cfg)
        assert result[0] == "firejail"
        assert "--net=none" in result
        assert result[-2:] == cmd

    @patch("shutil.which", return_value="/usr/bin/firejail")
    def test_sandbox_command_with_network(self, _):
        cmd = ["curl", "http://example.com"]
        cfg = SandboxConfig(allow_network=True)
        result = LinuxSandbox().sandbox_command(cmd, cfg)
        assert "--net=none" not in result

    @patch("shutil.which", return_value="/usr/bin/firejail")
    def test_sandbox_command_paths(self, _, tmp_path):
        cfg = SandboxConfig(
            allowed_read=[tmp_path],
            allowed_write=[tmp_path / "out"],
        )
        result = LinuxSandbox().sandbox_command(["ls"], cfg)
        read_args = [a for a in result if a.startswith("--read-only=")]
        write_args = [a for a in result if a.startswith("--read-write=")]
        assert len(read_args) == 1
        assert len(write_args) == 1

    def test_generate_profile(self):
        cfg = SandboxConfig(allow_network=False)
        profile = LinuxSandbox().generate_profile(cfg)
        assert "net none" in profile
        assert "caps.drop all" in profile

    def test_generate_profile_with_network(self):
        cfg = SandboxConfig(allow_network=True)
        profile = LinuxSandbox().generate_profile(cfg)
        assert "net none" not in profile


# ---------------------------------------------------------------------------
# get_sandbox factory tests
# ---------------------------------------------------------------------------


class TestGetSandbox:
    @patch("sys.platform", "darwin")
    @patch("shutil.which", return_value="/usr/bin/sandbox-exec")
    def test_macos(self, _):
        sandbox = get_sandbox()
        assert sandbox.platform_name == "macos"

    @patch("sys.platform", "linux")
    @patch("shutil.which", return_value="/usr/bin/firejail")
    def test_linux(self, _):
        sandbox = get_sandbox()
        assert sandbox.platform_name == "linux"

    @patch("sys.platform", "win32")
    def test_windows_noop(self):
        sandbox = get_sandbox()
        assert sandbox.platform_name == "noop"

    @patch("sys.platform", "darwin")
    @patch("shutil.which", return_value=None)
    def test_macos_unavailable(self, _):
        sandbox = get_sandbox()
        assert sandbox.platform_name == "noop"
