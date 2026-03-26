# Locky v3 Phase 3: Extensibility — Design v0.0.1

> Date: 2026-03-26
> Architecture: Option C (Pragmatic Balance)

---

## 1. Plugin System v2

### 1.1 Manifest Schema (`plugin.yaml`)

```yaml
name: my-plugin          # required, kebab-case
version: 1.0.0           # required, semver
description: "Short desc"
author: "Name"
commands:
  - name: lint           # CLI subcommand name
    description: "Run custom linter"
    entry: my_plugin.lint:run   # module.path:function
hooks:
  on_load: my_plugin.hooks:on_load       # optional lifecycle
  on_unload: my_plugin.hooks:on_unload   # optional lifecycle
```

### 1.2 Module Design

```
tools/plugins/
├── __init__.py
├── manifest.py    # PluginManifest dataclass, validate_manifest(), load_manifest()
├── loader.py      # PluginLoader: discover plugins, import entry points
└── registry.py    # PluginRegistry: register/unregister, get_command
```

**PluginManifest** (dataclass):
- `name: str`, `version: str`, `description: str`, `author: str`
- `commands: list[PluginCommand]` where PluginCommand = {name, description, entry}
- `hooks: dict[str, str]` — lifecycle hook entry points

**PluginLoader**:
- `discover(plugins_dir) -> list[Path]` — find dirs with plugin.yaml
- `load(plugin_path) -> PluginManifest` — parse + validate manifest
- `import_entry(entry_str) -> Callable` — dynamic import "module:func"

**PluginRegistry**:
- `register(manifest, plugin_path)` — add to registry
- `unregister(name)` — remove + call on_unload hook
- `get_command(name) -> Callable | None`
- `list_plugins() -> list[PluginManifest]`
- `load_all(plugins_dir)` — discover + load + register all

### 1.3 Discovery Paths

1. `~/.locky/plugins/*/plugin.yaml` (global)
2. `.locky/plugins/*/plugin.yaml` (project-local)

---

## 2. Recipes

### 2.1 Recipe Schema

```yaml
name: PR Ready Check
description: PR submission readiness pipeline
version: "1.0"
steps:
  - action: format
    args: {check: true}
  - action: test
  - action: scan
    args: {severity_filter: high}
  - action: deps
  - action: commit
    args: {dry_run: true}
fail_fast: true   # default: true
```

### 2.2 Module Design

```
tools/recipes/
├── __init__.py
├── parser.py     # Recipe dataclass, parse_recipe(), validate_recipe()
└── runner.py     # RecipeRunner: execute recipe steps via actions/
```

**Recipe** (dataclass):
- `name: str`, `description: str`, `version: str`
- `steps: list[RecipeStep]` where RecipeStep = {action, args}
- `fail_fast: bool`

**RecipeRunner**:
- `run(recipe, root) -> dict` — execute steps sequentially, return pipeline-style result
- `list_recipes(dirs) -> list[Recipe]` — discover from paths

### 2.3 Discovery Paths

1. `~/.locky/recipes/*.yaml`
2. `.locky/recipes/*.yaml`

---

## 3. MCP Server Export

### 3.1 Design

`tools/mcp/server.py` implements JSON-RPC 2.0 over stdio, exposing locky actions as MCP tools.

**Exposed Tools**:
| MCP Tool Name | Action | Input Schema |
|--------------|--------|-------------|
| `locky_format` | format_code.run | `{root, check, lang}` |
| `locky_scan` | security_scan.run | `{root, severity}` |
| `locky_test` | test_runner.run | `{root, path, verbose}` |
| `locky_deps` | deps_check.run | `{root}` |

**Protocol**:
- `initialize` → server info + capabilities
- `tools/list` → tool definitions
- `tools/call` → execute action, return result

### 3.2 CLI

```bash
locky serve-mcp   # starts MCP stdio server
```

---

## 4. Security Sandboxing

### 4.1 Architecture

```
tools/sandbox/
├── __init__.py
├── base.py       # SandboxBase ABC, SandboxConfig, get_sandbox()
├── macos.py      # MacOSSandbox — seatbelt profile generation
└── linux.py      # LinuxSandbox — seccomp-bpf (placeholder)
```

**SandboxBase** (ABC):
- `sandbox_command(cmd, allowed_paths, network) -> list[str]` — wrap command with sandbox
- `is_available() -> bool` — check OS support
- `generate_profile(config) -> str` — generate policy file content

**get_sandbox()** — factory returning MacOSSandbox/LinuxSandbox/None based on `sys.platform`

### 4.2 macOS seatbelt

Generates a `.sb` profile:
- Allow read/write to specified paths only
- Allow/deny network access
- Allow subprocess execution within sandbox

### 4.3 Linux seccomp

Placeholder implementation. Returns unsandboxed command with warning.

---

## 5. Web UI (TUI)

### 5.1 Design

`ui/tui.py` provides a Rich-based TUI dashboard (no textual dependency required for basic mode).

**Features**:
- Status panel: git status, last commit, active session
- Action runner: select and run locky actions
- Output viewer: action results in Rich panels

**Fallback**: If `textual` not installed, uses `rich.console` interactive prompts.

---

## 6. CLI Commands (Phase 3 additions)

| Command | Description |
|---------|------------|
| `locky recipe run <name>` | Execute a recipe |
| `locky recipe list` | List available recipes |
| `locky serve-mcp` | Start MCP stdio server |
| `locky plugin list` | (enhanced) Show v2 plugins with manifest info |
