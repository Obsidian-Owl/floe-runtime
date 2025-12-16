# Research: CLI Interface

**Feature**: 002-cli-interface
**Date**: 2025-12-16

## Summary

Research conducted on Click, Rich, and Jinja2 patterns for implementing floe-cli. All findings aligned with Constitution principles (standalone-first, type safety, security-first).

---

## 1. Click CLI Patterns

### Decision: Use rich-click for enhanced help formatting

**Rationale**: rich-click is a drop-in replacement for Click that provides beautiful Rich-formatted help without code changes. It's actively maintained and used by major projects.

**Alternatives Considered**:
- Plain Click: Works but lacks visual polish
- Custom Rich integration: More work, same result

### Decision: Use LazyGroup for fast --help performance

**Rationale**: LazyGroup loads commands only when invoked, not at import time. This ensures `floe --help` < 500ms even with heavy dependencies.

**Code Pattern**:
```python
class LazyGroup(click.Group):
    """Load commands lazily for fast --help."""

    def __init__(self, *args, lazy_subcommands=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazy_subcommands = lazy_subcommands or {}

    def list_commands(self, ctx):
        return sorted(self.lazy_subcommands.keys())

    def get_command(self, ctx, cmd_name):
        if cmd_name not in self.lazy_subcommands:
            return None
        module_path = self.lazy_subcommands[cmd_name]
        module_name, attr_name = module_path.rsplit(".", 1)
        mod = importlib.import_module(module_name)
        return getattr(mod, attr_name)
```

### Decision: Options over Arguments

**Rationale**: Click documentation recommends "use arguments exclusively for things like going to subcommands or input filenames / URLs, and have everything else be an option."

**Pattern**: Use `--file` not positional argument for floe.yaml path

---

## 2. Rich Terminal Patterns

### Decision: Use Console for all output

**Rationale**: Rich Console handles NO_COLOR, FORCE_COLOR, TTY detection automatically.

**Code Pattern**:
```python
from rich.console import Console

console = Console()  # Auto-detects terminal capabilities

# Success
console.print("[green]✓[/green] Validation successful", style="bold")

# Error
console.print("[red]✗[/red] Validation failed", style="bold red")

# Warning
console.print("[yellow]⚠[/yellow] Warning: deprecated option", style="yellow")
```

### Decision: Use console.status() for spinners

**Rationale**: Better UX than progress bars for operations with unknown duration.

**Code Pattern**:
```python
with console.status("[bold green]Compiling...", spinner="dots"):
    artifacts = compiler.compile(spec_path)
```

### Decision: Support NO_COLOR environment variable

**Rationale**: Standard convention for CI/CD and accessibility.

**Implementation**: Rich handles this automatically; add explicit `--no-color` flag for override.

---

## 3. Jinja2 Template Patterns

### Decision: Use SandboxedEnvironment for template rendering

**Rationale**: Constitution Principle V (Security First) requires preventing code injection. SandboxedEnvironment blocks access to `__code__`, `__globals__`, etc.

**Code Pattern**:
```python
from jinja2.sandbox import SandboxedEnvironment

env = SandboxedEnvironment(
    loader=PackageTemplateLoader("floe_cli", "templates"),
    trim_blocks=True,
    lstrip_blocks=True,
)
```

### Decision: Use importlib.resources for template loading

**Rationale**: Modern API (pkg_resources deprecated), works with zip files, PyInstaller.

**Code Pattern**:
```python
from importlib.resources import files

def get_template(name: str) -> str:
    template_files = files("floe_cli") / "templates"
    return (template_files / name).read_text()
```

### Decision: Validate all template context with Pydantic

**Rationale**: Prevent injection attacks by validating before rendering.

**Code Pattern**:
```python
class TemplateContext(BaseModel):
    project_name: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")

    @field_validator("project_name")
    @classmethod
    def validate_no_path_traversal(cls, v: str) -> str:
        if ".." in v or "/" in v:
            raise ValueError("Invalid project name")
        return v
```

---

## 4. Error Handling Patterns

### Decision: Wrap FloeError from floe-core

**Rationale**: Don't duplicate exception hierarchy. CLI adds context but delegates to core.

**Code Pattern**:
```python
from floe_core import FloeError, ValidationError, CompilationError

@cli.command()
def validate(file: Path):
    try:
        FloeSpec.from_yaml(file)
        console.print("[green]✓[/green] Valid")
    except ValidationError as e:
        console.print(f"[red]✗[/red] {e.user_message}")
        raise SystemExit(1)
```

### Decision: Exit codes follow sysexits.h convention

**Rationale**: Standard Unix convention for programmatic use.

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (validation, compilation) |
| 2 | Usage error (bad arguments, file not found) |

---

## 5. Testing Patterns

### Decision: Use click.testing.CliRunner with isolated_filesystem

**Rationale**: Clean test isolation, handles temp directories automatically.

**Code Pattern**:
```python
from click.testing import CliRunner

def test_validate_success():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("floe.yaml").write_text("name: test\nversion: 1.0.0\n...")
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 0
        assert "✓" in result.output
```

### Decision: Test with catch_exceptions=False for debugging

**Rationale**: Propagate exceptions during test development for better stack traces.

---

## 6. Dependencies

### Required (pyproject.toml):
```toml
dependencies = [
    "click>=8.1",
    "rich>=13.9",
    "rich-click>=1.7",
    "jinja2>=3.1",
    "floe-core",
]
```

### Why not typer?
- Typer is Click-based but adds unnecessary abstraction
- rich-click provides same benefits with less lock-in
- Direct Click usage aligns with floe-core patterns

---

## Constitution Alignment

| Principle | Alignment |
|-----------|-----------|
| I. Standalone-First | ✅ No SaaS dependencies, offline operation |
| II. Type Safety | ✅ All commands typed, Pydantic validation |
| III. Technology Ownership | ✅ CLI owns interface, delegates to floe-core |
| IV. Contract-Driven | ✅ Uses CompiledArtifacts, JSON Schema export |
| V. Security First | ✅ SandboxedEnvironment, input validation |
| VI. Quality Standards | ✅ >80% coverage target, Black/isort/ruff |
