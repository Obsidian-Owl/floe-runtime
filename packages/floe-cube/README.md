# floe-cube

Cube semantic layer integration for floe-runtime.

## Overview

floe-cube provides integration with Cube for semantic layer and consumption APIs:

- **Configuration**: Cube configuration generation
- **Model Sync**: Sync dbt models to Cube

## Installation

```bash
pip install floe-cube
```

## Usage

```python
from floe_cube import sync_models

# Sync dbt models to Cube semantic layer
sync_models(dbt_manifest_path="target/manifest.json")
```

## Architecture

floe-cube bridges dbt models with Cube semantic layer:

- Generates Cube data model from dbt manifest
- Configures Cube connections
- Exposes REST/GraphQL/SQL APIs via Cube

## Development

```bash
uv sync
uv run pytest packages/floe-cube/tests/
```

## License

Apache 2.0
