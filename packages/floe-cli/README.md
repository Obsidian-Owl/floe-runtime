# floe-cli

Developer CLI for floe-runtime.

## Overview

floe-cli provides the user-facing command-line interface for all floe-runtime operations.
It features fast `--help` performance (< 500ms) through lazy command loading.

## Installation

```bash
pip install floe-cli
```

## Commands

| Command | Purpose | Status |
|---------|---------|--------|
| `floe init` | Scaffold a new project | Implemented |
| `floe validate` | Validate floe.yaml | Implemented |
| `floe compile` | Generate CompiledArtifacts | Implemented |
| `floe schema export` | Export JSON Schema for IDE support | Implemented |
| `floe run` | Execute pipeline via Dagster | Stub (requires floe-dagster) |
| `floe dev` | Start Dagster development UI | Stub (requires floe-dagster) |

## Usage

### Create a new project

```bash
# Create project with default settings (duckdb)
floe init

# Create with custom name
floe init --name my-pipeline

# Create with specific compute target
floe init --target snowflake

# Overwrite existing files
floe init --force
```

### Validate configuration

```bash
# Validate ./floe.yaml
floe validate

# Validate custom file
floe validate --file path/to/floe.yaml
```

### Compile artifacts

```bash
# Compile to .floe/ directory
floe compile

# Compile to custom output directory
floe compile --output build/artifacts/

# Validate specific target
floe compile --target duckdb
```

### Export JSON Schema for IDE support

```bash
# Export to default location
floe schema export

# Export to custom location
floe schema export --output schemas/floe.schema.json
```

Then add to your `floe.yaml`:

```yaml
# yaml-language-server: $schema=./schemas/floe.schema.json
name: my-project
version: "1.0.0"
# ...
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User error (validation failed, invalid input) |
| 2 | System error (file not found, permission denied) |

## Architecture

See [docs/04-building-blocks.md](../../docs/04-building-blocks.md#3-floe-cli) for details.

## License

Apache 2.0
