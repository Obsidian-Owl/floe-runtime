# Research: Orchestration Layer

**Research Date**: 2025-12-16
**Feature**: 003-orchestration-layer
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Table of Contents

1. [dagster-dbt 0.25+ Integration Patterns](#1-dagster-dbt-025-integration-patterns)
2. [dbt profiles.yml Structure for 7 Targets](#2-dbt-profilesyml-structure-for-7-targets)
3. [OpenLineage Python SDK](#3-openlineage-python-sdk)
4. [OpenTelemetry Python SDK](#4-opentelemetry-python-sdk)
5. [dbt manifest.json Structure](#5-dbt-manifestjson-structure)
6. [dagster-dbt Lineage Hook Points](#6-dagster-dbt-lineage-hook-points)
7. [Structlog + OpenTelemetry Integration](#7-structlog--opentelemetry-integration)
8. [Graceful Degradation Patterns](#8-graceful-degradation-patterns)

---

## 1. dagster-dbt 0.25+ Integration Patterns

### Core Components

The dagster-dbt integration uses three main components:

| Component | Purpose |
|-----------|---------|
| `@dbt_assets` | Decorator to create Dagster assets from dbt manifest |
| `DbtCliResource` | Resource for executing dbt CLI commands |
| `DbtProject` | Helper for managing dbt project paths and manifest |

### @dbt_assets Decorator Pattern

```python
from __future__ import annotations

from pathlib import Path
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject

# Option 1: Direct path to manifest
@dbt_assets(manifest=Path("target/manifest.json"))
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

# Option 2: Using DbtProject helper (recommended for floe)
dbt_project = DbtProject(
    project_dir=Path("dbt_project"),
    profiles_dir=Path(".floe/profiles"),  # Generated profiles location
)

@dbt_assets(manifest=dbt_project.manifest_path)
def floe_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
```

### DbtCliResource Configuration

```python
from dagster import Definitions, ConfigurableResource
from dagster_dbt import DbtCliResource

definitions = Definitions(
    assets=[my_dbt_assets],
    resources={
        "dbt": DbtCliResource(
            project_dir=os.fspath(dbt_project.project_dir),
            profiles_dir=os.fspath(dbt_project.profiles_dir),
        ),
    },
)
```

### DagsterDbtTranslator for Metadata

Use `DagsterDbtTranslator` to customize how dbt models map to Dagster assets:

```python
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

class FloeTranslator(DagsterDbtTranslator):
    """Custom translator to map floe metadata to Dagster assets."""

    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        """Build asset key from dbt model path."""
        return AssetKey(dbt_resource_props["name"])

    def get_description(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        """Extract description from dbt model."""
        return dbt_resource_props.get("description")

    def get_metadata(self, dbt_resource_props: Mapping[str, Any]) -> Mapping[str, Any]:
        """Extract floe metadata from dbt meta tags."""
        meta = dbt_resource_props.get("meta", {})
        floe_meta = meta.get("floe", {})
        return {
            "owner": floe_meta.get("owner"),
            "classification": floe_meta.get("classification"),
            "sla": floe_meta.get("sla"),
        }

@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=FloeTranslator(),
)
def floe_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
```

### Key Findings

- **Manifest is required**: `@dbt_assets` needs `manifest.json` at definition time
- **Profiles directory**: Use `profiles_dir` in `DbtCliResource`, NOT `profiles_dir` in `DbtProject`
- **Event streaming**: `dbt.cli().stream()` provides real-time execution events
- **Asset dependencies**: Automatically extracted from dbt `ref()` relationships

---

## 2. dbt profiles.yml Structure for 7 Targets

### Overview

dbt profiles.yml uses YAML with Jinja templating for environment variables:

```yaml
# Standard structure for all targets
<profile_name>:
  target: <default_target>
  outputs:
    <target_name>:
      type: <adapter_type>
      # Target-specific configuration...
```

### Environment Variable Templating

```yaml
# Pattern for ALL secrets (Constitution: Security First)
password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
private_key_path: "{{ env_var('DBT_PRIVATE_KEY_PATH') }}"
keyfile: "{{ env_var('GOOGLE_APPLICATION_CREDENTIALS') }}"
```

### Target-Specific Profiles

#### DuckDB (Local Development)

```yaml
floe:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('DUCKDB_PATH', 'data/warehouse.duckdb') }}"
      threads: 4
      extensions:
        - parquet
        - iceberg
```

#### Snowflake

```yaml
floe:
  target: prod
  outputs:
    prod:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE', 'TRANSFORMER') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      schema: "{{ env_var('SNOWFLAKE_SCHEMA', 'PUBLIC') }}"
      threads: 4
      query_tag: "dbt"
```

#### BigQuery

```yaml
floe:
  target: prod
  outputs:
    prod:
      type: bigquery
      method: service-account  # or oauth
      project: "{{ env_var('GCP_PROJECT') }}"
      dataset: "{{ env_var('BQ_DATASET') }}"
      keyfile: "{{ env_var('GOOGLE_APPLICATION_CREDENTIALS') }}"
      threads: 4
      location: "{{ env_var('BQ_LOCATION', 'US') }}"
      maximum_bytes_billed: 1000000000000  # 1TB limit
```

#### Redshift

```yaml
floe:
  target: prod
  outputs:
    prod:
      type: redshift
      host: "{{ env_var('REDSHIFT_HOST') }}"
      port: 5439
      user: "{{ env_var('REDSHIFT_USER') }}"
      password: "{{ env_var('REDSHIFT_PASSWORD') }}"
      dbname: "{{ env_var('REDSHIFT_DATABASE') }}"
      schema: "{{ env_var('REDSHIFT_SCHEMA', 'public') }}"
      threads: 4
      ra3_node: true
```

#### Databricks

```yaml
floe:
  target: prod
  outputs:
    prod:
      type: databricks
      catalog: "{{ env_var('DATABRICKS_CATALOG', 'hive_metastore') }}"
      schema: "{{ env_var('DATABRICKS_SCHEMA') }}"
      host: "{{ env_var('DATABRICKS_HOST') }}"
      http_path: "{{ env_var('DATABRICKS_HTTP_PATH') }}"
      token: "{{ env_var('DATABRICKS_TOKEN') }}"
      threads: 4
```

#### PostgreSQL

```yaml
floe:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('POSTGRES_HOST', 'localhost') }}"
      port: "{{ env_var('POSTGRES_PORT', '5432') | int }}"
      user: "{{ env_var('POSTGRES_USER') }}"
      password: "{{ env_var('POSTGRES_PASSWORD') }}"
      dbname: "{{ env_var('POSTGRES_DATABASE') }}"
      schema: "{{ env_var('POSTGRES_SCHEMA', 'public') }}"
      threads: 4
```

#### Spark

```yaml
floe:
  target: prod
  outputs:
    prod:
      type: spark
      method: thrift  # or odbc, session, http
      host: "{{ env_var('SPARK_HOST') }}"
      port: 10000
      schema: "{{ env_var('SPARK_SCHEMA', 'default') }}"
      threads: 4
```

### Profile Generation Factory Pattern

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from floe_core.compiler.models import CompiledArtifacts

class ProfileGenerator(ABC):
    """Base class for profile generators."""

    @abstractmethod
    def generate(self, artifacts: CompiledArtifacts) -> dict[str, Any]:
        """Generate profile configuration for this target."""
        ...

class DuckDBProfileGenerator(ProfileGenerator):
    def generate(self, artifacts: CompiledArtifacts) -> dict[str, Any]:
        return {
            "type": "duckdb",
            "path": "{{ env_var('DUCKDB_PATH', 'data/warehouse.duckdb') }}",
            "threads": artifacts.compute.properties.get("threads", 4),
        }

# Factory pattern
GENERATORS: dict[str, type[ProfileGenerator]] = {
    "duckdb": DuckDBProfileGenerator,
    "snowflake": SnowflakeProfileGenerator,
    "bigquery": BigQueryProfileGenerator,
    "redshift": RedshiftProfileGenerator,
    "databricks": DatabricksProfileGenerator,
    "postgres": PostgreSQLProfileGenerator,
    "spark": SparkProfileGenerator,
}

def generate_profile(target: str, artifacts: CompiledArtifacts) -> dict[str, Any]:
    """Generate profile for the specified compute target."""
    generator_class = GENERATORS.get(target)
    if not generator_class:
        raise ValueError(f"Unsupported target: {target}")
    return generator_class().generate(artifacts)
```

---

## 3. OpenLineage Python SDK

### Core Concepts

OpenLineage uses **RunEvents** to track job execution state:

| Event Type | When Emitted |
|------------|--------------|
| `START` | Job begins execution |
| `RUNNING` | Progress updates (optional) |
| `COMPLETE` | Job finishes successfully |
| `FAIL` | Job fails with error |
| `ABORT` | Job is cancelled |

### Creating RunEvents

```python
from __future__ import annotations

from datetime import datetime
import uuid

from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job, Dataset
from openlineage.client.facet import (
    SchemaDatasetFacet,
    SchemaDatasetFacetFields,
    DataSourceDatasetFacet,
)

def emit_lineage_event(
    client: OpenLineageClient,
    event_type: RunState,
    job_namespace: str,
    job_name: str,
    run_id: str,
    inputs: list[Dataset] | None = None,
    outputs: list[Dataset] | None = None,
) -> None:
    """Emit an OpenLineage event."""
    client.emit(
        RunEvent(
            eventType=event_type,
            eventTime=datetime.now().isoformat() + "Z",
            run=Run(runId=run_id),
            job=Job(namespace=job_namespace, name=job_name),
            inputs=inputs or [],
            outputs=outputs or [],
            producer="floe-dagster",
        )
    )
```

### Building Datasets with Facets

```python
from openlineage.client.run import Dataset
from openlineage.client.facet import SchemaDatasetFacet, SchemaDatasetFacetFields

def build_dataset_from_dbt_model(
    node: dict[str, Any],
    manifest: dict[str, Any],
) -> Dataset:
    """Build OpenLineage Dataset from dbt model node."""
    database = node.get("database", "unknown")
    schema = node.get("schema", "unknown")
    name = node.get("alias") or node.get("name")

    # Build namespace from adapter type
    adapter_type = manifest.get("metadata", {}).get("adapter_type", "unknown")
    namespace = f"{adapter_type}://production"

    # Build schema facet from columns
    fields = [
        SchemaDatasetFacetFields(
            name=col_name,
            type=col_info.get("data_type", "unknown"),
            description=col_info.get("description"),
        )
        for col_name, col_info in node.get("columns", {}).items()
    ]

    return Dataset(
        namespace=namespace,
        name=f"{database}.{schema}.{name}",
        facets={
            "schema": SchemaDatasetFacet(fields=fields),
            "dataSource": DataSourceDatasetFacet(
                name=database,
                uri=f"{adapter_type}://{database}",
            ),
        },
    )
```

### Custom Facet for Column Classifications

```python
from __future__ import annotations

from typing import Any
from openlineage.client.facet import BaseFacet
from pydantic import Field

class FloeColumnClassificationFacet(BaseFacet):
    """Custom facet for floe column classifications.

    Extends OpenLineage with governance metadata from dbt meta.floe tags.
    """

    _additional_skip_redact: list[str] = ["classifications"]

    classifications: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Column name to classification metadata mapping",
    )

    @classmethod
    def _get_schema(cls) -> str:
        return "https://floe.dev/spec/facets/1-0-0/ColumnClassificationFacet.json"

def build_classification_facet(
    columns: dict[str, Any],
) -> FloeColumnClassificationFacet | None:
    """Build classification facet from dbt column meta."""
    classifications = {}

    for col_name, col_info in columns.items():
        floe_meta = col_info.get("meta", {}).get("floe", {})
        if floe_meta:
            classifications[col_name] = {
                "classification": floe_meta.get("classification"),
                "pii_type": floe_meta.get("pii_type"),
                "sensitivity": floe_meta.get("sensitivity"),
            }

    if classifications:
        return FloeColumnClassificationFacet(classifications=classifications)
    return None
```

### OpenLineageClient Configuration

```python
from openlineage.client import OpenLineageClient
from openlineage.client.transport.http import HttpConfig, HttpCompression

# Standard client (synchronous)
client = OpenLineageClient(url="http://localhost:5000")

# Async client (recommended for production)
config = HttpConfig(
    url="http://localhost:5000",
    timeout=5.0,
    verify=True,
    compression=HttpCompression.GZIP,
)
client = OpenLineageClient(transport=config)
```

---

## 4. OpenTelemetry Python SDK

### Core Components

| Component | Purpose |
|-----------|---------|
| `TracerProvider` | Factory for creating tracers |
| `Tracer` | Creates spans for operations |
| `Span` | Represents a unit of work |
| `SpanProcessor` | Processes spans (batch/simple) |
| `SpanExporter` | Exports spans to backends |

### Basic Setup

```python
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

def configure_tracing(
    service_name: str = "floe-dagster",
    otlp_endpoint: str | None = None,
) -> None:
    """Configure OpenTelemetry tracing."""
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
```

### Creating Spans

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

def materialize_asset(asset_name: str, context: AssetExecutionContext) -> None:
    """Materialize a dbt asset with tracing."""
    with tracer.start_as_current_span(
        "dbt_asset_materialization",
        attributes={
            "asset.name": asset_name,
            "dagster.run_id": context.run_id,
            "compute.target": "snowflake",
        },
    ) as span:
        try:
            # Execute dbt model
            result = execute_dbt_model(asset_name)

            span.set_attribute("dbt.execution_time", result.execution_time)
            span.set_attribute("dbt.rows_affected", result.rows_affected)
            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
```

### Graceful Degradation with NoOp Provider

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import NoOpTracerProvider

def configure_tracing(otlp_endpoint: str | None) -> None:
    """Configure tracing with graceful degradation."""
    if otlp_endpoint:
        # Full tracing with export
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    else:
        # NoOp provider - spans are created but not exported
        trace.set_tracer_provider(NoOpTracerProvider())
        logger.info("Tracing disabled - no OTLP endpoint configured")
```

### Context Propagation

```python
from opentelemetry.propagate import inject, extract
from opentelemetry import context

def propagate_context_to_subprocess() -> dict[str, str]:
    """Extract trace context for subprocess."""
    carrier: dict[str, str] = {}
    inject(carrier)
    return carrier

def receive_context_from_parent(carrier: dict[str, str]) -> None:
    """Restore trace context from parent process."""
    ctx = extract(carrier)
    context.attach(ctx)
```

---

## 5. dbt manifest.json Structure

### Key Sections

| Section | Purpose |
|---------|---------|
| `nodes` | All compiled nodes (models, tests, seeds, etc.) |
| `sources` | Source definitions |
| `parent_map` | Node → list of parent node IDs |
| `child_map` | Node → list of child node IDs |
| `metadata` | Project metadata, adapter type |

### Node Structure (Model)

```json
{
  "unique_id": "model.my_project.customers",
  "resource_type": "model",
  "name": "customers",
  "alias": "customers",
  "schema": "analytics",
  "database": "warehouse",
  "description": "Customer dimension table",
  "tags": ["pii", "tier1"],
  "config": {
    "materialized": "table",
    "schema": "analytics"
  },
  "depends_on": {
    "macros": [],
    "nodes": [
      "model.my_project.stg_customers",
      "model.my_project.stg_orders"
    ]
  },
  "columns": {
    "customer_id": {
      "name": "customer_id",
      "description": "Primary key",
      "data_type": "integer",
      "meta": {
        "floe": {
          "classification": "internal",
          "owner": "analytics-team"
        }
      }
    },
    "email": {
      "name": "email",
      "description": "Customer email address",
      "data_type": "varchar",
      "meta": {
        "floe": {
          "classification": "pii",
          "pii_type": "email",
          "sensitivity": "high"
        }
      }
    }
  },
  "meta": {
    "floe": {
      "owner": "data-platform",
      "sla": "tier1"
    }
  }
}
```

### Extracting Column Classifications

```python
def extract_column_classifications(
    node: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Extract floe column classifications from dbt node.

    Classifications are stored in columns[].meta.floe namespace.
    """
    classifications = {}

    for col_name, col_info in node.get("columns", {}).items():
        floe_meta = col_info.get("meta", {}).get("floe", {})
        if floe_meta:
            classifications[col_name] = {
                "classification": floe_meta.get("classification"),
                "pii_type": floe_meta.get("pii_type"),
                "sensitivity": floe_meta.get("sensitivity"),
            }

    return classifications
```

### Building Dependency Graph

```python
def build_dependency_graph(
    manifest: dict[str, Any],
) -> dict[str, list[str]]:
    """Build model dependency graph from manifest.

    Uses parent_map for upstream dependencies.
    """
    dependencies = {}

    for node_id, parents in manifest.get("parent_map", {}).items():
        if node_id.startswith("model."):
            # Filter to only model parents (not sources, macros)
            model_parents = [
                p for p in parents
                if p.startswith("model.") or p.startswith("source.")
            ]
            dependencies[node_id] = model_parents

    return dependencies
```

---

## 6. dagster-dbt Lineage Hook Points

### Hook Points Overview

Three main patterns for custom OpenLineage emission:

1. **Before/After Invocation**: Code before/after `yield from dbt.cli().stream()`
2. **Raw Event Interception**: Use `stream_raw_events()` for per-model events
3. **Post-Execution Artifacts**: Access `run_results.json` and `manifest.json`

### Recommended Pattern: Post-Execution Processing

```python
@dbt_assets(manifest=Path("target/manifest.json"))
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """dbt assets with post-execution OpenLineage emission."""

    # Execute dbt and capture invocation
    dbt_invocation = dbt.cli(["build"], context=context)
    yield from dbt_invocation.stream()

    # Access artifacts after execution
    manifest = dbt_invocation.get_artifact("manifest.json")
    run_results = dbt_invocation.get_artifact("run_results.json")

    # Emit OpenLineage events with full metadata
    emit_lineage_events(
        context=context,
        manifest=manifest,
        run_results=run_results,
        openlineage_client=openlineage_client,
    )
```

### Per-Model Event Interception

```python
@dbt_assets(manifest=Path("target/manifest.json"))
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """dbt assets with per-model OpenLineage emission."""

    dbt_invocation = dbt.cli(["build"], context=context)

    for raw_event in dbt_invocation.stream_raw_events():
        # Extract node info from dbt structured log
        node_info = raw_event.raw_event.get("data", {}).get("node_info", {})

        if node_info:
            unique_id = node_info.get("unique_id", "")
            node_status = node_info.get("node_status")

            # Emit OpenLineage events based on status
            if node_status == "started" and unique_id.startswith("model."):
                emit_start_event(unique_id, node_info)
            elif node_status in ("success", "error", "fail"):
                emit_complete_event(unique_id, node_info, node_status)

        # Yield Dagster events
        for dagster_event in raw_event.to_default_asset_events(context=context):
            yield dagster_event
```

### dbt Structured Log Event Structure

```json
{
  "data": {
    "node_info": {
      "unique_id": "model.my_project.customers",
      "node_name": "customers",
      "node_status": "started",
      "node_relation": {
        "database": "warehouse",
        "schema": "analytics",
        "alias": "customers"
      },
      "materialized": "table",
      "resource_type": "model"
    }
  },
  "info": {
    "code": "Q011",
    "level": "info",
    "ts": "2025-12-16T10:30:45.123456Z"
  }
}
```

### Key Fields for OpenLineage

| Field | Purpose |
|-------|---------|
| `node_info.unique_id` | Unique model identifier for job name |
| `node_info.node_status` | Execution state (started, success, error, fail) |
| `node_info.node_relation` | Database/schema/table for Dataset namespace/name |
| `info.ts` | Event timestamp |

---

## 7. Structlog + OpenTelemetry Integration

### Custom Processor for Trace Context

```python
from __future__ import annotations

from typing import Any
from opentelemetry import trace

def add_trace_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add OpenTelemetry trace context to structlog event dictionary.

    Injects trace_id and span_id for log-trace correlation in
    observability backends.
    """
    span = trace.get_current_span()

    if span.is_recording():
        ctx = span.get_span_context()
        # W3C Trace Context format: lowercase hex
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")

    return event_dict
```

### Complete Configuration

```python
import structlog

def configure_structlog() -> None:
    """Configure structlog with OpenTelemetry trace context injection."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            add_trace_context,  # Inject trace context
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Example Log Output

```json
{
  "event": "dbt_model_materialized",
  "model": "customers",
  "duration_ms": 1234,
  "timestamp": "2025-12-16T10:30:45.123456Z",
  "level": "info",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

---

## 8. Graceful Degradation Patterns

### Constitution Requirement

> FR-021: System MUST function without OpenLineage endpoint (lineage disabled gracefully)
> FR-022: System MUST function without OTLP endpoint (traces disabled gracefully)

### OpenLineage Graceful Degradation

```python
from __future__ import annotations

import logging
from openlineage.client import OpenLineageClient

logger = logging.getLogger(__name__)

class NoOpOpenLineageClient:
    """No-op client for when OpenLineage is disabled."""

    def emit(self, event: RunEvent) -> None:
        """Log event but don't send anywhere."""
        logger.debug(
            "OpenLineage event (disabled)",
            extra={
                "event_type": event.eventType.value,
                "job_name": event.job.name,
            }
        )

def create_openlineage_client(
    endpoint: str | None,
) -> OpenLineageClient | NoOpOpenLineageClient:
    """Create OpenLineage client with graceful degradation."""
    if endpoint:
        try:
            client = OpenLineageClient(url=endpoint)
            logger.info("OpenLineage enabled", endpoint=endpoint)
            return client
        except Exception as e:
            logger.warning(
                "OpenLineage client creation failed, using no-op",
                error=str(e),
            )
            return NoOpOpenLineageClient()
    else:
        logger.info("OpenLineage disabled - no endpoint configured")
        return NoOpOpenLineageClient()
```

### OpenTelemetry Graceful Degradation

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import NoOpTracerProvider

def configure_tracing(
    otlp_endpoint: str | None,
    service_name: str = "floe-dagster",
) -> None:
    """Configure OpenTelemetry with graceful degradation.

    When no endpoint is configured, uses NoOpTracerProvider which
    creates valid spans but doesn't export them.
    """
    if otlp_endpoint:
        try:
            resource = Resource.create({SERVICE_NAME: service_name})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            logger.info("OpenTelemetry enabled", endpoint=otlp_endpoint)
        except Exception as e:
            logger.warning(
                "OpenTelemetry setup failed, using no-op",
                error=str(e),
            )
            trace.set_tracer_provider(NoOpTracerProvider())
    else:
        # NoOp provider - spans created but not exported
        trace.set_tracer_provider(NoOpTracerProvider())
        logger.info("OpenTelemetry disabled - no endpoint configured")
```

### Error Isolation Pattern

```python
def emit_lineage_safe(
    client: OpenLineageClient,
    event: RunEvent,
) -> None:
    """Emit OpenLineage event with error isolation.

    Never fails dbt execution due to lineage emission errors.
    """
    try:
        client.emit(event)
    except Exception as e:
        # Log error but don't fail pipeline
        logger.error(
            "OpenLineage emission failed",
            error=str(e),
            event_type=event.eventType.value,
            job_name=event.job.name,
        )
        # Optionally emit metric for monitoring
        emit_lineage_failure_metric()
```

---

## Key Implementation Decisions

Based on research findings:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| OpenLineage emission timing | Post-execution | Full metadata from manifest + run_results |
| OpenLineage transport | Async HTTP | Non-blocking, event ordering guarantees |
| OTel provider when disabled | NoOpTracerProvider | Valid spans created, API works, no export overhead |
| Profile generation pattern | Factory with generators | Clean separation per target, easy to extend |
| dbt meta namespace | `meta.floe.*` | Clear ownership, avoid conflicts |
| Trace context in logs | Flat fields | Simpler querying in observability backends |

---

## Sources

- [Dagster dbt Integration](https://docs.dagster.io/integrations/libraries/dbt)
- [dagster-dbt API Reference](https://docs.dagster.io/api/libraries/dagster-dbt)
- [dbt Profiles Documentation](https://docs.getdbt.com/docs/core/connect-data-platform/profiles.yml)
- [OpenLineage Python Client](https://openlineage.io/docs/client/python/)
- [OpenLineage Spec](https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md)
- [OpenTelemetry Python](https://opentelemetry-python.readthedocs.io/)
- [Structlog Frameworks](https://www.structlog.org/en/stable/frameworks.html)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
