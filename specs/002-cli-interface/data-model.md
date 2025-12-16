# Data Model: CLI Interface

**Feature**: 002-cli-interface
**Date**: 2025-12-16

## Overview

The CLI interface is a thin layer that transforms user commands into floe-core operations. It does not introduce new domain entities but defines command structures and validation rules for user input.

## CLI Command Structure

### Root Command: `floe`

```text
floe [OPTIONS] COMMAND [ARGS]

Options:
  --version     Show version and exit
  --no-color    Disable colored output
  --help        Show help and exit

Commands:
  validate      Validate floe.yaml configuration
  compile       Generate CompiledArtifacts JSON
  init          Scaffold a new project
  run           Execute pipeline via Dagster (P3)
  dev           Start development environment (P3)
  schema        JSON Schema operations
```

### Command: `floe validate`

```text
floe validate [OPTIONS]

Options:
  -f, --file PATH    Path to floe.yaml (default: ./floe.yaml)
  --help             Show help and exit

Exit Codes:
  0    Configuration is valid
  1    Configuration is invalid (schema violations)
  2    File not found or unreadable
```

### Command: `floe compile`

```text
floe compile [OPTIONS]

Options:
  -f, --file PATH      Path to floe.yaml (default: ./floe.yaml)
  -o, --output PATH    Output directory (default: .floe/)
  -t, --target TEXT    Compute target to compile for (must exist in spec)
  --help               Show help and exit

Exit Codes:
  0    Compilation successful
  1    Validation failed
  2    Compilation failed
  3    Target not found in spec
```

### Command: `floe init`

```text
floe init [OPTIONS]

Options:
  -n, --name TEXT      Project name (default: directory name)
  -t, --target TEXT    Compute target (default: duckdb)
  --force              Overwrite existing files
  --help               Show help and exit

Exit Codes:
  0    Project initialized
  1    File already exists (without --force)
  2    Write permission denied
```

### Command: `floe schema`

```text
floe schema COMMAND [OPTIONS]

Commands:
  export    Export JSON Schema

floe schema export [OPTIONS]

Options:
  -o, --output PATH    Output file path (default: stdout)
  --type TEXT          Schema type: floe-spec | compiled-artifacts (default: floe-spec)
  --help               Show help and exit

Exit Codes:
  0    Schema exported
  1    Invalid schema type
  2    Write failed
```

### Command: `floe run` (P3 Stub)

```text
floe run [OPTIONS]

Options:
  -f, --file PATH      Path to floe.yaml (default: ./floe.yaml)
  -s, --select TEXT    Model selection (dbt-style selector)
  --help               Show help and exit

Exit Codes:
  0    Pipeline completed
  1    Compilation failed
  2    Execution failed
  3    Dagster not installed
```

### Command: `floe dev` (P3 Stub)

```text
floe dev [OPTIONS]

Options:
  -f, --file PATH    Path to floe.yaml (default: ./floe.yaml)
  -p, --port INT     Dev server port (default: 3000)
  --help             Show help and exit

Exit Codes:
  0    Dev server stopped gracefully
  1    Startup failed
  2    Dagster not installed
```

## Input/Output Entities

### Input: Configuration File

| Attribute | Type | Source | Validation |
|-----------|------|--------|------------|
| path | `Path` | `--file` option or CWD | Must exist, must be readable |
| content | `str` | File read | Must be valid YAML |
| spec | `FloeSpec` | Pydantic parse | Must pass FloeSpec validation |

### Output: Compiled Artifacts

| Attribute | Type | Destination | Format |
|-----------|------|-------------|--------|
| path | `Path` | `--output` or `.floe/compiled_artifacts.json` | JSON file |
| content | `CompiledArtifacts` | Serialized via `model_dump_json()` | JSON (indented) |

### Output: JSON Schema

| Attribute | Type | Destination | Format |
|-----------|------|-------------|--------|
| schema_type | `Literal["floe-spec", "compiled-artifacts"]` | `--type` option | Selection |
| output | `Path | None` | `--output` option or stdout | JSON |

### Output: Project Template

| File | Template | Variables |
|------|----------|-----------|
| `floe.yaml` | `floe.yaml.jinja2` | `name`, `target`, `version` |
| `README.md` | `README.md.jinja2` | `name` |

## Exit Code Convention

| Range | Meaning |
|-------|---------|
| 0 | Success |
| 1 | User error (validation, missing file) |
| 2 | System error (permissions, write failure) |
| 3 | Dependency error (missing floe-dagster) |

## Error Messages

All error messages follow the pattern:

```text
Error: <action-oriented message>

<optional: suggestion for fix>
```

Example:
```text
Error: Configuration file not found: floe.yaml

Run 'floe init' to create a new project, or use --file to specify a path.
```

## State Diagram: Command Flow

```text
┌─────────────────────────────────────────────────────────────┐
│                      User runs command                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Parse CLI arguments                       │
│              (Click decorators handle this)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Locate configuration file                   │
│     (--file option or default ./floe.yaml)                  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
       File exists?                     File not found
              │                               │
              ▼                               ▼
       Read & parse                    Exit code 2
              │                        "File not found"
              ▼
┌─────────────────────────────────────────────────────────────┐
│                Validate with FloeSpec                        │
│              (floe-core Pydantic model)                      │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
       Validation passes              Validation fails
              │                               │
              ▼                               ▼
     Execute command                   Exit code 1
     (compile, etc.)                  "Validation error"
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│              Write output (artifacts, schema)                │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
       Write succeeds                   Write fails
              │                               │
              ▼                               ▼
       Exit code 0                     Exit code 2
       "Success"                       "Permission denied"
```

## Dependencies on floe-core

| CLI Operation | floe-core Function | Import |
|--------------|-------------------|--------|
| `floe validate` | `FloeSpec.from_yaml()` | `from floe_core import FloeSpec` |
| `floe compile` | `Compiler().compile()` | `from floe_core import Compiler` |
| `floe schema export --type floe-spec` | `export_floe_spec_schema()` | `from floe_core import export_floe_spec_schema` |
| `floe schema export --type compiled-artifacts` | `export_compiled_artifacts_schema()` | `from floe_core import export_compiled_artifacts_schema` |
| Error handling | `FloeError`, `ValidationError`, `CompilationError` | `from floe_core import FloeError, ValidationError, CompilationError` |
