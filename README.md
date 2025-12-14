# floe-runtime

**Open-source data execution layer** - Define your data pipeline in a single `floe.yaml` file, and floe-runtime handles orchestration, transformation, storage, and observability.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

## Overview

floe-runtime integrates best-in-class open-source tools into a cohesive developer experience:

- **Dagster** for asset-centric orchestration
- **dbt** for SQL transformations
- **Apache Iceberg** for open table format storage
- **Apache Polaris** for catalog management
- **Cube** for semantic layer and consumption APIs
- **OpenTelemetry** for observability
- **OpenLineage** for data lineage

## Quick Start

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/your-org/floe-runtime.git
cd floe-runtime
uv sync

# Run your first pipeline
floe init my-project
cd my-project
floe run
```

## Project Structure

```
floe-runtime/
├── packages/
│   ├── floe-core/       # Schema, validation, compilation
│   ├── floe-cli/        # Developer CLI
│   ├── floe-dagster/    # Dagster asset factory
│   ├── floe-dbt/        # dbt profile generation, execution
│   ├── floe-iceberg/    # Iceberg table management
│   ├── floe-polaris/    # Polaris catalog client
│   └── floe-cube/       # Cube semantic layer
├── docs/                # Architecture documentation
└── charts/              # Helm charts (coming soon)
```

## Example floe.yaml

```yaml
name: customer-analytics
version: "1.0"

compute:
  target: duckdb  # or snowflake, bigquery, postgres, databricks

transforms:
  - type: dbt
    path: models/

consumption:
  enabled: true
  cube:
    port: 4000

observability:
  traces: true
  lineage: true
```

## Philosophy

### dbt Owns SQL

floe-runtime **never parses SQL**. dbt handles all SQL compilation, dialect translation, and execution. We provide orchestration, not a new SQL engine.

### Standard Open Formats

We use open standards everywhere:
- **Iceberg** for storage
- **OpenLineage** for lineage
- **OpenTelemetry** for observability

### Extensible by Design

Clear interfaces for custom transforms, compute targets, and integrations. No vendor lock-in.

## Development

```bash
# Install dependencies
uv sync

# Run quality checks
uv run mypy --strict packages/
uv run ruff check .
uv run black --check .
uv run pytest

# Format code
uv run black .
uv run isort .
```

## Documentation

- [Architecture Overview](docs/00-overview.md)
- [Building Blocks](docs/04-building-blocks.md)
- [Solution Strategy](docs/03-solution-strategy.md)
- [Glossary](docs/10-glossary.md)

## Contributing

We welcome contributions! Please see our contributing guidelines for details.

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
