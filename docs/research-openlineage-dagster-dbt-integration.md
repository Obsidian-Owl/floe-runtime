# Research: OpenLineage Emission During dagster-dbt Asset Execution

**Research Date**: 2025-12-16
**Purpose**: Document hook points, event interception patterns, and best practices for emitting custom OpenLineage events during dagster-dbt asset execution.

---

## Table of Contents

1. [Hook Points in @dbt_assets](#hook-points-in-dbt_assets)
2. [Intercepting dbt Execution Events](#intercepting-dbt-execution-events)
3. [Accessing dbt Run Results](#accessing-dbt-run-results)
4. [OpenLineage Emission Patterns](#openlineage-emission-patterns)
5. [Best Practices](#best-practices)
6. [Complete Implementation Examples](#complete-implementation-examples)

---

## Hook Points in @dbt_assets

### 1. Before/After dbt Invocation (Primary Pattern)

The `@dbt_assets` decorator allows custom code execution before and after dbt commands:

```python
from __future__ import annotations

from pathlib import Path
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets

@dbt_assets(manifest=Path("target/manifest.json"))
def jaffle_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    # HOOK POINT 1: Before dbt execution
    context.log.info("Custom code before dbt invocation")
    emit_openlineage_start_event(context)

    # Execute dbt and stream events
    yield from dbt.cli(["build"], context=context).stream()

    # HOOK POINT 2: After dbt execution
    context.log.info("Custom code after dbt invocation")
    emit_openlineage_complete_event(context)
```

**Key Points**:
- Custom code runs in the main execution flow
- Access to full `AssetExecutionContext`
- Synchronous execution (blocking)
- Suitable for critical pre/post-processing

### 2. Asset-Level Hooks (Success/Failure)

Dagster supports `hooks` argument on `@asset` decorator for success/failure callbacks:

```python
from __future__ import annotations

from dagster import asset, success_hook, failure_hook, HookContext

@success_hook
def openlineage_success_hook(context: HookContext) -> None:
    """Emit OpenLineage COMPLETE event on asset success."""
    context.log.info(f"Asset {context.op.name} succeeded")
    # Emit OpenLineage COMPLETE event
    emit_openlineage_complete(context)

@failure_hook
def openlineage_failure_hook(context: HookContext) -> None:
    """Emit OpenLineage FAIL event on asset failure."""
    context.log.error(f"Asset {context.op.name} failed")
    # Emit OpenLineage FAIL event
    emit_openlineage_fail(context)

@asset(hooks={openlineage_success_hook, openlineage_failure_hook})
def my_asset(context: AssetExecutionContext):
    # Asset logic
    pass
```

**Limitations**:
- Only triggers on success/failure (not per-model events)
- Not directly compatible with `@dbt_assets` (requires `@asset`)
- Cannot be applied to `define_asset_job()` - use RunStatusSensor instead

### 3. Custom DbtProjectComponent Subclass

For advanced use cases, subclass `DbtProjectComponent` to override the `execute` method:

```python
from __future__ import annotations

import dagster as dg
from dagster_dbt import DbtProjectComponent

class OpenLineageDbtProjectComponent(DbtProjectComponent):
    """Custom DbtProjectComponent with OpenLineage emission."""

    def execute(
        self,
        context: dg.AssetExecutionContext,
        dbt: DbtCliResource
    ) -> Iterator[dg.Output | dg.AssetObservation]:
        """Override execute to add OpenLineage emission."""
        # Emit START event
        context.log.info("Starting custom dbt execution with OpenLineage")
        emit_openlineage_start(context)

        # Call parent execute method
        yield from super().execute(context, dbt)

        # Emit COMPLETE event
        context.log.info("Completed custom dbt execution")
        emit_openlineage_complete(context)
```

**Advantages**:
- Full control over execution lifecycle
- Can add custom op configuration via `op_config_schema`
- Can override `get_asset_spec` for custom metadata
- Encapsulates OpenLineage logic in reusable component

---

## Intercepting dbt Execution Events

### DbtCliEventMessage: Raw Event Access

The `DbtCliEventMessage` class provides access to raw dbt structured logging events:

```python
from __future__ import annotations

from pathlib import Path
from typing import Iterator, Any
from dagster import AssetExecutionContext, Output, AssetObservation
from dagster_dbt import DbtCliResource, dbt_assets, DbtCliEventMessage

@dbt_assets(manifest=Path("target/manifest.json"))
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """dbt assets with per-model event interception."""
    dbt_invocation = dbt.cli(["build"], context=context)

    # Stream raw events and intercept each one
    for raw_event in dbt_invocation.stream_raw_events():
        # Access raw dbt structured log
        raw_dict: dict[str, Any] = raw_event.raw_event

        # Parse event metadata
        event_info = raw_dict.get("info", {})
        event_data = raw_dict.get("data", {})
        node_info = event_data.get("node_info", {})

        # Check model status
        node_status = node_info.get("node_status")  # "started" | "success" | "error" | "fail"
        unique_id = node_info.get("unique_id")  # "model.project.model_name"

        # Emit OpenLineage events based on status
        if node_status == "started":
            context.log.info(f"Model started: {unique_id}")
            emit_openlineage_model_start(context, unique_id, node_info)
        elif node_status in ("success", "error", "fail"):
            context.log.info(f"Model {node_status}: {unique_id}")
            emit_openlineage_model_complete(context, unique_id, node_info, node_status)

        # Convert to Dagster events and yield
        for dagster_event in raw_event.to_default_asset_events(context=context):
            yield dagster_event
```

### dbt Structured Logging Event Structure

dbt emits structured logs in the following format (see [dbt Events and Logs](https://docs.getdbt.com/reference/events-logging)):

```json
{
  "data": {
    "description": "sql view model dbt_jcohen.my_model",
    "index": 1,
    "node_info": {
      "materialized": "view",
      "node_name": "my_model",
      "node_path": "my_model.sql",
      "node_relation": {
        "alias": "my_model",
        "database": "my_database",
        "schema": "my_schema"
      },
      "node_started_at": "2023-04-12T19:27:27.435364",
      "node_status": "started",
      "resource_type": "model",
      "unique_id": "model.my_dbt_project.my_model"
    },
    "total": 1
  },
  "info": {
    "code": "Q011",
    "level": "info",
    "msg": "1 of 1 START sql view model my_database.my_model ... [RUN]",
    "name": "LogStartLine",
    "ts": "2023-04-12T19:27:27.436283Z"
  }
}
```

**Key Fields for OpenLineage**:
- `node_info.unique_id`: Unique model identifier
- `node_info.node_status`: Running status (`started` | `compiling` | `executing`) or final status (`success` | `error` | `fail` | `warn` | `skipped`)
- `node_info.node_relation`: Database/schema/table information (for Dataset namespace/name)
- `node_info.materialized`: Materialization type (view, table, incremental, etc.)
- `info.ts`: Event timestamp

### Custom Event Filter Wrapper

Create a custom wrapper to filter and process events:

```python
from __future__ import annotations

from typing import Iterator
from dagster import Output, AssetObservation
from dagster_dbt import DbtCliEventMessage

def process_dbt_events_with_lineage(
    context: AssetExecutionContext,
    raw_events: Iterator[DbtCliEventMessage],
    openlineage_client: OpenLineageClient
) -> Iterator[Output | AssetObservation]:
    """Process dbt events and emit OpenLineage events in parallel."""

    for raw_event in raw_events:
        # Extract node info
        node_info = raw_event.raw_event.get("data", {}).get("node_info", {})

        if node_info:
            unique_id = node_info.get("unique_id")
            node_status = node_info.get("node_status")

            # Emit OpenLineage events based on status
            if node_status == "started":
                # Non-blocking emission
                emit_model_start_event_async(
                    openlineage_client,
                    unique_id,
                    node_info
                )
            elif node_status in ("success", "error", "fail"):
                emit_model_complete_event_async(
                    openlineage_client,
                    unique_id,
                    node_info,
                    node_status
                )

        # Yield Dagster events
        for dagster_event in raw_event.to_default_asset_events(context=context):
            yield dagster_event
```

---

## Accessing dbt Run Results

### Using get_artifact() for run_results.json

After dbt execution, access `run_results.json` to get detailed execution metadata:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets

@dbt_assets(manifest=Path("target/manifest.json"))
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """dbt assets with run_results.json access."""

    # Execute dbt and capture invocation
    dbt_invocation = dbt.cli(["build"], context=context)

    # Stream events (must consume generator!)
    yield from dbt_invocation.stream()

    # Access run_results.json after execution
    run_results: dict[str, Any] = dbt_invocation.get_artifact("run_results.json")

    # Parse results by model
    for result in run_results.get("results", []):
        unique_id = result["unique_id"]
        status = result["status"]  # "success" | "error" | "fail" | "skipped"
        execution_time = result["execution_time"]
        rows_affected = result.get("adapter_response", {}).get("rows_affected")

        context.log.info(
            f"Model {unique_id}: {status} "
            f"(execution_time={execution_time}s, rows_affected={rows_affected})"
        )

        # Emit final OpenLineage event with execution metadata
        emit_openlineage_with_stats(
            unique_id=unique_id,
            status=status,
            execution_time=execution_time,
            rows_affected=rows_affected
        )
```

### Accessing manifest.json for Lineage

Use `manifest.json` to extract input/output dataset lineage:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any
from dagster_dbt import DbtCliResource, dbt_assets

@dbt_assets(manifest=Path("target/manifest.json"))
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """dbt assets with manifest.json access for lineage."""

    # Execute dbt
    dbt_invocation = dbt.cli(["build"], context=context)
    yield from dbt_invocation.stream()

    # Access manifest.json
    manifest: dict[str, Any] = dbt_invocation.get_artifact("manifest.json")

    # Extract lineage for each model
    for node_id, node in manifest.get("nodes", {}).items():
        if node["resource_type"] == "model":
            model_name = node["name"]
            depends_on = node.get("depends_on", {}).get("nodes", [])

            context.log.info(
                f"Model {model_name} depends on: {depends_on}"
            )

            # Build OpenLineage Dataset objects
            input_datasets = build_input_datasets(depends_on, manifest)
            output_dataset = build_output_dataset(node)

            # Emit OpenLineage event with full lineage
            emit_openlineage_event(
                job_name=f"dbt.{model_name}",
                inputs=input_datasets,
                outputs=[output_dataset]
            )
```

### Mapping run_results to manifest for Complete Metadata

Combine both artifacts for comprehensive lineage:

```python
from __future__ import annotations

from typing import Any

def emit_complete_lineage(
    context: AssetExecutionContext,
    dbt_invocation: DbtCliInvocation
) -> None:
    """Emit complete OpenLineage events with both runtime and static metadata."""

    # Get both artifacts
    manifest: dict[str, Any] = dbt_invocation.get_artifact("manifest.json")
    run_results: dict[str, Any] = dbt_invocation.get_artifact("run_results.json")

    # Build mapping of unique_id to run result
    results_by_id = {
        result["unique_id"]: result
        for result in run_results["results"]
    }

    # Emit lineage for each model
    for unique_id, result in results_by_id.items():
        # Get static metadata from manifest
        node = manifest["nodes"].get(unique_id)
        if not node:
            continue

        # Extract lineage from manifest
        depends_on = node.get("depends_on", {}).get("nodes", [])
        input_datasets = [
            build_dataset_from_node(manifest["nodes"][dep_id])
            for dep_id in depends_on
            if dep_id in manifest["nodes"]
        ]

        # Extract runtime metadata from run_results
        output_dataset = build_dataset_from_node(node)
        output_dataset.facets["outputStatistics"] = {
            "rowCount": result.get("adapter_response", {}).get("rows_affected"),
            "size": None  # Not available from dbt
        }

        # Emit OpenLineage RunEvent
        openlineage_client.emit(
            RunEvent(
                eventType=RunState.COMPLETE,
                eventTime=datetime.now().isoformat(),
                run=Run(runId=str(uuid.uuid4())),
                job=Job(namespace="dbt", name=node["name"]),
                inputs=input_datasets,
                outputs=[output_dataset],
                producer="floe-dagster"
            )
        )
```

---

## OpenLineage Emission Patterns

### 1. Synchronous vs. Asynchronous Emission

#### Synchronous Emission (Blocking)

```python
from __future__ import annotations

from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job, Dataset

def emit_openlineage_sync(
    client: OpenLineageClient,
    event_type: RunState,
    job_name: str,
    inputs: list[Dataset] | None = None,
    outputs: list[Dataset] | None = None
) -> None:
    """Emit OpenLineage event synchronously (blocking)."""

    client.emit(
        RunEvent(
            eventType=event_type,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=str(uuid.uuid4())),
            job=Job(namespace="dbt", name=job_name),
            inputs=inputs or [],
            outputs=outputs or [],
            producer="floe-dagster"
        )
    )
```

**Use case**: Critical lineage events where you need confirmation of emission

#### Asynchronous Emission (Non-Blocking) - RECOMMENDED

OpenLineage Python client (>= 1.0.0) supports asynchronous HTTP transport:

```python
from __future__ import annotations

from openlineage.client import OpenLineageClient
from openlineage.client.transport.http import HttpConfig, HttpCompression

# Configure async HTTP transport
config = HttpConfig(
    url="http://localhost:5000",
    timeout=5.0,
    verify=True,
    compression=HttpCompression.GZIP,
    # Async configuration
    async_transport=True,  # Enable async mode
    max_workers=4,  # Concurrent workers
    queue_size=1000  # Event queue size
)

client = OpenLineageClient(transport=config)

def emit_openlineage_async(
    client: OpenLineageClient,
    event_type: RunState,
    job_name: str,
    inputs: list[Dataset] | None = None,
    outputs: list[Dataset] | None = None
) -> None:
    """Emit OpenLineage event asynchronously (non-blocking)."""

    # Emission is queued and sent asynchronously
    client.emit(
        RunEvent(
            eventType=event_type,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=str(uuid.uuid4())),
            job=Job(namespace="dbt", name=job_name),
            inputs=inputs or [],
            outputs=outputs or [],
            producer="floe-dagster"
        )
    )
    # Returns immediately without blocking
```

**Advantages**:
- Non-blocking execution
- Event ordering guarantees (START before COMPLETE)
- Bounded queues with backpressure
- Automatic retries with exponential backoff
- Real-time statistics

### 2. Building OpenLineage Datasets from dbt Metadata

```python
from __future__ import annotations

from typing import Any
from openlineage.client.run import Dataset

def build_dataset_from_dbt_node(
    node: dict[str, Any],
    manifest: dict[str, Any]
) -> Dataset:
    """Build OpenLineage Dataset from dbt node metadata."""

    # Extract relation info
    relation = node.get("relation_name") or node.get("alias")
    database = node.get("database")
    schema = node.get("schema")

    # Build namespace (e.g., "snowflake://abc123.snowflakecomputing.com")
    # Pattern: {adapter}://{host}/{database}
    adapter_type = manifest.get("metadata", {}).get("adapter_type", "unknown")
    namespace = f"{adapter_type}://production"  # Customize based on your setup

    # Build dataset name (e.g., "database.schema.table")
    dataset_name = f"{database}.{schema}.{relation}"

    # Create Dataset with facets
    return Dataset(
        namespace=namespace,
        name=dataset_name,
        facets={
            "schema": {
                "_producer": "floe-dagster",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
                "fields": [
                    {
                        "name": col["name"],
                        "type": col.get("data_type", "unknown"),
                        "description": col.get("description", "")
                    }
                    for col in node.get("columns", {}).values()
                ]
            },
            "dataSource": {
                "_producer": "floe-dagster",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
                "name": database,
                "uri": f"{adapter_type}://{database}"
            }
        }
    )
```

### 3. Dataset Namespace Best Practices

From [OpenLineage: What's in a Namespace?](https://openlineage.io/blog/whats-in-a-namespace/):

**Namespace Patterns**:
- PostgreSQL: `postgres://workshop-db:None` or `postgres://host:port`
- Snowflake: `snowflake://abc123.snowflakecomputing.com`
- BigQuery: `bigquery://project-id`
- S3/Iceberg: `s3://bucket-name` or `iceberg://catalog-name`

**Dataset Name Patterns**:
- Fully qualified: `database.schema.table`
- S3 path: `path/to/data/file.parquet`
- Iceberg table: `namespace.table`

**Key Principles**:
- Namespace uniquely identifies the data source instance
- Dataset name is unique within the namespace
- Together they form a globally unique dataset identifier
- Use consistent patterns across all jobs for lineage stitching

### 4. Handling Temporary Datasets

For intermediate/temporary datasets (e.g., dbt ephemeral models):

```python
from __future__ import annotations

from openlineage.client.run import Dataset

def build_ephemeral_dataset(node: dict[str, Any]) -> Dataset:
    """Build Dataset for ephemeral dbt model."""

    return Dataset(
        namespace="inmemory://dbt",  # Use inmemory:// for ephemeral data
        name=f"ephemeral.{node['name']}",
        facets={
            "lifecycleStateChange": {
                "_producer": "floe-dagster",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/LifecycleStateChangeDatasetFacet.json",
                "lifecycleStateChange": "CREATE"  # or "DROP" after use
            }
        }
    )
```

---

## Best Practices

### 1. Non-Blocking Lineage Emission

**Always use asynchronous transport for OpenLineage emission**:

```python
from __future__ import annotations

from openlineage.client import OpenLineageClient
from openlineage.client.transport.http import HttpConfig

# ✅ CORRECT - Async transport (non-blocking)
config = HttpConfig(
    url="http://openlineage-backend:5000",
    async_transport=True,
    max_workers=4,
    queue_size=1000
)
client = OpenLineageClient(transport=config)

# ❌ WRONG - Synchronous transport (blocks dbt execution)
client = OpenLineageClient(url="http://openlineage-backend:5000")
```

**Why**: Synchronous emission adds latency to dbt execution. Async transport queues events and sends them in the background.

### 2. Event Ordering Guarantees

Ensure START events are emitted before COMPLETE/FAIL events:

```python
from __future__ import annotations

from openlineage.client.run import RunState

def emit_model_lifecycle(
    client: OpenLineageClient,
    job_name: str,
    run_id: str,
    inputs: list[Dataset],
    outputs: list[Dataset],
    status: str  # "success" | "error" | "fail"
) -> None:
    """Emit START and COMPLETE/FAIL events with ordering guarantee."""

    # Always emit START first
    client.emit(
        RunEvent(
            eventType=RunState.START,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace="dbt", name=job_name),
            producer="floe-dagster"
        )
    )

    # Then emit COMPLETE or FAIL
    event_type = RunState.COMPLETE if status == "success" else RunState.FAIL
    client.emit(
        RunEvent(
            eventType=event_type,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace="dbt", name=job_name),
            inputs=inputs,
            outputs=outputs,
            producer="floe-dagster"
        )
    )
```

### 3. Use Consistent Run IDs

Generate run IDs from Dagster context to ensure traceability:

```python
from __future__ import annotations

import uuid
from dagster import AssetExecutionContext

def generate_run_id(context: AssetExecutionContext, model_unique_id: str) -> str:
    """Generate deterministic run ID from Dagster context."""

    # Option 1: Use Dagster run ID + model ID
    dagster_run_id = context.run_id
    return f"{dagster_run_id}:{model_unique_id}"

    # Option 2: Generate UUID (less traceable)
    return str(uuid.uuid4())
```

### 4. Attach Facets for Rich Metadata

Include relevant facets for observability:

```python
from __future__ import annotations

from openlineage.client.run import Dataset

def build_dataset_with_facets(
    node: dict[str, Any],
    run_result: dict[str, Any] | None = None
) -> Dataset:
    """Build Dataset with comprehensive facets."""

    facets: dict[str, Any] = {
        "schema": build_schema_facet(node),
        "dataSource": build_datasource_facet(node)
    }

    # Add output statistics if available
    if run_result:
        rows_affected = run_result.get("adapter_response", {}).get("rows_affected")
        if rows_affected is not None:
            facets["outputStatistics"] = {
                "_producer": "floe-dagster",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/OutputStatisticsOutputDatasetFacet.json",
                "rowCount": rows_affected,
                "size": None
            }

    # Add data quality facets if tests ran
    if node.get("test_results"):
        facets["dataQualityAssertions"] = build_data_quality_facets(node)

    return Dataset(
        namespace=build_namespace(node),
        name=build_dataset_name(node),
        facets=facets
    )
```

### 5. Error Handling and Graceful Degradation

Never fail dbt execution due to lineage emission errors:

```python
from __future__ import annotations

import logging
from openlineage.client import OpenLineageClient

logger = logging.getLogger(__name__)

def emit_openlineage_safe(
    client: OpenLineageClient,
    event: RunEvent
) -> None:
    """Emit OpenLineage event with error handling."""

    try:
        client.emit(event)
    except Exception as e:
        # Log error but don't fail dbt execution
        logger.error(f"Failed to emit OpenLineage event: {e}", exc_info=True)
        # Optional: Emit metric for monitoring
        emit_lineage_failure_metric()
```

### 6. Structured Logging for Debugging

Log all OpenLineage emissions for debugging:

```python
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

def emit_openlineage_with_logging(
    client: OpenLineageClient,
    event: RunEvent
) -> None:
    """Emit OpenLineage event with structured logging."""

    logger.info(
        "openlineage_event_emitted",
        event_type=event.eventType.value,
        job_namespace=event.job.namespace,
        job_name=event.job.name,
        run_id=event.run.runId,
        input_count=len(event.inputs or []),
        output_count=len(event.outputs or [])
    )

    try:
        client.emit(event)
    except Exception as e:
        logger.error(
            "openlineage_emission_failed",
            error=str(e),
            event_type=event.eventType.value,
            job_name=event.job.name
        )
```

---

## Complete Implementation Examples

### Example 1: Minimal OpenLineage Integration

Simple before/after pattern with START and COMPLETE events:

```python
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import uuid

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job, Dataset

# Initialize OpenLineage client (async transport)
openlineage_client = OpenLineageClient(
    url="http://openlineage-backend:5000",
    options={"async": True}
)

@dbt_assets(manifest=Path("target/manifest.json"))
def dbt_models_with_lineage(
    context: AssetExecutionContext,
    dbt: DbtCliResource
) -> None:
    """dbt assets with minimal OpenLineage integration."""

    run_id = str(uuid.uuid4())

    # Emit START event
    openlineage_client.emit(
        RunEvent(
            eventType=RunState.START,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace="dbt", name="dbt_models"),
            producer="floe-dagster"
        )
    )

    try:
        # Execute dbt
        yield from dbt.cli(["build"], context=context).stream()

        # Emit COMPLETE event
        openlineage_client.emit(
            RunEvent(
                eventType=RunState.COMPLETE,
                eventTime=datetime.now().isoformat(),
                run=Run(runId=run_id),
                job=Job(namespace="dbt", name="dbt_models"),
                producer="floe-dagster"
            )
        )
    except Exception as e:
        # Emit FAIL event
        openlineage_client.emit(
            RunEvent(
                eventType=RunState.FAIL,
                eventTime=datetime.now().isoformat(),
                run=Run(runId=run_id),
                job=Job(namespace="dbt", name="dbt_models"),
                producer="floe-dagster"
            )
        )
        raise
```

### Example 2: Per-Model OpenLineage Emission

Emit lineage events for each individual dbt model:

```python
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any
import uuid

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets, DbtCliEventMessage
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job, Dataset

def emit_model_event(
    client: OpenLineageClient,
    event_type: RunState,
    run_id: str,
    unique_id: str,
    node_info: dict[str, Any],
    manifest: dict[str, Any] | None = None
) -> None:
    """Emit OpenLineage event for a single dbt model."""

    # Extract model name from unique_id (e.g., "model.project.customers" -> "customers")
    model_name = unique_id.split(".")[-1]

    # Build dataset info from node_info
    node_relation = node_info.get("node_relation", {})
    database = node_relation.get("database", "unknown")
    schema = node_relation.get("schema", "unknown")
    table = node_relation.get("alias", model_name)

    output_dataset = Dataset(
        namespace=f"snowflake://production",  # Customize based on adapter
        name=f"{database}.{schema}.{table}"
    )

    # Emit event
    client.emit(
        RunEvent(
            eventType=event_type,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace="dbt", name=model_name),
            outputs=[output_dataset] if event_type == RunState.COMPLETE else None,
            producer="floe-dagster"
        )
    )

@dbt_assets(manifest=Path("target/manifest.json"))
def dbt_models_per_model_lineage(
    context: AssetExecutionContext,
    dbt: DbtCliResource
) -> None:
    """dbt assets with per-model OpenLineage emission."""

    # Initialize client (async)
    client = OpenLineageClient(
        url="http://openlineage-backend:5000",
        options={"async": True}
    )

    # Track run IDs per model
    model_run_ids: dict[str, str] = {}

    # Execute dbt and intercept events
    dbt_invocation = dbt.cli(["build"], context=context)

    for raw_event in dbt_invocation.stream_raw_events():
        # Extract node info
        node_info = raw_event.raw_event.get("data", {}).get("node_info", {})

        if node_info:
            unique_id = node_info.get("unique_id", "")
            node_status = node_info.get("node_status")

            # Only process dbt models (not tests, seeds, etc.)
            if unique_id.startswith("model."):
                if node_status == "started":
                    # Generate run ID for this model
                    run_id = f"{context.run_id}:{unique_id}"
                    model_run_ids[unique_id] = run_id

                    # Emit START event
                    emit_model_event(
                        client,
                        RunState.START,
                        run_id,
                        unique_id,
                        node_info
                    )

                elif node_status in ("success", "error", "fail"):
                    # Get run ID for this model
                    run_id = model_run_ids.get(unique_id)
                    if run_id:
                        # Emit COMPLETE or FAIL event
                        event_type = RunState.COMPLETE if node_status == "success" else RunState.FAIL
                        emit_model_event(
                            client,
                            event_type,
                            run_id,
                            unique_id,
                            node_info
                        )

        # Yield Dagster events
        for dagster_event in raw_event.to_default_asset_events(context=context):
            yield dagster_event
```

### Example 3: Complete Lineage with Input/Output Datasets

Full lineage with input dependencies and output statistics:

```python
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any
import uuid

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job, Dataset

def build_dataset_from_node(
    node: dict[str, Any],
    manifest: dict[str, Any],
    run_result: dict[str, Any] | None = None
) -> Dataset:
    """Build OpenLineage Dataset from dbt node with facets."""

    # Extract relation info
    database = node.get("database", "unknown")
    schema = node.get("schema", "unknown")
    alias = node.get("alias") or node.get("name")

    # Build namespace (customize based on your adapter)
    adapter_type = manifest.get("metadata", {}).get("adapter_type", "snowflake")
    namespace = f"{adapter_type}://production"

    # Build dataset name
    dataset_name = f"{database}.{schema}.{alias}"

    # Build facets
    facets: dict[str, Any] = {
        "schema": {
            "_producer": "floe-dagster",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
            "fields": [
                {
                    "name": col_name,
                    "type": col_info.get("data_type", "unknown"),
                    "description": col_info.get("description", "")
                }
                for col_name, col_info in node.get("columns", {}).items()
            ]
        },
        "dataSource": {
            "_producer": "floe-dagster",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
            "name": database,
            "uri": f"{adapter_type}://{database}"
        }
    }

    # Add output statistics if available
    if run_result:
        rows_affected = run_result.get("adapter_response", {}).get("rows_affected")
        if rows_affected is not None:
            facets["outputStatistics"] = {
                "_producer": "floe-dagster",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/OutputStatisticsOutputDatasetFacet.json",
                "rowCount": rows_affected,
                "size": None
            }

    return Dataset(namespace=namespace, name=dataset_name, facets=facets)

@dbt_assets(manifest=Path("target/manifest.json"))
def dbt_models_complete_lineage(
    context: AssetExecutionContext,
    dbt: DbtCliResource
) -> None:
    """dbt assets with complete input/output lineage."""

    # Initialize OpenLineage client
    client = OpenLineageClient(
        url="http://openlineage-backend:5000",
        options={"async": True}
    )

    # Execute dbt
    dbt_invocation = dbt.cli(["build"], context=context)
    yield from dbt_invocation.stream()

    # Get artifacts
    manifest: dict[str, Any] = dbt_invocation.get_artifact("manifest.json")
    run_results: dict[str, Any] = dbt_invocation.get_artifact("run_results.json")

    # Build mapping of unique_id to run result
    results_by_id = {
        result["unique_id"]: result
        for result in run_results["results"]
    }

    # Emit lineage for each successful model
    for unique_id, result in results_by_id.items():
        if result["status"] != "success":
            continue

        # Get node from manifest
        node = manifest["nodes"].get(unique_id)
        if not node or node["resource_type"] != "model":
            continue

        # Build input datasets from dependencies
        depends_on = node.get("depends_on", {}).get("nodes", [])
        input_datasets = [
            build_dataset_from_node(manifest["nodes"][dep_id], manifest)
            for dep_id in depends_on
            if dep_id in manifest["nodes"]
        ]

        # Build output dataset with run statistics
        output_dataset = build_dataset_from_node(node, manifest, result)

        # Emit RunEvent with complete lineage
        run_id = f"{context.run_id}:{unique_id}"
        model_name = node["name"]

        # Emit START event
        client.emit(
            RunEvent(
                eventType=RunState.START,
                eventTime=datetime.now().isoformat(),
                run=Run(runId=run_id),
                job=Job(namespace="dbt", name=model_name),
                producer="floe-dagster"
            )
        )

        # Emit COMPLETE event with lineage
        client.emit(
            RunEvent(
                eventType=RunState.COMPLETE,
                eventTime=datetime.now().isoformat(),
                run=Run(runId=run_id),
                job=Job(namespace="dbt", name=model_name),
                inputs=input_datasets,
                outputs=[output_dataset],
                producer="floe-dagster"
            )
        )
```

### Example 4: Reusable OpenLineage Resource

Create a reusable Dagster resource for OpenLineage emission:

```python
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any
import uuid

from dagster import ConfigurableResource, AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job, Dataset
from pydantic import Field

class OpenLineageResource(ConfigurableResource):
    """Dagster resource for OpenLineage emission."""

    url: str = Field(description="OpenLineage backend URL")
    async_transport: bool = Field(default=True, description="Use async transport")
    namespace: str = Field(default="dbt", description="Default job namespace")

    def get_client(self) -> OpenLineageClient:
        """Get configured OpenLineage client."""
        return OpenLineageClient(
            url=self.url,
            options={"async": self.async_transport}
        )

    def emit_run_event(
        self,
        event_type: RunState,
        run_id: str,
        job_name: str,
        inputs: list[Dataset] | None = None,
        outputs: list[Dataset] | None = None
    ) -> None:
        """Emit OpenLineage RunEvent."""
        client = self.get_client()

        try:
            client.emit(
                RunEvent(
                    eventType=event_type,
                    eventTime=datetime.now().isoformat(),
                    run=Run(runId=run_id),
                    job=Job(namespace=self.namespace, name=job_name),
                    inputs=inputs or [],
                    outputs=outputs or [],
                    producer="floe-dagster"
                )
            )
        except Exception as e:
            # Log but don't fail execution
            print(f"Failed to emit OpenLineage event: {e}")

@dbt_assets(manifest=Path("target/manifest.json"))
def dbt_models_with_resource(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
    openlineage: OpenLineageResource
) -> None:
    """dbt assets using OpenLineage resource."""

    run_id = str(uuid.uuid4())

    # Emit START event
    openlineage.emit_run_event(
        RunState.START,
        run_id,
        "dbt_models"
    )

    try:
        # Execute dbt
        yield from dbt.cli(["build"], context=context).stream()

        # Emit COMPLETE event
        openlineage.emit_run_event(
            RunState.COMPLETE,
            run_id,
            "dbt_models"
        )
    except Exception as e:
        # Emit FAIL event
        openlineage.emit_run_event(
            RunState.FAIL,
            run_id,
            "dbt_models"
        )
        raise
```

---

## Summary

### Key Hook Points

1. **Before/After Invocation**: Custom code before `yield from dbt.cli().stream()`
2. **Raw Event Interception**: Use `stream_raw_events()` for per-model events
3. **Post-Execution Artifacts**: Access `run_results.json` and `manifest.json` with `get_artifact()`
4. **Custom Component**: Subclass `DbtProjectComponent` for advanced control

### Recommended Pattern

For most use cases, use **post-execution artifact processing**:

```python
# Execute dbt
dbt_invocation = dbt.cli(["build"], context=context)
yield from dbt_invocation.stream()

# Access artifacts and emit lineage
manifest = dbt_invocation.get_artifact("manifest.json")
run_results = dbt_invocation.get_artifact("run_results.json")
emit_complete_lineage(manifest, run_results)
```

**Why**:
- Non-blocking (lineage emission happens after dbt completes)
- Complete metadata (both static from manifest and runtime from run_results)
- Simpler error handling (dbt execution not affected by lineage failures)
- Better performance (no overhead during dbt execution)

### Best Practices Checklist

- ✅ Use async OpenLineage transport (non-blocking)
- ✅ Emit START before COMPLETE/FAIL events
- ✅ Use consistent namespace/name patterns for datasets
- ✅ Include facets (schema, dataSource, outputStatistics)
- ✅ Handle emission errors gracefully (don't fail dbt runs)
- ✅ Log all emissions for debugging
- ✅ Use deterministic run IDs from Dagster context

---

## Sources

- [Dagster & dbt (Component) | Dagster Docs](https://docs.dagster.io/integrations/libraries/dbt)
- [dbt (dagster-dbt) | Dagster Docs](https://docs.dagster.io/api/libraries/dagster-dbt)
- [dagster-dbt integration reference | Dagster Docs](https://docs.dagster.io/integrations/libraries/dbt/reference)
- [Op hooks | Dagster Docs](https://docs.dagster.io/guides/build/ops/op-hooks)
- [hooks | Dagster Docs](https://docs.dagster.io/api/dagster/hooks)
- [Events and logs | dbt Developer Hub](https://docs.getdbt.com/reference/events-logging)
- [Python | OpenLineage](https://openlineage.io/docs/client/python/)
- [OpenLineage/client/python/openlineage/client/client.py](https://github.com/OpenLineage/OpenLineage/blob/main/client/python/openlineage/client/client.py)
- [Dataset Facets | OpenLineage](https://openlineage.io/docs/spec/facets/dataset-facets/)
- [What's in a Namespace? | OpenLineage](https://openlineage.io/blog/whats-in-a-namespace/)
- [Understanding and Using Facets | OpenLineage](https://openlineage.io/docs/guides/facets/)
- [OpenLineage Spec](https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md)
