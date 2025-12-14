# 04. Building Blocks (C4 Level 2)

This document describes the container view—the seven packages that comprise floe-runtime and their responsibilities.

---

## 1. Package Overview

```
floe-runtime/
├── floe-core/          # Schema, parsing, validation, CompiledArtifacts
├── floe-cli/           # Developer CLI (init, validate, compile, run, dev)
├── floe-dagster/       # Dagster asset factory from CompiledArtifacts
├── floe-dbt/           # dbt profile generation, execution wrapper
├── floe-iceberg/       # Iceberg table management utilities
├── floe-polaris/       # Polaris catalog client
├── floe-cube/          # Cube semantic layer, consumption APIs
├── charts/             # Modular Helm charts
└── docs/               # This documentation
```

### Package Dependencies

```
                    ┌─────────────┐
                    │  floe-cli   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌───────────┐ ┌───────────┐ ┌───────────┐
       │ floe-core │ │floe-dagster│ │  floe-dbt │
       └───────────┘ └─────┬─────┘ └─────┬─────┘
              │            │             │
              │      ┌─────┴─────┐       │
              │      ▼           ▼       │
              │ ┌─────────┐ ┌─────────┐  │
              │ │floe-    │ │floe-    │  │
              └►│iceberg  │ │polaris  │◄─┘
                └────┬────┘ └────┬────┘
                     │           │
                     └─────┬─────┘
                           ▼
                    ┌───────────┐
                    │ floe-cube │  (Consumption Layer)
                    └───────────┘
```

---

## 2. floe-core

### 2.1 Purpose

The foundation package that defines the `floe.yaml` schema, validates user configuration, and produces `CompiledArtifacts` for downstream consumers.

### 2.2 Responsibilities

| Responsibility | Description |
|----------------|-------------|
| Schema definition | Pydantic models for floe.yaml |
| Validation | Validate user configuration against schema |
| Compilation | Transform FloeSpec → CompiledArtifacts |
| JSON Schema | Generate JSON Schema for IDE support |

### 2.3 Key Components

```python
# floe_core/schemas/floe_spec.py
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum

class ComputeTarget(str, Enum):
    """Supported compute targets."""
    DUCKDB = "duckdb"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    POSTGRES = "postgres"
    REDSHIFT = "redshift"
    DATABRICKS = "databricks"
    SPARK = "spark"

class ComputeConfig(BaseModel):
    """Compute target configuration."""
    target: ComputeTarget
    connection_secret_ref: Optional[str] = None
    properties: dict = Field(default_factory=dict)

class TransformConfig(BaseModel):
    """Transform configuration."""
    type: Literal["dbt"]  # Python transforms deferred to future scope
    path: str
    target: Optional[str] = None

class ObservabilityConfig(BaseModel):
    """Observability configuration."""
    traces: bool = True
    metrics: bool = True
    lineage: bool = True
    otlp_endpoint: Optional[str] = None
    lineage_endpoint: Optional[str] = None

class CubeSecurityConfig(BaseModel):
    """Cube security configuration."""
    row_level: bool = True
    tenant_column: str = "tenant_id"

class PreAggregationConfig(BaseModel):
    """Cube pre-aggregation configuration."""
    refresh_schedule: str = "*/30 * * * *"
    timezone: str = "UTC"

class CubeConfig(BaseModel):
    """Cube semantic layer configuration."""
    port: int = 4000
    api_secret_ref: Optional[str] = None
    pre_aggregations: PreAggregationConfig = Field(default_factory=PreAggregationConfig)
    security: CubeSecurityConfig = Field(default_factory=CubeSecurityConfig)

class ConsumptionConfig(BaseModel):
    """Consumption layer configuration."""
    enabled: bool = False
    cube: Optional[CubeConfig] = None

# --- Governance Configuration ---
# See ADR-0012: Data Classification Governance

class ClassificationSource(str, Enum):
    """Where to read classification metadata from."""
    DBT_META = "dbt_meta"  # Read from dbt model meta tags
    EXTERNAL = "external"   # External catalog (future)

class PolicyAction(str, Enum):
    """Actions to take for classified data."""
    RESTRICT = "restrict"     # Enforce access control
    SYNTHESIZE = "synthesize" # Generate synthetic data
    REDACT = "redact"         # Remove/null the data
    MASK = "mask"             # Partial masking (e.g., ***@email.com)
    HASH = "hash"             # One-way hash

class EnvironmentPolicy(BaseModel):
    """Policy for a specific environment type."""
    action: PolicyAction
    requires_role: list[str] = Field(default_factory=list)

class ClassificationPolicy(BaseModel):
    """Policy for a classification type."""
    production: Optional[EnvironmentPolicy] = None
    non_production: Optional[EnvironmentPolicy] = None

class GovernanceConfig(BaseModel):
    """Data governance configuration. See ADR-0012."""
    classification_source: ClassificationSource = ClassificationSource.DBT_META
    policies: dict[str, ClassificationPolicy] = Field(default_factory=dict)
    emit_classification_lineage: bool = True  # Emit OpenLineage classification facets

class FloeSpec(BaseModel):
    """Root schema for floe.yaml."""
    name: str = Field(description="Pipeline name")
    version: str = Field(default="1.0", description="Schema version")
    compute: ComputeConfig
    transforms: list[TransformConfig] = Field(default_factory=list)
    consumption: ConsumptionConfig = Field(default_factory=ConsumptionConfig)
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig
    )
```

```python
# floe_core/schemas/compiled_artifacts.py
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

class ArtifactMetadata(BaseModel):
    """Metadata about compilation."""
    compiled_at: datetime
    floe_core_version: str
    source_hash: str

class EnvironmentContext(BaseModel):
    """Runtime context injected by Control Plane enricher.

    Only present in managed (SaaS) mode. Not included in base compilation output.
    """
    tenant_id: UUID
    tenant_slug: str
    project_id: UUID
    project_slug: str
    environment_id: UUID
    environment_type: Literal["development", "preview", "staging", "production"]
    governance_category: Literal["production", "non_production"]

class CompiledArtifacts(BaseModel):
    """Output of compilation - input to runtime."""
    version: str = "1.0.0"
    metadata: ArtifactMetadata
    compute: ComputeConfig
    transforms: list[TransformConfig]
    consumption: ConsumptionConfig
    governance: GovernanceConfig
    observability: ObservabilityConfig

    # Dagster-specific
    dbt_manifest_path: Optional[str] = None
    dbt_project_path: Optional[str] = None

    # Lineage-specific (set by Control Plane in managed mode)
    lineage_namespace: Optional[str] = None

    # Environment context (set by Control Plane enricher)
    environment_context: Optional[EnvironmentContext] = None

    # Governance-specific (extracted from dbt manifest)
    column_classifications: Optional[dict[str, dict[str, dict]]] = None  # model → column → classification
```

```python
# floe_core/compiler.py
from pathlib import Path
import yaml
from .schemas import FloeSpec, CompiledArtifacts, ArtifactMetadata

class Compiler:
    """Compile floe.yaml to CompiledArtifacts."""

    def compile(self, spec_path: Path) -> CompiledArtifacts:
        """Parse and compile floe.yaml."""
        with open(spec_path) as f:
            raw = yaml.safe_load(f)

        spec = FloeSpec.model_validate(raw)

        # Extract classifications from dbt manifest if available
        column_classifications = None
        dbt_project = self._find_dbt_project(spec_path.parent)
        if dbt_project and spec.governance.classification_source == ClassificationSource.DBT_META:
            column_classifications = self._extract_classifications(dbt_project)

        return CompiledArtifacts(
            metadata=ArtifactMetadata(
                compiled_at=datetime.now(timezone.utc),
                floe_core_version=__version__,
                source_hash=self._hash_spec(spec_path),
            ),
            compute=spec.compute,
            transforms=spec.transforms,
            consumption=spec.consumption,
            governance=spec.governance,
            observability=spec.observability,
            dbt_project_path=dbt_project,
            column_classifications=column_classifications,
        )

    def _extract_classifications(self, dbt_project_path: str) -> dict:
        """Extract column classifications from dbt manifest meta tags."""
        manifest_path = Path(dbt_project_path) / "target" / "manifest.json"
        if not manifest_path.exists():
            return {}

        with open(manifest_path) as f:
            manifest = json.load(f)

        classifications = {}
        for node_id, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") != "model":
                continue

            model_name = node["name"]
            model_classifications = {}

            for col_name, col_info in node.get("columns", {}).items():
                floe_meta = col_info.get("meta", {}).get("floe", {})
                if floe_meta.get("classification"):
                    model_classifications[col_name] = {
                        "classification": floe_meta["classification"],
                        "pii_type": floe_meta.get("pii_type"),
                        "sensitivity": floe_meta.get("sensitivity", "medium"),
                    }

            if model_classifications:
                classifications[model_name] = model_classifications

        return classifications
```

### 2.4 Public API

```python
from floe_core import (
    FloeSpec,
    CompiledArtifacts,
    Compiler,
    ValidationError,
)

# Parse and validate
spec = FloeSpec.model_validate(yaml_dict)

# Compile
compiler = Compiler()
artifacts = compiler.compile(Path("floe.yaml"))

# Generate JSON Schema (for IDE support)
schema = FloeSpec.model_json_schema()
```

### 2.5 JSON Schema Export

floe-core exports JSON Schema for cross-repository validation. See [CompiledArtifacts Contract](../contracts/compiled-artifacts.md).

```python
# floe_core/schema_export.py
from pathlib import Path
import json
from .schemas import FloeSpec, CompiledArtifacts

def export_floespec_schema(output_path: Path) -> None:
    """Export FloeSpec JSON Schema for IDE support."""
    schema = FloeSpec.model_json_schema()
    output_path.write_text(json.dumps(schema, indent=2))

def export_artifacts_schema(output_path: Path) -> None:
    """Export CompiledArtifacts JSON Schema for Control Plane validation."""
    schema = CompiledArtifacts.model_json_schema()
    output_path.write_text(json.dumps(schema, indent=2))
```

**Usage:**

```bash
# Export schemas via CLI
floe schema export --type floespec --output floe.schema.json
floe schema export --type artifacts --output compiled-artifacts.schema.json
```

The exported JSON Schema enables:
- **IDE support**: VS Code, IntelliJ YAML validation
- **Control Plane validation**: Go code validates artifacts against schema
- **Documentation**: Auto-generated from Pydantic models

---

## 3. floe-cli

### 3.1 Purpose

The user-facing command-line interface for all floe-runtime operations.

### 3.2 Commands

| Command | Purpose |
|---------|---------|
| `floe init` | Scaffold a new project |
| `floe validate` | Validate floe.yaml |
| `floe compile` | Generate CompiledArtifacts |
| `floe run` | Execute pipeline |
| `floe dev` | Start development environment |
| `floe test` | Run data tests |
| `floe schema export` | Export JSON Schema for validation |

### 3.3 Implementation

```python
# floe_cli/main.py
import click
from pathlib import Path

@click.group()
@click.version_option()
def cli():
    """Floe Runtime CLI - Build and run data pipelines."""
    pass

@cli.command()
@click.argument("name")
@click.option("--template", default="basic", help="Project template")
def init(name: str, template: str):
    """Create a new Floe project."""
    from floe_cli.commands.init import create_project
    create_project(name, template)
    click.echo(f"Created project: {name}")

@cli.command()
@click.option("--config", "-c", default="floe.yaml", help="Config file path")
def validate(config: str):
    """Validate floe.yaml configuration."""
    from floe_core import Compiler, ValidationError

    try:
        compiler = Compiler()
        compiler.validate(Path(config))
        click.echo("✓ Configuration is valid")
    except ValidationError as e:
        click.echo(f"✗ Validation failed: {e}", err=True)
        raise SystemExit(1)

@cli.command()
@click.option("--config", "-c", default="floe.yaml")
@click.option("--output", "-o", default=".floe/artifacts.json")
def compile(config: str, output: str):
    """Compile floe.yaml to artifacts."""
    from floe_core import Compiler

    compiler = Compiler()
    artifacts = compiler.compile(Path(config))

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(artifacts.model_dump_json(indent=2))

    click.echo(f"✓ Compiled to {output}")

@cli.command()
@click.option("--config", "-c", default="floe.yaml")
@click.option("--env", "-e", default="dev", help="Environment name")
@click.option("--select", "-s", multiple=True, help="Select specific models")
def run(config: str, env: str, select: tuple[str, ...]):
    """Execute the data pipeline."""
    from floe_cli.commands.run import execute_pipeline

    execute_pipeline(
        config_path=Path(config),
        environment=env,
        select=list(select) if select else None,
    )

@cli.command()
@click.option("--config", "-c", default="floe.yaml")
def dev(config: str):
    """Start the development environment."""
    from floe_cli.commands.dev import start_dev_environment

    click.echo("Starting development environment...")
    click.echo("  Dagster UI: http://localhost:3000")
    click.echo("  Marquez:    http://localhost:5000")
    click.echo("  Jaeger:     http://localhost:16686")

    start_dev_environment(Path(config))
```

### 3.4 Project Templates

```
floe_cli/templates/
├── basic/
│   ├── floe.yaml.j2
│   ├── models/
│   │   └── example.sql
│   └── seeds/
│       └── sample_data.csv
├── dbt-only/
│   ├── floe.yaml.j2
│   └── dbt_project.yml.j2
└── full/
    ├── floe.yaml.j2
    ├── models/
    ├── seeds/
    ├── tests/
    └── docker-compose.yml
```

---

## 4. floe-dagster

### 4.1 Purpose

Dagster integration that creates Software-Defined Assets from CompiledArtifacts.

### 4.2 Responsibilities

| Responsibility | Description |
|----------------|-------------|
| Asset factory | Generate Dagster assets from artifacts |
| dbt integration | Use dagster-dbt for model execution |
| Schedules | Create Dagster schedules from config |
| Sensors | Create Dagster sensors from config |
| OpenLineage | Emit lineage events during execution |

### 4.3 Implementation

```python
# floe_dagster/asset_factory.py
from dagster import (
    Definitions,
    AssetExecutionContext,
    asset,
    AssetsDefinition,
)
from dagster_dbt import DbtCliResource, dbt_assets

from floe_core import CompiledArtifacts

def create_definitions(artifacts: CompiledArtifacts) -> Definitions:
    """Create Dagster Definitions from CompiledArtifacts."""

    assets = create_assets(artifacts)
    resources = create_resources(artifacts)

    return Definitions(
        assets=assets,
        resources=resources,
    )

def create_assets(artifacts: CompiledArtifacts) -> list[AssetsDefinition]:
    """Create Dagster assets from CompiledArtifacts."""
    assets = []

    for transform in artifacts.transforms:
        if transform.type == "dbt":
            assets.extend(create_dbt_assets(artifacts, transform))
        elif transform.type == "python":
            assets.extend(create_python_assets(artifacts, transform))

    return assets

def create_dbt_assets(
    artifacts: CompiledArtifacts,
    transform: TransformConfig,
) -> list[AssetsDefinition]:
    """Create dbt assets."""

    manifest_path = artifacts.dbt_manifest_path

    @dbt_assets(manifest=manifest_path)
    def dbt_models(context: AssetExecutionContext, dbt: DbtCliResource):
        yield from dbt.cli(["build"], context=context).stream()

    return [dbt_models]

def create_resources(artifacts: CompiledArtifacts) -> dict:
    """Create Dagster resources."""
    return {
        "dbt": DbtCliResource(
            project_dir=artifacts.dbt_project_path,
            profiles_dir=artifacts.dbt_profiles_path,
        ),
    }
```

```python
# floe_dagster/lineage.py
from dagster import OpExecutionContext
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Job, Run, Dataset

class LineageEmitter:
    """Emit OpenLineage events during Dagster execution."""

    def __init__(self, client: OpenLineageClient, namespace: str):
        self.client = client
        self.namespace = namespace

    def emit_run_start(
        self,
        context: OpExecutionContext,
        inputs: list[Dataset],
    ) -> str:
        """Emit run start event."""
        run_id = str(context.run_id)
        job_name = context.asset_key.to_user_string()

        event = RunEvent(
            eventType=RunState.START,
            eventTime=datetime.now(timezone.utc).isoformat(),
            job=Job(namespace=self.namespace, name=job_name),
            run=Run(runId=run_id),
            inputs=inputs,
        )

        self.client.emit(event)
        return run_id

    def emit_run_complete(
        self,
        context: OpExecutionContext,
        run_id: str,
        outputs: list[Dataset],
    ):
        """Emit run complete event."""
        event = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=datetime.now(timezone.utc).isoformat(),
            job=Job(
                namespace=self.namespace,
                name=context.asset_key.to_user_string(),
            ),
            run=Run(runId=run_id),
            outputs=outputs,
        )

        self.client.emit(event)
```

### 4.4 Definitions Entry Point

```python
# floe_dagster/definitions.py
from pathlib import Path
from dagster import Definitions
from floe_core import Compiler
from floe_dagster.asset_factory import create_definitions

# Load artifacts from environment or default path
artifacts_path = Path(
    os.environ.get("FLOE_ARTIFACTS_PATH", ".floe/artifacts.json")
)

if artifacts_path.exists():
    artifacts = CompiledArtifacts.model_validate_json(
        artifacts_path.read_text()
    )
    defs = create_definitions(artifacts)
else:
    # Fall back to compiling from floe.yaml
    compiler = Compiler()
    artifacts = compiler.compile(Path("floe.yaml"))
    defs = create_definitions(artifacts)
```

---

## 5. floe-dbt

### 5.1 Purpose

dbt integration for profile generation and execution wrapping.

### 5.2 Responsibilities

| Responsibility | Description |
|----------------|-------------|
| Profile generation | Generate profiles.yml from CompiledArtifacts |
| Adapter selection | Choose dbt adapter based on compute target |
| Environment injection | Inject environment variables |
| OpenLineage wrapper | Wrap dbt execution with lineage |

### 5.3 Implementation

```python
# floe_dbt/profiles.py
from pathlib import Path
import yaml
from floe_core import CompiledArtifacts, ComputeTarget

def generate_profiles(artifacts: CompiledArtifacts) -> dict:
    """Generate dbt profiles.yml from CompiledArtifacts."""
    target = artifacts.compute.target
    props = artifacts.compute.properties

    generators = {
        ComputeTarget.DUCKDB: _duckdb_profile,
        ComputeTarget.SNOWFLAKE: _snowflake_profile,
        ComputeTarget.BIGQUERY: _bigquery_profile,
        ComputeTarget.POSTGRES: _postgres_profile,
        ComputeTarget.REDSHIFT: _redshift_profile,
        ComputeTarget.DATABRICKS: _databricks_profile,
    }

    generator = generators.get(target)
    if not generator:
        raise ValueError(f"Unsupported target: {target}")

    return {"floe": {"target": "default", "outputs": {"default": generator(props)}}}

def _duckdb_profile(props: dict) -> dict:
    return {
        "type": "duckdb",
        "path": props.get("path", "/tmp/floe.duckdb"),
        "extensions": props.get("extensions", ["parquet", "httpfs"]),
    }

def _snowflake_profile(props: dict) -> dict:
    return {
        "type": "snowflake",
        "account": "{{ env_var('SNOWFLAKE_ACCOUNT') }}",
        "user": "{{ env_var('SNOWFLAKE_USER') }}",
        "password": "{{ env_var('SNOWFLAKE_PASSWORD') }}",
        "role": props.get("role", "{{ env_var('SNOWFLAKE_ROLE') }}"),
        "database": props.get("database", "{{ env_var('SNOWFLAKE_DATABASE') }}"),
        "warehouse": props.get("warehouse", "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"),
        "schema": props.get("schema", "public"),
    }

def _bigquery_profile(props: dict) -> dict:
    return {
        "type": "bigquery",
        "method": props.get("method", "oauth"),
        "project": props.get("project", "{{ env_var('GCP_PROJECT') }}"),
        "dataset": props.get("dataset", "{{ env_var('BQ_DATASET') }}"),
        "location": props.get("location", "US"),
    }

def write_profiles(artifacts: CompiledArtifacts, output_dir: Path) -> Path:
    """Write profiles.yml to disk."""
    profiles = generate_profiles(artifacts)
    output_path = output_dir / "profiles.yml"
    output_path.write_text(yaml.dump(profiles))
    return output_path
```

```python
# floe_dbt/executor.py
import subprocess
from pathlib import Path
from floe_core import CompiledArtifacts

class DbtExecutor:
    """Execute dbt commands with proper configuration."""

    def __init__(self, artifacts: CompiledArtifacts, profiles_dir: Path):
        self.artifacts = artifacts
        self.profiles_dir = profiles_dir
        self.project_dir = Path(artifacts.dbt_project_path)

    def run(
        self,
        command: str = "build",
        select: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> subprocess.CompletedProcess:
        """Run dbt command."""
        args = [
            "dbt",
            command,
            "--project-dir", str(self.project_dir),
            "--profiles-dir", str(self.profiles_dir),
        ]

        if select:
            args.extend(["--select", " ".join(select)])
        if exclude:
            args.extend(["--exclude", " ".join(exclude)])

        return subprocess.run(args, check=True)

    def compile(self) -> Path:
        """Compile dbt project and return manifest path."""
        self.run("compile")
        return self.project_dir / "target" / "manifest.json"
```

---

## 6. floe-iceberg

### 6.1 Purpose

Apache Iceberg utilities for table management.

### 6.2 Responsibilities

| Responsibility | Description |
|----------------|-------------|
| Table creation | Create Iceberg tables with proper schema |
| Partitioning | Apply partitioning strategies |
| Compaction | Manage table compaction |
| Snapshots | Manage time travel snapshots |

### 6.3 Implementation

```python
# floe_iceberg/tables.py
from pyiceberg.catalog import Catalog
from pyiceberg.schema import Schema
from pyiceberg.partitioning import PartitionSpec
from pyiceberg.table import Table

class IcebergTableManager:
    """Manage Iceberg tables."""

    def __init__(self, catalog: Catalog, namespace: str):
        self.catalog = catalog
        self.namespace = namespace

    def create_table(
        self,
        name: str,
        schema: Schema,
        partition_spec: PartitionSpec | None = None,
        properties: dict | None = None,
    ) -> Table:
        """Create an Iceberg table."""
        identifier = f"{self.namespace}.{name}"

        return self.catalog.create_table(
            identifier=identifier,
            schema=schema,
            partition_spec=partition_spec or PartitionSpec(),
            properties=properties or {},
        )

    def get_table(self, name: str) -> Table:
        """Get an existing Iceberg table."""
        identifier = f"{self.namespace}.{name}"
        return self.catalog.load_table(identifier)

    def list_tables(self) -> list[str]:
        """List all tables in namespace."""
        return [
            t.name for t in self.catalog.list_tables(self.namespace)
        ]
```

```python
# floe_iceberg/compaction.py
from pyiceberg.table import Table

class CompactionManager:
    """Manage Iceberg table compaction."""

    def __init__(self, table: Table):
        self.table = table

    def compact_data_files(
        self,
        target_file_size_bytes: int = 512 * 1024 * 1024,  # 512 MB
    ):
        """Compact small data files."""
        # Implementation depends on compute engine
        # Spark: table.compact_data_files()
        pass

    def expire_snapshots(
        self,
        older_than_days: int = 7,
        retain_last: int = 5,
    ):
        """Expire old snapshots."""
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=older_than_days)

        self.table.manage_snapshots().expire_snapshots_older_than(
            cutoff.timestamp() * 1000
        ).commit()
```

---

## 7. floe-polaris

### 7.1 Purpose

Apache Polaris catalog client for Iceberg metadata management.

### 7.2 Responsibilities

| Responsibility | Description |
|----------------|-------------|
| Catalog connection | Connect to Polaris REST API |
| Namespace management | Create/manage namespaces |
| Table registration | Register tables in catalog |
| Credential vending | Obtain storage credentials |

### 7.3 Implementation

```python
# floe_polaris/client.py
from pyiceberg.catalog import load_catalog
from pyiceberg.catalog.rest import RestCatalog

class PolarisClient:
    """Client for Apache Polaris catalog."""

    def __init__(
        self,
        uri: str,
        credential: str | None = None,
        warehouse: str | None = None,
    ):
        self.catalog = load_catalog(
            "polaris",
            type="rest",
            uri=uri,
            credential=credential,
            warehouse=warehouse,
        )

    def create_namespace(self, namespace: str, properties: dict | None = None):
        """Create a namespace."""
        self.catalog.create_namespace(namespace, properties or {})

    def list_namespaces(self) -> list[str]:
        """List all namespaces."""
        return [ns[0] for ns in self.catalog.list_namespaces()]

    def namespace_exists(self, namespace: str) -> bool:
        """Check if namespace exists."""
        return namespace in self.list_namespaces()
```

```python
# floe_polaris/factory.py
from floe_core import CompiledArtifacts
from floe_polaris.client import PolarisClient

def create_catalog_client(artifacts: CompiledArtifacts) -> PolarisClient:
    """Create Polaris client from artifacts."""
    catalog_config = artifacts.catalog

    if catalog_config.type != "polaris":
        raise ValueError(f"Expected polaris catalog, got {catalog_config.type}")

    return PolarisClient(
        uri=catalog_config.uri,
        credential=catalog_config.credential,
        warehouse=catalog_config.warehouse,
    )
```

---

## 8. floe-cube

### 8.1 Purpose

Cube semantic layer integration for data consumption APIs. Provides REST, GraphQL, and SQL interfaces for querying transformed data. See [ADR-R0001](adr/0001-cube-semantic-layer.md).

### 8.2 Responsibilities

| Responsibility | Description |
|----------------|-------------|
| Model sync | Sync dbt models to Cube cubes via cube_dbt |
| API serving | Expose REST, GraphQL, SQL (Postgres wire protocol) |
| Caching | Manage Cube Store pre-aggregations |
| Security | Implement row-level security via security context |
| Lineage | Emit OpenLineage events for queries |
| MCP server | Expose MCP interface for AI agents |

### 8.3 Implementation

```python
# floe_cube/config.py
from pathlib import Path
from floe_core import CompiledArtifacts

def generate_cube_config(artifacts: CompiledArtifacts) -> dict:
    """Generate Cube configuration from CompiledArtifacts."""
    cube_config = artifacts.consumption.cube

    if not artifacts.consumption.enabled or not cube_config:
        raise ValueError("Consumption layer not enabled")

    return {
        "apiPort": cube_config.port,
        "dbType": _map_compute_to_cube_driver(artifacts.compute.target),
        "preAggregationsSchema": "floe_preaggs",
        "scheduledRefreshTimer": cube_config.pre_aggregations.refresh_schedule,
        "scheduledRefreshTimezone": cube_config.pre_aggregations.timezone,
    }

def _map_compute_to_cube_driver(target: str) -> str:
    """Map Floe compute target to Cube driver type."""
    mapping = {
        "duckdb": "duckdb",
        "snowflake": "snowflake",
        "bigquery": "bigquery",
        "postgres": "postgres",
        "redshift": "redshift",
        "databricks": "databricks",
    }
    return mapping.get(target, "postgres")
```

```python
# floe_cube/model_sync.py
from pathlib import Path
from cube_dbt import Dbt

class CubeModelSync:
    """Sync dbt models to Cube cubes."""

    def __init__(self, dbt_manifest_path: Path):
        self.dbt = Dbt.from_file(str(dbt_manifest_path))

    def generate_cube_models(
        self,
        output_dir: Path,
        tags: list[str] | None = None,
    ) -> list[Path]:
        """Generate Cube model files from dbt models."""
        models = self.dbt.filter(tags=tags) if tags else self.dbt.models()

        generated = []
        for model in models:
            cube_yaml = self._render_cube(model)
            output_path = output_dir / f"{model.name}.yaml"
            output_path.write_text(cube_yaml)
            generated.append(output_path)

        return generated

    def _render_cube(self, model) -> str:
        """Render a dbt model as a Cube cube definition."""
        cube_def = model.as_cube()
        dimensions = model.as_dimensions()

        return f"""
cubes:
  - name: {model.name}
    sql_table: {cube_def['sql_table']}

    dimensions:
{self._format_dimensions(dimensions)}

    measures:
      - name: count
        type: count
"""

    def _format_dimensions(self, dimensions: list[dict]) -> str:
        lines = []
        for dim in dimensions:
            lines.append(f"      - name: {dim['name']}")
            lines.append(f"        sql: {dim['sql']}")
            lines.append(f"        type: {dim['type']}")
        return "\n".join(lines)
```

```python
# floe_cube/security.py
from typing import Any

class CubeSecurityContext:
    """Build Cube security context for row-level security."""

    def __init__(self, tenant_column: str = "tenant_id"):
        self.tenant_column = tenant_column

    def build_query_rewrite(self, tenant_id: str) -> dict[str, Any]:
        """Build queryRewrite filter for tenant isolation."""
        return {
            "filters": [
                {
                    "member": f"*.{self.tenant_column}",
                    "operator": "equals",
                    "values": [tenant_id],
                }
            ]
        }

    def build_security_context(
        self,
        tenant_id: str,
        user_id: str | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build full security context for Cube."""
        return {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "roles": roles or [],
        }
```

```python
# floe_cube/lineage.py
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Job, Run, Dataset

class CubeLineageEmitter:
    """Emit OpenLineage events for Cube queries."""

    def __init__(self, client: OpenLineageClient, namespace: str):
        self.client = client
        self.namespace = namespace

    def emit_query_event(
        self,
        query_id: str,
        cube_name: str,
        input_tables: list[str],
        pre_aggregation: str | None = None,
    ):
        """Emit lineage event for a Cube query."""
        inputs = [
            Dataset(namespace=self.namespace, name=table)
            for table in input_tables
        ]

        outputs = []
        if pre_aggregation:
            outputs.append(
                Dataset(namespace=self.namespace, name=f"preagg_{pre_aggregation}")
            )

        event = RunEvent(
            eventType=RunState.COMPLETE,
            job=Job(namespace=self.namespace, name=f"cube.{cube_name}"),
            run=Run(runId=query_id),
            inputs=inputs,
            outputs=outputs,
        )

        self.client.emit(event)
```

### 8.4 Deployment Components

Cube requires multiple components for production deployment:

| Component | Purpose | Replicas |
|-----------|---------|----------|
| Cube API | Handle REST/GraphQL/SQL queries | 2+ (horizontal) |
| Cube Refresh Worker | Build pre-aggregations | 1 |
| Cube Store Router | Route queries to workers | 1 |
| Cube Store Workers | Execute cached queries | 2+ (horizontal) |

```yaml
# charts/floe-cube/values.yaml
cube:
  api:
    replicas: 2
    image: cubejs/cube:latest
    resources:
      requests:
        cpu: 500m
        memory: 1Gi

  refreshWorker:
    enabled: true
    replicas: 1

  store:
    router:
      replicas: 1
    workers:
      replicas: 2
      persistence:
        enabled: true
        size: 50Gi
        storageClass: standard
```

---

## 9. Package Summary

| Package | Lines (est.) | Dependencies |
|---------|--------------|--------------|
| floe-core | 1,500 | pydantic, pyyaml |
| floe-cli | 1,000 | click, rich, floe-core |
| floe-dagster | 1,200 | dagster, dagster-dbt, floe-core |
| floe-dbt | 800 | dbt-core, floe-core |
| floe-iceberg | 600 | pyiceberg, floe-core |
| floe-polaris | 400 | pyiceberg, floe-core |
| floe-cube | 800 | cube_dbt, floe-core |

### Dependency Graph

```
External Dependencies:
├── pydantic (core)
├── pyyaml (core)
├── click (cli)
├── rich (cli)
├── dagster (dagster)
├── dagster-dbt (dagster)
├── dbt-core (dbt)
├── dbt-duckdb (dbt, optional)
├── dbt-snowflake (dbt, optional)
├── pyiceberg (iceberg, polaris)
├── cube_dbt (cube)
├── opentelemetry-api (all)
└── openlineage-python (dagster, cube)
```
