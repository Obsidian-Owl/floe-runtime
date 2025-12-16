# CLI Commands Contract

**Feature**: 002-cli-interface
**Date**: 2025-12-16

## Overview

This document defines the CLI command contract for floe-cli. All commands follow these conventions:

- **Exit Code 0**: Success
- **Exit Code 1**: User error (validation, missing file)
- **Exit Code 2**: System error (permissions, write failure)
- **Output**: Colored by default, respects NO_COLOR and `--no-color`

---

## Command: `floe`

```
Usage: floe [OPTIONS] COMMAND [ARGS]...

  Floe Runtime - Open-Source Data Execution Layer

Options:
  --version    Show version and exit.
  --no-color   Disable colored output.
  --help       Show this message and exit.

Commands:
  compile   Generate CompiledArtifacts from floe.yaml
  dev       Start local development environment
  init      Scaffold a new floe project
  run       Execute pipeline via Dagster
  schema    JSON Schema operations
  validate  Validate floe.yaml configuration
```

---

## Command: `floe validate`

**Purpose**: Validate floe.yaml against FloeSpec schema

```
Usage: floe validate [OPTIONS]

  Validate floe.yaml configuration.

Options:
  -f, --file PATH  Path to floe.yaml [default: ./floe.yaml]
  --help           Show this message and exit.
```

### Exit Codes

| Code | Condition | Output |
|------|-----------|--------|
| 0 | Valid configuration | `✓ Configuration valid` |
| 1 | Schema violation | `✗ Validation failed: {details}` |
| 2 | File not found | `✗ File not found: {path}` |

### Examples

```bash
# Validate default floe.yaml
floe validate

# Validate specific file
floe validate --file path/to/floe.yaml
floe validate -f ./dev/floe.yaml
```

---

## Command: `floe compile`

**Purpose**: Transform FloeSpec into CompiledArtifacts JSON

```
Usage: floe compile [OPTIONS]

  Generate CompiledArtifacts from floe.yaml.

Options:
  -f, --file PATH    Path to floe.yaml [default: ./floe.yaml]
  -o, --output PATH  Output directory [default: .floe/]
  -t, --target TEXT  Compute target (must exist in spec)
  --help             Show this message and exit.
```

### Exit Codes

| Code | Condition | Output |
|------|-----------|--------|
| 0 | Compilation successful | `✓ Compiled to {output_path}` |
| 1 | Validation failed | `✗ Validation failed: {details}` |
| 2 | Write permission denied | `✗ Cannot write to: {path}` |
| 2 | Target not found | `✗ Target not found: {target}. Available: {list}` |

### Examples

```bash
# Compile to default .floe/ directory
floe compile

# Compile to custom directory
floe compile --output build/artifacts/
floe compile -o ./dist/

# Compile for specific target
floe compile --target snowflake
```

---

## Command: `floe init`

**Purpose**: Scaffold a new floe project with templates

```
Usage: floe init [OPTIONS]

  Scaffold a new floe project.

Options:
  -n, --name TEXT    Project name [default: current directory name]
  -t, --target TEXT  Compute target [default: duckdb]
  --force            Overwrite existing files
  --help             Show this message and exit.
```

### Exit Codes

| Code | Condition | Output |
|------|-----------|--------|
| 0 | Project created | `✓ Created project: {name}` |
| 1 | File exists (without --force) | `✗ floe.yaml already exists. Use --force to overwrite.` |
| 2 | Write permission denied | `✗ Cannot write to: {path}` |

### Files Created

| File | Description |
|------|-------------|
| `floe.yaml` | Pipeline configuration |
| `README.md` | Project documentation |

### Examples

```bash
# Initialize in current directory
floe init

# Initialize with specific name
floe init --name my-pipeline
floe init -n analytics-project

# Initialize with Snowflake target
floe init --target snowflake

# Force overwrite
floe init --force
```

---

## Command: `floe schema`

**Purpose**: JSON Schema operations

```
Usage: floe schema [OPTIONS] COMMAND [ARGS]...

  JSON Schema operations.

Options:
  --help  Show this message and exit.

Commands:
  export  Export JSON Schema to file or stdout
```

---

## Command: `floe schema export`

**Purpose**: Export JSON Schema for IDE autocomplete

```
Usage: floe schema export [OPTIONS]

  Export JSON Schema to file or stdout.

Options:
  -o, --output PATH  Output file path [default: stdout]
  --type TEXT        Schema type: floe-spec | compiled-artifacts [default: floe-spec]
  --help             Show this message and exit.
```

### Exit Codes

| Code | Condition | Output |
|------|-----------|--------|
| 0 | Schema exported | `{json_schema}` (stdout) or `✓ Schema written to {path}` |
| 1 | Invalid type | `✗ Invalid type: {type}. Use: floe-spec, compiled-artifacts` |
| 2 | Write failed | `✗ Cannot write to: {path}` |

### Examples

```bash
# Export FloeSpec schema to stdout
floe schema export

# Export to file
floe schema export --output schemas/floe.schema.json
floe schema export -o ./floe.schema.json

# Export CompiledArtifacts schema
floe schema export --type compiled-artifacts
floe schema export --type compiled-artifacts -o schemas/artifacts.schema.json
```

---

## Command: `floe run` (P3 Stub)

**Purpose**: Execute pipeline via Dagster orchestration

```
Usage: floe run [OPTIONS]

  Execute pipeline via Dagster.

  Requires floe-dagster package to be installed.

Options:
  -f, --file PATH    Path to floe.yaml [default: ./floe.yaml]
  -s, --select TEXT  Model selection (dbt-style selector)
  --help             Show this message and exit.
```

### Exit Codes

| Code | Condition | Output |
|------|-----------|--------|
| 0 | Pipeline completed | `✓ Pipeline completed` |
| 1 | Compilation failed | `✗ Compilation failed` |
| 2 | Execution failed | `✗ Execution failed: {details}` |
| 2 | Dagster not installed | `✗ floe-dagster not installed. Run: pip install floe-dagster` |

**Note**: This command is a stub in P1/P2. Full implementation requires floe-dagster package.

---

## Command: `floe dev` (P3 Stub)

**Purpose**: Start local development environment

```
Usage: floe dev [OPTIONS]

  Start local development environment.

  Requires floe-dagster package to be installed.

Options:
  -f, --file PATH  Path to floe.yaml [default: ./floe.yaml]
  -p, --port INT   Dev server port [default: 3000]
  --help           Show this message and exit.
```

### Exit Codes

| Code | Condition | Output |
|------|-----------|--------|
| 0 | Graceful shutdown | (Ctrl+C) |
| 1 | Startup failed | `✗ Failed to start dev server` |
| 2 | Dagster not installed | `✗ floe-dagster not installed. Run: pip install floe-dagster` |

**Note**: This command is a stub in P1/P2. Full implementation requires floe-dagster package.

---

## Environment Variables

| Variable | Effect |
|----------|--------|
| `NO_COLOR` | Disable colored output (standard) |
| `FORCE_COLOR` | Force colored output (overrides NO_COLOR) |
| `FLOE_CONFIG` | Default path to floe.yaml |

---

## Integration with floe-core

| CLI Command | floe-core Function |
|-------------|-------------------|
| `floe validate` | `FloeSpec.from_yaml(path)` |
| `floe compile` | `Compiler().compile(path)` |
| `floe schema export --type floe-spec` | `export_floe_spec_schema(output)` |
| `floe schema export --type compiled-artifacts` | `export_compiled_artifacts_schema(output)` |
