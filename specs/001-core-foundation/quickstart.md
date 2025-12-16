# Quickstart: floe-core

**Feature**: 001-core-foundation
**Date**: 2025-12-15

## Overview

floe-core is the foundational package for floe-runtime, providing:
- **FloeSpec** - Schema for validating `floe.yaml` configuration files
- **CompiledArtifacts** - Immutable contract consumed by runtime packages
- **Compiler** - Transforms FloeSpec to CompiledArtifacts
- **JSON Schema Export** - For IDE autocomplete and cross-language validation

## Installation

```bash
# Install floe-core
pip install floe-core

# Or with uv (recommended)
uv add floe-core
```

## Basic Usage

### 1. Create a floe.yaml

```yaml
# floe.yaml
$schema: https://floe.dev/schemas/floe-spec.schema.json

name: customer-analytics
version: "1.0.0"

compute:
  target: duckdb
  properties:
    path: ./data/analytics.duckdb

transforms:
  - type: dbt
    path: models/

observability:
  traces: true
  metrics: true
  lineage: true
```

### 2. Validate Configuration

```python
from pathlib import Path
from floe_core import FloeSpec

# Load and validate floe.yaml
spec = FloeSpec.from_yaml(Path("floe.yaml"))

print(f"Pipeline: {spec.name} v{spec.version}")
print(f"Target: {spec.compute.target}")
```

### 3. Compile to Artifacts

```python
from floe_core import Compiler

# Create compiler
compiler = Compiler()

# Compile FloeSpec to CompiledArtifacts
artifacts = compiler.compile(spec, source_path=Path("floe.yaml"))

# Artifacts is now immutable and ready for runtime packages
print(f"Compiled at: {artifacts.metadata.compiled_at}")
print(f"Source hash: {artifacts.metadata.source_hash}")
```

### 4. Serialize for Downstream Packages

```python
import json
from pathlib import Path

# Serialize to JSON for floe-dagster, floe-dbt, etc.
artifacts_json = artifacts.model_dump_json(indent=2)
Path("target/compiled_artifacts.json").write_text(artifacts_json)

# Downstream packages load the artifacts:
# from floe_core import CompiledArtifacts
# artifacts = CompiledArtifacts.model_validate_json(Path("target/compiled_artifacts.json").read_text())
```

## Configuration Examples

### DuckDB (Local Development)

```yaml
name: dev-pipeline
version: "1.0.0"

compute:
  target: duckdb
  properties:
    path: ./data/dev.duckdb
    extensions:
      - httpfs
      - parquet
```

### Snowflake (Production)

```yaml
name: prod-pipeline
version: "1.0.0"

compute:
  target: snowflake
  connection_secret_ref: snowflake-credentials
  properties:
    account: myorg-account
    warehouse: COMPUTE_WH
    database: ANALYTICS
    schema: PUBLIC
```

### With Iceberg Catalog

```yaml
name: lakehouse-pipeline
version: "1.0.0"

compute:
  target: spark
  properties:
    master: local[*]

catalog:
  type: polaris
  uri: https://polaris.example.com/api/catalog
  credential_secret_ref: polaris-token
  warehouse: analytics_warehouse
```

### Full Configuration

```yaml
$schema: https://floe.dev/schemas/floe-spec.schema.json

name: enterprise-analytics
version: "2.1.0"

compute:
  target: snowflake
  connection_secret_ref: snowflake-prod
  properties:
    account: myorg
    warehouse: ANALYTICS_WH
    database: PROD_DW
    schema: PUBLIC

transforms:
  - type: dbt
    path: models/

consumption:
  enabled: true
  port: 4000
  api_secret_ref: cube-api-key
  pre_aggregations:
    refresh_schedule: "0 */6 * * *"
    timezone: "America/New_York"
  security:
    row_level: true
    tenant_column: tenant_id

governance:
  classification_source: dbt_meta
  emit_lineage: true

observability:
  traces: true
  metrics: true
  lineage: true
  otlp_endpoint: https://otel.example.com:4317
  lineage_endpoint: https://marquez.example.com
  attributes:
    environment: production
    team: data-platform

catalog:
  type: polaris
  uri: https://polaris.example.com/api/catalog
  credential_secret_ref: polaris-token
  warehouse: prod_warehouse
```

## API Reference

### FloeSpec

```python
from floe_core import FloeSpec

# Load from YAML file
spec = FloeSpec.from_yaml(Path("floe.yaml"))

# Load from dict
spec = FloeSpec.model_validate({
    "name": "my-pipeline",
    "version": "1.0.0",
    "compute": {"target": "duckdb"}
})

# Access configuration
spec.name              # "my-pipeline"
spec.version           # "1.0.0"
spec.compute.target    # ComputeTarget.DUCKDB
spec.transforms        # list[TransformConfig]
spec.consumption       # ConsumptionConfig (defaults applied)
spec.observability     # ObservabilityConfig (defaults applied)
```

### Compiler

```python
from floe_core import Compiler, FloeSpec, CompiledArtifacts

compiler = Compiler()

# Compile with source path (required for hash calculation)
artifacts: CompiledArtifacts = compiler.compile(
    spec=spec,
    source_path=Path("floe.yaml")
)

# Artifacts contains:
artifacts.version              # "1.0.0"
artifacts.metadata             # ArtifactMetadata
artifacts.compute              # ComputeConfig
artifacts.transforms           # list[TransformConfig]
artifacts.dbt_manifest_path    # Optional[str]
artifacts.dbt_project_path     # Optional[str]
artifacts.dbt_profiles_path    # Optional[str] (defaults to .floe/profiles/)
artifacts.column_classifications  # Optional[dict] (extracted from dbt meta)
```

### CompiledArtifacts

```python
from floe_core import CompiledArtifacts

# Load from JSON file
artifacts = CompiledArtifacts.model_validate_json(
    Path("target/compiled_artifacts.json").read_text()
)

# Serialize to JSON
json_str = artifacts.model_dump_json(indent=2)

# Access fields (immutable - cannot modify after creation)
artifacts.metadata.compiled_at      # datetime
artifacts.metadata.floe_core_version  # "0.1.0"
artifacts.metadata.source_hash      # "a1b2c3..."

# Check version compatibility
if artifacts.version.startswith("1."):
    # Compatible with v1.x consumers
    pass
```

### JSON Schema Export

```python
from floe_core import FloeSpec, CompiledArtifacts
import json
from pathlib import Path

# Export FloeSpec schema for IDE autocomplete
schema = FloeSpec.model_json_schema()
schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
Path("schemas/floe-spec.schema.json").write_text(json.dumps(schema, indent=2))

# Export CompiledArtifacts schema for cross-language validation
schema = CompiledArtifacts.model_json_schema()
Path("schemas/compiled-artifacts.schema.json").write_text(json.dumps(schema, indent=2))
```

## Error Handling

```python
from floe_core import FloeSpec, Compiler
from floe_core.errors import FloeError, ValidationError, CompilationError

try:
    spec = FloeSpec.from_yaml(Path("floe.yaml"))
    artifacts = Compiler().compile(spec, source_path=Path("floe.yaml"))
except ValidationError as e:
    # User-friendly message (safe to display)
    print(f"Configuration error: {e.user_message}")
except CompilationError as e:
    # User-friendly message (safe to display)
    print(f"Compilation error: {e.user_message}")
except FloeError as e:
    # Base exception for all floe errors
    print(f"Error: {e.user_message}")
```

## IDE Support

Add the `$schema` directive to your `floe.yaml` for autocomplete:

```yaml
# Option 1: Remote schema (once published)
$schema: https://floe.dev/schemas/floe-spec.schema.json

# Option 2: Local schema (for development)
$schema: ./schemas/floe-spec.schema.json

name: my-pipeline
version: "1.0.0"
# IDE now provides autocomplete for all fields!
```

## Integration with Runtime Packages

floe-core is the foundation. Runtime packages consume CompiledArtifacts:

```python
# floe-dagster uses artifacts to create Dagster assets
from floe_dagster import create_definitions
definitions = create_definitions(artifacts)

# floe-dbt uses artifacts to generate profiles.yml
from floe_dbt import generate_profiles
generate_profiles(artifacts)

# floe-cube uses artifacts to configure semantic layer
from floe_cube import configure_cube
configure_cube(artifacts)
```

## Next Steps

- See [data-model.md](data-model.md) for complete entity documentation
- See [research.md](research.md) for design decisions
- See [spec.md](spec.md) for full requirements
