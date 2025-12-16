# Quickstart: CLI Interface

**Feature**: 002-cli-interface
**Date**: 2025-12-16

## Prerequisites

- Python 3.10+
- uv package manager
- floe-runtime repository cloned

## Installation (Development)

```bash
# From repository root
uv sync --all-packages

# Verify CLI is available
uv run floe --version
```

## Basic Usage

### 1. Create a New Project

```bash
# Initialize with default DuckDB target
uv run floe init --name my-pipeline

# Or with Snowflake target
uv run floe init --name my-pipeline --target snowflake
```

This creates:
- `floe.yaml` - Pipeline configuration
- `README.md` - Project documentation

### 2. Validate Configuration

```bash
# Validate floe.yaml in current directory
uv run floe validate

# Validate specific file
uv run floe validate --file path/to/floe.yaml
```

### 3. Compile to Artifacts

```bash
# Compile to default .floe/ directory
uv run floe compile

# Compile to custom location
uv run floe compile --output build/

# Compile for specific target
uv run floe compile --target snowflake
```

### 4. Export JSON Schema (for IDE)

```bash
# Export FloeSpec schema to file
uv run floe schema export --output schemas/floe.schema.json

# Export CompiledArtifacts schema
uv run floe schema export --type compiled-artifacts --output schemas/artifacts.schema.json

# Print schema to stdout
uv run floe schema export
```

### 5. Configure VS Code YAML

Add to your `floe.yaml`:
```yaml
# yaml-language-server: $schema=./schemas/floe.schema.json
name: my-pipeline
version: "1.0.0"
compute:
  target: duckdb
```

## Example floe.yaml

```yaml
name: analytics-pipeline
version: "1.0.0"
compute:
  target: duckdb
  properties:
    path: ":memory:"
transforms:
  - type: dbt
    path: ./dbt
governance:
  classification_source: dbt_meta
observability:
  tracing_enabled: true
  metrics_enabled: true
```

## Command Reference

| Command | Description |
|---------|-------------|
| `floe --help` | Show all commands |
| `floe --version` | Show version |
| `floe validate` | Validate configuration |
| `floe compile` | Generate artifacts |
| `floe init` | Create new project |
| `floe schema export` | Export JSON Schema |

## Common Options

| Option | Commands | Description |
|--------|----------|-------------|
| `--file, -f` | validate, compile | Path to floe.yaml |
| `--output, -o` | compile, schema export | Output path |
| `--target, -t` | compile, init | Compute target |
| `--no-color` | all | Disable colored output |
| `--force` | init | Overwrite existing files |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User error (validation, missing file) |
| 2 | System error (permissions, write failure) |

## Troubleshooting

### "File not found: floe.yaml"

```bash
# Either create a new project
uv run floe init

# Or specify the path
uv run floe validate --file path/to/floe.yaml
```

### "Validation failed"

Check the error message for specific field issues. Common problems:
- Missing required fields (`name`, `version`, `compute`)
- Invalid compute target (must be one of: duckdb, snowflake, bigquery, redshift, databricks, postgres, spark)

### CI/CD Integration

```bash
# Disable colors for log output
uv run floe --no-color validate
uv run floe --no-color compile

# Check exit code
if uv run floe validate; then
    uv run floe compile
else
    echo "Validation failed"
    exit 1
fi
```
