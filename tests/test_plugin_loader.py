"""tests/test_plugin_loader.py — Plugin loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.plugins.loader import PluginLoader


class TestPluginDiscover:
    def test_empty_dir(self, tmp_path):
        assert PluginLoader.discover(tmp_path) == []

    def test_nonexistent_dir(self, tmp_path):
        assert PluginLoader.discover(tmp_path / "missing") == []

    def test_discovers_manifests(self, tmp_path):
        p1 = tmp_path / "plugin-a"
        p1.mkdir()
        (p1 / "plugin.yaml").write_text("name: plugin-a\nversion: 1.0.0")

        p2 = tmp_path / "plugin-b"
        p2.mkdir()
        (p2 / "plugin.yaml").write_text("name: plugin-b\nversion: 1.0.0")

        # Dir without manifest — should be skipped
        p3 = tmp_path / "no-manifest"
        p3.mkdir()

        results = PluginLoader.discover(tmp_path)
        assert len(results) == 2
        assert all(r.name == "plugin.yaml" for r in results)

    def test_ignores_files(self, tmp_path):
        (tmp_path / "not-a-dir.yaml").write_text("something")
        assert PluginLoader.discover(tmp_path) == []

    def test_sorted_order(self, tmp_path):
        for name in ["z-plugin", "a-plugin", "m-plugin"]:
            d = tmp_path / name
            d.mkdir()
            (d / "plugin.yaml").write_text(f"name: {name}\nversion: 1.0.0")

        results = PluginLoader.discover(tmp_path)
        names = [r.parent.name for r in results]
        assert names == ["a-plugin", "m-plugin", "z-plugin"]


class TestPluginLoad:
    def test_load_valid(self, tmp_path):
        (tmp_path / "plugin.yaml").write_text("name: test-plugin\nversion: 1.0.0")
        manifest = PluginLoader.load(tmp_path / "plugin.yaml")
        assert manifest.name == "test-plugin"

    def test_load_invalid(self, tmp_path):
        (tmp_path / "plugin.yaml").write_text("name: BAD\nversion: x")
        with pytest.raises(ValueError):
            PluginLoader.load(tmp_path / "plugin.yaml")


class TestPluginImportEntry:
    def test_import_builtin(self):
        func = PluginLoader.import_entry("os.path:exists")
        assert callable(func)

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid entry format"):
            PluginLoader.import_entry("no_colon_here")

    def test_module_not_found(self):
        with pytest.raises(ImportError):
            PluginLoader.import_entry("nonexistent_module_xyz:func")

    def test_function_not_found(self):
        with pytest.raises(ImportError, match="Function"):
            PluginLoader.import_entry("os.path:nonexistent_func_xyz")

    def test_import_from_plugin_path(self, tmp_path):
        # Create a module in plugin path
        (tmp_path / "my_mod.py").write_text("def hello():\n    return 'world'\n")
        func = PluginLoader.import_entry("my_mod:hello", plugin_path=tmp_path)
        assert func() == "world"

    def test_sys_path_cleanup(self, tmp_path):
        import sys

        (tmp_path / "cleanup_test.py").write_text("def fn(): pass\n")
        before = str(tmp_path) in sys.path

        PluginLoader.import_entry("cleanup_test:fn", plugin_path=tmp_path)

        after = str(tmp_path) in sys.path
        assert before == after  # Should be cleaned up
