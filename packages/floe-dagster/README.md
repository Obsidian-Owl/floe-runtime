# floe-dagster

Dagster integration for floe-runtime.

## Overview

floe-dagster provides:

- **Asset factory**: Generate Dagster assets from CompiledArtifacts
- **dbt integration**: Use dagster-dbt for model execution
- **OpenLineage**: Emit lineage events during execution
- **Definitions entry point**: Ready-to-use Dagster Definitions

## Installation

```bash
pip install floe-dagster
```

## Usage

```python
from floe_dagster import create_definitions
from floe_core import CompiledArtifacts

# Load artifacts
artifacts = CompiledArtifacts.model_validate_json(
    Path(".floe/artifacts.json").read_text()
)

# Create Dagster Definitions
defs = create_definitions(artifacts)
```

## Architecture

See [docs/04-building-blocks.md](../../docs/04-building-blocks.md#4-floe-dagster) for details.

### Component Ownership

Per `.claude/rules/component-ownership.md`:
- **Dagster owns orchestration** - floe-dagster manages assets, schedules, and sensors
- **dbt owns SQL** - we invoke dbt, never parse SQL

## License

Apache 2.0
