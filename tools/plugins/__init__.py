"""tools/plugins/ — Declarative plugin system v2 (Phase 3)."""

from .loader import PluginLoader
from .manifest import PluginCommand, PluginManifest, load_manifest, validate_manifest
from .registry import PluginRegistry

__all__ = [
    "PluginManifest",
    "PluginCommand",
    "load_manifest",
    "validate_manifest",
    "PluginLoader",
    "PluginRegistry",
]
