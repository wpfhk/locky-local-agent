"""tests/test_plugin_registry.py — Plugin registry tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.plugins.manifest import PluginCommand, PluginManifest
from tools.plugins.registry import PluginRegistry


def _make_manifest(name="test-plugin", commands=None, hooks=None, plugin_path=None):
    return PluginManifest(
        name=name,
        version="1.0.0",
        commands=commands or [],
        hooks=hooks or {},
        plugin_path=plugin_path,
    )


class TestPluginRegistry:
    def test_register_empty(self):
        reg = PluginRegistry()
        reg.register(_make_manifest())
        assert len(reg.list_plugins()) == 1

    def test_register_duplicate(self):
        reg = PluginRegistry()
        reg.register(_make_manifest())
        with pytest.raises(ValueError, match="already registered"):
            reg.register(_make_manifest())

    def test_unregister(self):
        reg = PluginRegistry()
        reg.register(_make_manifest("plugin-a"))
        assert reg.unregister("plugin-a")
        assert len(reg.list_plugins()) == 0

    def test_unregister_not_found(self):
        reg = PluginRegistry()
        assert not reg.unregister("missing")

    def test_get_command(self):
        reg = PluginRegistry()
        cmd_func = MagicMock()

        with patch.object(reg._loader, "import_entry", return_value=cmd_func):
            manifest = _make_manifest(
                commands=[PluginCommand(name="lint", entry="mod:run")]
            )
            reg.register(manifest)

        assert reg.get_command("lint") is cmd_func

    def test_get_command_not_found(self):
        reg = PluginRegistry()
        assert reg.get_command("missing") is None

    def test_list_commands(self):
        reg = PluginRegistry()
        cmd_func = MagicMock()

        with patch.object(reg._loader, "import_entry", return_value=cmd_func):
            manifest = _make_manifest(
                name="my-plugin",
                commands=[PluginCommand(name="fmt", entry="mod:fmt")],
            )
            reg.register(manifest)

        cmds = reg.list_commands()
        assert cmds == {"fmt": "my-plugin"}

    def test_unregister_removes_commands(self):
        reg = PluginRegistry()
        cmd_func = MagicMock()

        with patch.object(reg._loader, "import_entry", return_value=cmd_func):
            manifest = _make_manifest(
                commands=[PluginCommand(name="lint", entry="mod:run")]
            )
            reg.register(manifest)

        assert reg.get_command("lint") is not None
        reg.unregister("test-plugin")
        assert reg.get_command("lint") is None

    def test_on_load_hook_called(self):
        reg = PluginRegistry()
        hook_func = MagicMock()

        with patch.object(reg._loader, "import_entry", return_value=hook_func):
            manifest = _make_manifest(hooks={"on_load": "hooks:init"})
            reg.register(manifest)

        hook_func.assert_called_once()

    def test_on_unload_hook_called(self):
        reg = PluginRegistry()
        hook_func = MagicMock()

        with patch.object(reg._loader, "import_entry", return_value=hook_func):
            manifest = _make_manifest(hooks={"on_unload": "hooks:cleanup"})
            reg.register(manifest)

        # on_load wasn't defined, so hook_func shouldn't be called yet
        # Now unregister
        with patch.object(reg._loader, "import_entry", return_value=hook_func):
            reg.unregister("test-plugin")

        hook_func.assert_called()

    def test_load_all(self, tmp_path):
        p = tmp_path / "my-plugin"
        p.mkdir()
        (p / "plugin.yaml").write_text(
            "name: my-plugin\nversion: 1.0.0\ncommands: []\n"
        )

        reg = PluginRegistry()
        results = reg.load_all(tmp_path)
        assert "my-plugin" in results
        assert results["my-plugin"] is None  # success
        assert len(reg.list_plugins()) == 1

    def test_load_all_invalid_plugin(self, tmp_path):
        p = tmp_path / "bad-plugin"
        p.mkdir()
        (p / "plugin.yaml").write_text("name: BAD\nversion: x")

        reg = PluginRegistry()
        results = reg.load_all(tmp_path)
        assert "bad-plugin" in results
        assert results["bad-plugin"] is not None  # error message

    def test_load_all_multiple_dirs(self, tmp_path):
        d1 = tmp_path / "dir1"
        d1.mkdir()
        p1 = d1 / "plugin-a"
        p1.mkdir()
        (p1 / "plugin.yaml").write_text("name: plugin-a\nversion: 1.0.0\n")

        d2 = tmp_path / "dir2"
        d2.mkdir()
        p2 = d2 / "plugin-b"
        p2.mkdir()
        (p2 / "plugin.yaml").write_text("name: plugin-b\nversion: 1.0.0\n")

        reg = PluginRegistry()
        results = reg.load_all(d1, d2)
        assert len(results) == 2
        assert len(reg.list_plugins()) == 2

    def test_import_failure_logged(self):
        reg = PluginRegistry()
        manifest = _make_manifest(
            commands=[PluginCommand(name="bad", entry="nonexistent:func")]
        )
        # Should not raise, just log warning
        reg.register(manifest)
        assert reg.get_command("bad") is None  # import failed
