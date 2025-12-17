# OpenLineage Python SDK Research (v1.24+)

Research findings for integrating OpenLineage into floe-runtime for data lineage tracking.

**Last Updated**: 2025-12-16

---

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Installation](#installation)
4. [Client Configuration](#client-configuration)
5. [Creating RunEvents](#creating-runevents)
6. [Job and Run Facets](#job-and-run-facets)
7. [Dataset Facets](#dataset-facets)
8. [Schema Facets for Column Information](#schema-facets-for-column-information)
9. [Column Classifications](#column-classifications)
10. [Error Handling and Graceful Degradation](#error-handling-and-graceful-degradation)
11. [Complete Example](#complete-example)
12. [Integration Patterns](#integration-patterns)

---

## Overview

OpenLineage is an open standard for metadata and lineage collection designed to instrument jobs as they are running. It defines a generic model of run, job, and dataset entities identified using consistent naming strategies.

**Key Features**:
- Event-based lineage tracking (START, COMPLETE, FAIL, ABORT)
- Extensible facet system for metadata
- Standard open format (no vendor lock-in)
- HTTP transport with retry and error handling
- Async event emission with ordering guarantees

---

## Core Concepts

### Event Types

OpenLineage supports three types of events:
- **RunEvent**: An event describing an observed state of a job run
- **DatasetEvent**: Changes to dataset metadata
- **JobEvent**: Changes to job metadata

**RunEvent States**:
- `START`: Job execution begins
- `COMPLETE`: Job execution succeeds
- `FAIL`: Job execution fails
- `ABORT`: Job execution aborted
- `RUNNING`: Optional intermediate state
- `OTHER`: Custom state

**Requirements**: You MUST issue 1 START event and 1 of [COMPLETE, ABORT, FAIL] event per run.

### Core Entities

**Job**: A process definition that consumes and produces datasets (defined as its inputs and outputs). It is identified by a unique name within a namespace (which is assigned to the scheduler starting the jobs).

**Run**: A specific execution instance of a Job, identified by a unique `runId` (UUID).

**Dataset**: An abstract representation of data. It has a unique name within the datasource namespace derived from its physical location (e.g., `db.host.database.schema.table`).

**Facets**: Atomic pieces of metadata attached to core entities. Facets are extensible and follow a versioned schema.

---

## Installation

```bash
# Install OpenLineage Python client
pip install openlineage-python==1.24.0

# Or latest version
pip install openlineage-python
```

**Supported Python Versions**: Python 3.8+

---

## Client Configuration

### HTTP Transport Configuration

```python
from openlineage.client import OpenLineageClient
from openlineage.client.transport.http import HttpConfig, HttpTransport

# Configuration dictionary
config = HttpConfig.from_dict({
    "type": "http",
    "url": "http://localhost:5000",
    "endpoint": "api/v1/lineage",  # Optional, default: api/v1/lineage
    "timeout": 5.0,  # Optional, default: 5 seconds
    "verify": True,  # Optional, default: True (verify TLS certs)
    "auth": {
        "type": "api_key",
        "apiKey": "your-api-key-here"
    },
    "retry": {
        "total": 5,  # Total retries, default: 5
        "read": 5,  # Read retries, default: 5
        "connect": 5,  # Connection retries, default: 5
        "backoff_factor": 0.3,  # Backoff between retries, default: 0.3
        "status_forcelist": [500, 502, 503, 504],  # HTTP codes to retry
        "allowed_methods": ["HEAD", "POST"]  # Methods that allow retry
    }
})

# Create transport and client
transport = HttpTransport(config)
client = OpenLineageClient(transport=transport)
```

### Environment Variables Configuration

```bash
# Minimal configuration via environment variables
export OPENLINEAGE_URL="http://localhost:5000"
export OPENLINEAGE_API_KEY="your-api-key"
```

```python
# Client will automatically use environment variables
from openlineage.client import OpenLineageClient

client = OpenLineageClient()  # Reads from env vars
```

### YAML Configuration File

Create `openlineage.yml`:

```yaml
transport:
  type: http
  url: https://backend:5000
  endpoint: api/v1/lineage
  timeout: 10.0
  verify: true
  auth:
    type: api_key
    apiKey: f048521b-dfe8-47cd-9c65-0cb07d57591e
  retry:
    total: 5
    backoff_factor: 0.3
```

```python
from openlineage.client import OpenLineageClient

# Client loads from openlineage.yml in current directory
client = OpenLineageClient()
```

### Console Transport (Development/Testing)

```python
from openlineage.client import OpenLineageClient
from openlineage.client.transport.console import ConsoleTransport

# Events will be printed to console (useful for debugging)
transport = ConsoleTransport()
client = OpenLineageClient(transport=transport)
```

---

## Creating RunEvents

### Basic RunEvent Structure

```python
from __future__ import annotations

import datetime
from typing import Any

from openlineage.client import OpenLineageClient
from openlineage.client.event_v2 import (
    RunEvent,
    RunState,
    Run,
    Job,
    InputDataset,
    OutputDataset,
)
from openlineage.client.uuid import generate_new_uuid


def emit_start_event(
    client: OpenLineageClient,
    job_name: str,
    job_namespace: str,
    run_id: str | None = None,
) -> str:
    """Emit START event for a job run.

    Args:
        client: OpenLineage client
        job_name: Name of the job (e.g., "customers_transform")
        job_namespace: Namespace (e.g., "floe-runtime" or "dagster")
        run_id: Optional run ID (will generate UUID if not provided)

    Returns:
        The run ID used for this event
    """
    if run_id is None:
        run_id = str(generate_new_uuid())

    event = RunEvent(
        eventType=RunState.START,
        eventTime=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        run=Run(runId=run_id, facets={}),
        job=Job(namespace=job_namespace, name=job_name, facets={}),
        producer="floe-runtime",  # Your application name
        inputs=[],
        outputs=[],
    )

    client.emit(event)
    return run_id


def emit_complete_event(
    client: OpenLineageClient,
    job_name: str,
    job_namespace: str,
    run_id: str,
    inputs: list[InputDataset] | None = None,
    outputs: list[OutputDataset] | None = None,
) -> None:
    """Emit COMPLETE event for a successful job run.

    Args:
        client: OpenLineage client
        job_name: Name of the job
        job_namespace: Namespace
        run_id: Run ID from START event
        inputs: Input datasets consumed
        outputs: Output datasets produced
    """
    event = RunEvent(
        eventType=RunState.COMPLETE,
        eventTime=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        run=Run(runId=run_id, facets={}),
        job=Job(namespace=job_namespace, name=job_name, facets={}),
        producer="floe-runtime",
        inputs=inputs or [],
        outputs=outputs or [],
    )

    client.emit(event)


def emit_fail_event(
    client: OpenLineageClient,
    job_name: str,
    job_namespace: str,
    run_id: str,
    error_message: str,
) -> None:
    """Emit FAIL event for a failed job run.

    Args:
        client: OpenLineage client
        job_name: Name of the job
        job_namespace: Namespace
        run_id: Run ID from START event
        error_message: Error message describing the failure
    """
    from openlineage.client.facet_v2 import error_message_run_facet

    event = RunEvent(
        eventType=RunState.FAIL,
        eventTime=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        run=Run(
            runId=run_id,
            facets={
                "errorMessage": error_message_run_facet.ErrorMessageRunFacet(
                    message=error_message,
                    programmingLanguage="python",
                    stackTrace=None,  # Optional: include stack trace
                )
            },
        ),
        job=Job(namespace=job_namespace, name=job_name, facets={}),
        producer="floe-runtime",
        inputs=[],
        outputs=[],
    )

    client.emit(event)
```

---

## Job and Run Facets

### Job Facets

Job facets provide metadata about the job definition:

```python
from openlineage.client.facet_v2 import (
    sql_job_facet,
    source_code_location_job_facet,
    job_type_job_facet,
)

job_facets = {
    # SQL query executed by the job
    "sql": sql_job_facet.SQLJobFacet(
        query="SELECT * FROM customers WHERE created_at > '2025-01-01'"
    ),
    # Source code location (git repo, commit SHA)
    "sourceCodeLocation": source_code_location_job_facet.SourceCodeLocationJobFacet(
        type="git",
        url="https://github.com/org/repo",
        repoUrl="https://github.com/org/repo",
        path="transforms/customers.sql",
        version="abc123def456",  # git commit SHA
        tag="v1.0.0",  # Optional git tag
        branch="main",  # Optional git branch
    ),
    # Job type (BATCH, STREAMING, etc.)
    "jobType": job_type_job_facet.JobTypeJobFacet(
        processingType="BATCH",  # or STREAMING
        integration="DAGSTER",  # Integration name
        jobType="SQL_TRANSFORM",  # Custom job type
    ),
}

job = Job(
    namespace="floe-runtime",
    name="customers_transform",
    facets=job_facets,
)
```

### Run Facets

Run facets provide metadata about the specific run instance:

```python
from openlineage.client.facet_v2 import (
    nominal_time_run_facet,
    parent_run_facet,
    processing_engine_run_facet,
)

run_facets = {
    # Nominal time (scheduled execution time)
    "nominalTime": nominal_time_run_facet.NominalTimeRunFacet(
        nominalStartTime="2025-12-16T00:00:00Z",
        nominalEndTime="2025-12-16T01:00:00Z",
    ),
    # Parent run (for orchestration hierarchy)
    "parent": parent_run_facet.ParentRunFacet(
        run=parent_run_facet.Run(runId="parent-run-uuid"),
        job=parent_run_facet.Job(
            namespace="floe-runtime",
            name="parent_job_name",
        ),
    ),
    # Processing engine metadata
    "processing_engine": processing_engine_run_facet.ProcessingEngineRunFacet(
        version="1.0.0",
        name="dbt",
        openlineageAdapterVersion="1.24.0",
    ),
}

run = Run(
    runId=str(generate_new_uuid()),
    facets=run_facets,
)
```

---

## Dataset Facets

### Input and Output Datasets

```python
from openlineage.client.event_v2 import InputDataset, OutputDataset
from openlineage.client.facet_v2 import (
    datasource_dataset_facet,
    lifecycle_state_change_dataset_facet,
)

# Input dataset (read)
input_dataset = InputDataset(
    namespace="iceberg://localhost:8181",
    name="bronze.raw.customers",
    facets={
        "dataSource": datasource_dataset_facet.DatasourceDatasetFacet(
            name="bronze.raw.customers",
            uri="iceberg://localhost:8181/bronze/raw/customers",
        ),
    },
    inputFacets={},  # Input-specific facets (e.g., inputStatistics)
)

# Output dataset (written)
output_dataset = OutputDataset(
    namespace="iceberg://localhost:8181",
    name="silver.analytics.customers",
    facets={
        "dataSource": datasource_dataset_facet.DatasourceDatasetFacet(
            name="silver.analytics.customers",
            uri="iceberg://localhost:8181/silver/analytics/customers",
        ),
        "lifecycleStateChange": lifecycle_state_change_dataset_facet.LifecycleStateChangeDatasetFacet(
            lifecycleStateChange="OVERWRITE",  # CREATE, DROP, ALTER, RENAME, TRUNCATE
        ),
    },
    outputFacets={},  # Output-specific facets (e.g., outputStatistics)
)
```

### Dataset Statistics

```python
from openlineage.client.facet_v2 import (
    output_statistics_output_dataset_facet,
    input_statistics_input_dataset_facet,
)

# Input statistics
input_facets = {
    "inputStatistics": input_statistics_input_dataset_facet.InputStatisticsInputDatasetFacet(
        rowCount=100000,
        size=52428800,  # bytes
    ),
}

input_dataset = InputDataset(
    namespace="iceberg://localhost:8181",
    name="bronze.raw.customers",
    facets={},
    inputFacets=input_facets,
)

# Output statistics
output_facets = {
    "outputStatistics": output_statistics_output_dataset_facet.OutputStatisticsOutputDatasetFacet(
        rowCount=95000,
        size=48000000,  # bytes
    ),
}

output_dataset = OutputDataset(
    namespace="iceberg://localhost:8181",
    name="silver.analytics.customers",
    facets={},
    outputFacets=output_facets,
)
```

---

## Schema Facets for Column Information

### Creating Schema Facets with Column Metadata

```python
from __future__ import annotations

from typing import Any

from openlineage.client.facet_v2 import schema_dataset_facet


def create_schema_facet(columns: list[dict[str, Any]]) -> schema_dataset_facet.SchemaDatasetFacet:
    """Create schema facet from column definitions.

    Args:
        columns: List of column dicts with 'name', 'type', 'description'

    Returns:
        SchemaDatasetFacet with column metadata
    """
    fields = [
        schema_dataset_facet.SchemaDatasetFacetFields(
            name=col["name"],
            type=col["type"],
            description=col.get("description"),
        )
        for col in columns
    ]

    return schema_dataset_facet.SchemaDatasetFacet(fields=fields)


# Example usage
columns = [
    {"name": "customer_id", "type": "BIGINT", "description": "Unique customer identifier"},
    {"name": "email", "type": "VARCHAR", "description": "Customer email address"},
    {"name": "full_name", "type": "VARCHAR", "description": "Customer full name"},
    {"name": "created_at", "type": "TIMESTAMP", "description": "Account creation timestamp"},
    {"name": "status", "type": "VARCHAR", "description": "Account status"},
]

schema_facet = create_schema_facet(columns)

# Add schema to dataset
output_dataset = OutputDataset(
    namespace="iceberg://localhost:8181",
    name="silver.analytics.customers",
    facets={
        "schema": schema_facet,
    },
    outputFacets={},
)
```

### Nested Schema (Structs and Arrays)

```python
from openlineage.client.facet_v2 import schema_dataset_facet

# Complex nested structure
fields = [
    schema_dataset_facet.SchemaDatasetFacetFields(
        name="customer_id",
        type="BIGINT",
        description="Unique identifier",
    ),
    schema_dataset_facet.SchemaDatasetFacetFields(
        name="address",
        type="STRUCT",
        description="Customer address",
        fields=[  # Nested struct fields
            schema_dataset_facet.SchemaDatasetFacetFields(
                name="street",
                type="VARCHAR",
                description="Street address",
            ),
            schema_dataset_facet.SchemaDatasetFacetFields(
                name="city",
                type="VARCHAR",
                description="City",
            ),
            schema_dataset_facet.SchemaDatasetFacetFields(
                name="postal_code",
                type="VARCHAR",
                description="Postal code",
            ),
        ],
    ),
    schema_dataset_facet.SchemaDatasetFacetFields(
        name="tags",
        type="ARRAY",
        description="Customer tags",
        fields=[  # Array element type
            schema_dataset_facet.SchemaDatasetFacetFields(
                name="_element",
                type="VARCHAR",
                description="Tag value",
            ),
        ],
    ),
]

schema_facet = schema_dataset_facet.SchemaDatasetFacet(fields=fields)
```

---

## Column Classifications

### Custom Classification Facet

OpenLineage allows custom facets for column-level metadata like classifications. Here's how to implement a custom classification facet:

```python
from __future__ import annotations

from typing import Any

from openlineage.client.facet_v2.base import DatasetFacet


class ColumnClassification:
    """Column classification metadata."""

    def __init__(
        self,
        column_name: str,
        classification: str,
        sensitivity: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.column_name = column_name
        self.classification = classification
        self.sensitivity = sensitivity
        self.tags = tags or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "columnName": self.column_name,
            "classification": self.classification,
        }
        if self.sensitivity:
            result["sensitivity"] = self.sensitivity
        if self.tags:
            result["tags"] = self.tags
        return result


class FloeColumnClassificationDatasetFacet(DatasetFacet):
    """Custom facet for Floe column classifications.

    This facet captures data governance classifications from dbt meta tags.
    """

    def __init__(
        self,
        classifications: list[ColumnClassification],
        _producer: str = "floe-runtime",
        _schemaURL: str = "https://raw.githubusercontent.com/floe/floe-runtime/main/specs/FloeColumnClassificationDatasetFacet.json",
    ) -> None:
        """Initialize facet.

        Args:
            classifications: List of column classifications
            _producer: Producer name (defaults to floe-runtime)
            _schemaURL: Schema URL for this custom facet
        """
        super().__init__()
        self._producer = _producer
        self._schemaURL = _schemaURL
        self.classifications = [c.to_dict() for c in classifications]


# Usage example
classifications = [
    ColumnClassification(
        column_name="email",
        classification="pii",
        sensitivity="high",
        tags=["email", "contact"],
    ),
    ColumnClassification(
        column_name="ssn",
        classification="pii",
        sensitivity="critical",
        tags=["ssn", "restricted"],
    ),
    ColumnClassification(
        column_name="revenue",
        classification="financial",
        sensitivity="medium",
        tags=["financial", "sensitive"],
    ),
]

classification_facet = FloeColumnClassificationDatasetFacet(
    classifications=classifications
)

# Add to dataset
output_dataset = OutputDataset(
    namespace="iceberg://localhost:8181",
    name="silver.analytics.customers",
    facets={
        "schema": schema_facet,
        "floe_columnClassification": classification_facet,  # Custom facet
    },
    outputFacets={},
)
```

### Using OpenLineage Data Quality Facets for Classification

Alternatively, use the built-in data quality facets:

```python
from openlineage.client.facet_v2 import data_quality_metrics_input_dataset_facet

# Column-level data quality metrics (can include classification metadata)
column_metrics = {
    "email": data_quality_metrics_input_dataset_facet.ColumnMetrics(
        nullCount=150,
        distinctCount=95000,
        min=None,
        max=None,
        quantiles=None,
    ),
    "ssn": data_quality_metrics_input_dataset_facet.ColumnMetrics(
        nullCount=0,
        distinctCount=95000,
        min=None,
        max=None,
        quantiles=None,
    ),
}

dq_facet = data_quality_metrics_input_dataset_facet.DataQualityMetricsInputDatasetFacet(
    rowCount=95000,
    bytes=48000000,
    fileCount=1,
    columnMetrics=column_metrics,
)
```

---

## Error Handling and Graceful Degradation

### HTTP Retry Configuration

The OpenLineage client includes built-in retry logic with exponential backoff:

```python
from openlineage.client import OpenLineageClient
from openlineage.client.transport.http import HttpConfig, HttpTransport

config = HttpConfig.from_dict({
    "type": "http",
    "url": "http://localhost:5000",
    "retry": {
        "total": 5,  # Total retries
        "read": 5,  # Read retries
        "connect": 5,  # Connection retries
        "backoff_factor": 0.3,  # Exponential backoff multiplier
        "status_forcelist": [500, 502, 503, 504],  # Retry these HTTP codes
        "allowed_methods": ["HEAD", "POST"],  # Methods that allow retry
    }
})

transport = HttpTransport(config)
client = OpenLineageClient(transport=transport)
```

**Backoff calculation**: `{backoff_factor} * (2 ** ({retry_count} - 1))` seconds
- Retry 1: 0.3 * (2 ** 0) = 0.3 seconds
- Retry 2: 0.3 * (2 ** 1) = 0.6 seconds
- Retry 3: 0.3 * (2 ** 2) = 1.2 seconds
- Retry 4: 0.3 * (2 ** 3) = 2.4 seconds
- Retry 5: 0.3 * (2 ** 4) = 4.8 seconds

### Graceful Degradation Pattern

```python
from __future__ import annotations

import logging
from typing import Any

from openlineage.client import OpenLineageClient
from openlineage.client.transport.http import HttpConfig, HttpTransport
from openlineage.client.transport.console import ConsoleTransport

logger = logging.getLogger(__name__)


def create_lineage_client(
    url: str | None = None,
    api_key: str | None = None,
    fallback_to_console: bool = True,
) -> OpenLineageClient | None:
    """Create OpenLineage client with graceful degradation.

    Args:
        url: OpenLineage backend URL (optional, reads from env if not provided)
        api_key: API key for authentication (optional)
        fallback_to_console: If True, fall back to console logging on error

    Returns:
        OpenLineageClient instance or None if unavailable
    """
    try:
        if url:
            # Explicit HTTP configuration
            config_dict: dict[str, Any] = {
                "type": "http",
                "url": url,
                "timeout": 5.0,
                "retry": {
                    "total": 3,  # Fewer retries for faster failure
                    "backoff_factor": 0.3,
                },
            }
            if api_key:
                config_dict["auth"] = {
                    "type": "api_key",
                    "apiKey": api_key,
                }

            config = HttpConfig.from_dict(config_dict)
            transport = HttpTransport(config)
            logger.info(f"OpenLineage client configured for {url}")
        else:
            # Try environment variables (OPENLINEAGE_URL, OPENLINEAGE_API_KEY)
            transport = None  # Client will auto-detect from env
            logger.info("OpenLineage client using environment configuration")

        return OpenLineageClient(transport=transport)

    except Exception as e:
        logger.warning(f"Failed to create OpenLineage HTTP client: {e}")

        if fallback_to_console:
            logger.info("Falling back to console logging for OpenLineage events")
            return OpenLineageClient(transport=ConsoleTransport())

        logger.info("OpenLineage disabled - lineage will not be collected")
        return None


def emit_event_safe(client: OpenLineageClient | None, event: Any) -> bool:
    """Emit event with error handling.

    Args:
        client: OpenLineage client (can be None)
        event: RunEvent to emit

    Returns:
        True if event was emitted successfully, False otherwise
    """
    if client is None:
        return False

    try:
        client.emit(event)
        return True
    except Exception as e:
        logger.warning(f"Failed to emit OpenLineage event: {e}")
        return False


# Usage
client = create_lineage_client(
    url="http://localhost:5000",
    api_key=None,
    fallback_to_console=True,
)

# Emit events safely
emit_event_safe(client, start_event)
```

### Async Event Emission

The OpenLineage client supports async event emission with guaranteed ordering:

```python
from openlineage.client import OpenLineageClient

client = OpenLineageClient()  # Uses async HTTP transport by default

# Events are queued and sent asynchronously
client.emit(start_event)  # Returns immediately

# Get stats
if hasattr(client.transport, "get_stats"):
    stats = client.transport.get_stats()
    logger.info(
        f"OpenLineage stats - Pending: {stats['pending']}, "
        f"Success: {stats['success']}, Failed: {stats['failed']}"
    )

# Graceful shutdown (wait for pending events)
client.close()
```

### Disable Lineage Collection

```python
import os

# Disable OpenLineage by not setting OPENLINEAGE_URL
if os.getenv("OPENLINEAGE_DISABLED", "false").lower() == "true":
    logger.info("OpenLineage disabled via OPENLINEAGE_DISABLED=true")
    client = None
else:
    client = create_lineage_client()
```

---

## Complete Example

### End-to-End Lineage Collection

```python
from __future__ import annotations

import datetime
import logging
from typing import Any

from openlineage.client import OpenLineageClient
from openlineage.client.event_v2 import (
    RunEvent,
    RunState,
    Run,
    Job,
    InputDataset,
    OutputDataset,
)
from openlineage.client.facet_v2 import (
    schema_dataset_facet,
    sql_job_facet,
    source_code_location_job_facet,
    nominal_time_run_facet,
    output_statistics_output_dataset_facet,
    input_statistics_input_dataset_facet,
    datasource_dataset_facet,
    error_message_run_facet,
)
from openlineage.client.uuid import generate_new_uuid

logger = logging.getLogger(__name__)


class LineageEmitter:
    """Emit OpenLineage events for data pipeline execution."""

    def __init__(self, client: OpenLineageClient, namespace: str = "floe-runtime") -> None:
        """Initialize emitter.

        Args:
            client: OpenLineage client
            namespace: Namespace for jobs and datasets
        """
        self.client = client
        self.namespace = namespace

    def emit_transform_start(
        self,
        transform_name: str,
        sql_query: str,
        source_location: str | None = None,
        git_sha: str | None = None,
    ) -> str:
        """Emit START event for a data transformation.

        Args:
            transform_name: Name of the transformation
            sql_query: SQL query being executed
            source_location: Path to source file
            git_sha: Git commit SHA

        Returns:
            Run ID for this execution
        """
        run_id = str(generate_new_uuid())

        job_facets: dict[str, Any] = {
            "sql": sql_job_facet.SQLJobFacet(query=sql_query),
        }

        if source_location and git_sha:
            job_facets["sourceCodeLocation"] = (
                source_code_location_job_facet.SourceCodeLocationJobFacet(
                    type="git",
                    url=f"https://github.com/org/repo/blob/{git_sha}/{source_location}",
                    path=source_location,
                    version=git_sha,
                )
            )

        event = RunEvent(
            eventType=RunState.START,
            eventTime=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            run=Run(
                runId=run_id,
                facets={
                    "nominalTime": nominal_time_run_facet.NominalTimeRunFacet(
                        nominalStartTime=datetime.datetime.now(datetime.timezone.utc).isoformat()
                    ),
                },
            ),
            job=Job(
                namespace=self.namespace,
                name=transform_name,
                facets=job_facets,
            ),
            producer="floe-runtime",
            inputs=[],
            outputs=[],
        )

        self.client.emit(event)
        logger.info(f"Emitted START event for {transform_name} (run_id={run_id})")
        return run_id

    def emit_transform_complete(
        self,
        transform_name: str,
        run_id: str,
        input_tables: list[dict[str, Any]],
        output_table: dict[str, Any],
    ) -> None:
        """Emit COMPLETE event for a successful transformation.

        Args:
            transform_name: Name of the transformation
            run_id: Run ID from START event
            input_tables: List of input table metadata
            output_table: Output table metadata
        """
        # Create input datasets
        inputs = []
        for input_table in input_tables:
            input_schema = schema_dataset_facet.SchemaDatasetFacet(
                fields=[
                    schema_dataset_facet.SchemaDatasetFacetFields(
                        name=col["name"],
                        type=col["type"],
                        description=col.get("description"),
                    )
                    for col in input_table.get("columns", [])
                ]
            )

            input_dataset = InputDataset(
                namespace=self.namespace,
                name=input_table["name"],
                facets={
                    "schema": input_schema,
                    "dataSource": datasource_dataset_facet.DatasourceDatasetFacet(
                        name=input_table["name"],
                        uri=input_table.get("uri", ""),
                    ),
                },
                inputFacets={
                    "inputStatistics": (
                        input_statistics_input_dataset_facet.InputStatisticsInputDatasetFacet(
                            rowCount=input_table.get("row_count", 0),
                            size=input_table.get("size_bytes", 0),
                        )
                    ),
                },
            )
            inputs.append(input_dataset)

        # Create output dataset
        output_schema = schema_dataset_facet.SchemaDatasetFacet(
            fields=[
                schema_dataset_facet.SchemaDatasetFacetFields(
                    name=col["name"],
                    type=col["type"],
                    description=col.get("description"),
                )
                for col in output_table.get("columns", [])
            ]
        )

        output_dataset = OutputDataset(
            namespace=self.namespace,
            name=output_table["name"],
            facets={
                "schema": output_schema,
                "dataSource": datasource_dataset_facet.DatasourceDatasetFacet(
                    name=output_table["name"],
                    uri=output_table.get("uri", ""),
                ),
            },
            outputFacets={
                "outputStatistics": (
                    output_statistics_output_dataset_facet.OutputStatisticsOutputDatasetFacet(
                        rowCount=output_table.get("row_count", 0),
                        size=output_table.get("size_bytes", 0),
                    )
                ),
            },
        )

        event = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            run=Run(runId=run_id, facets={}),
            job=Job(namespace=self.namespace, name=transform_name, facets={}),
            producer="floe-runtime",
            inputs=inputs,
            outputs=[output_dataset],
        )

        self.client.emit(event)
        logger.info(f"Emitted COMPLETE event for {transform_name} (run_id={run_id})")

    def emit_transform_fail(
        self,
        transform_name: str,
        run_id: str,
        error_message: str,
        stack_trace: str | None = None,
    ) -> None:
        """Emit FAIL event for a failed transformation.

        Args:
            transform_name: Name of the transformation
            run_id: Run ID from START event
            error_message: Error message
            stack_trace: Optional stack trace
        """
        event = RunEvent(
            eventType=RunState.FAIL,
            eventTime=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            run=Run(
                runId=run_id,
                facets={
                    "errorMessage": error_message_run_facet.ErrorMessageRunFacet(
                        message=error_message,
                        programmingLanguage="python",
                        stackTrace=stack_trace,
                    ),
                },
            ),
            job=Job(namespace=self.namespace, name=transform_name, facets={}),
            producer="floe-runtime",
            inputs=[],
            outputs=[],
        )

        self.client.emit(event)
        logger.error(f"Emitted FAIL event for {transform_name} (run_id={run_id}): {error_message}")


# Usage example
def run_transformation() -> None:
    """Example: Run a transformation with lineage collection."""
    from openlineage.client.transport.http import HttpConfig, HttpTransport

    # Create client
    config = HttpConfig.from_dict({
        "type": "http",
        "url": "http://localhost:5000",
        "timeout": 5.0,
        "retry": {"total": 3},
    })
    transport = HttpTransport(config)
    client = OpenLineageClient(transport=transport)

    emitter = LineageEmitter(client, namespace="floe-runtime")

    transform_name = "silver.analytics.customers"
    sql_query = """
        SELECT
            customer_id,
            email,
            full_name,
            created_at,
            status
        FROM bronze.raw.customers
        WHERE created_at >= '2025-01-01'
    """

    # Emit START event
    run_id = emitter.emit_transform_start(
        transform_name=transform_name,
        sql_query=sql_query,
        source_location="transforms/customers.sql",
        git_sha="abc123def456",
    )

    try:
        # Execute transformation (pseudo-code)
        # result = execute_dbt_model(transform_name)

        # Emit COMPLETE event
        emitter.emit_transform_complete(
            transform_name=transform_name,
            run_id=run_id,
            input_tables=[
                {
                    "name": "bronze.raw.customers",
                    "uri": "iceberg://localhost:8181/bronze/raw/customers",
                    "row_count": 100000,
                    "size_bytes": 52428800,
                    "columns": [
                        {"name": "customer_id", "type": "BIGINT"},
                        {"name": "email", "type": "VARCHAR"},
                        {"name": "full_name", "type": "VARCHAR"},
                        {"name": "created_at", "type": "TIMESTAMP"},
                        {"name": "status", "type": "VARCHAR"},
                    ],
                }
            ],
            output_table={
                "name": "silver.analytics.customers",
                "uri": "iceberg://localhost:8181/silver/analytics/customers",
                "row_count": 95000,
                "size_bytes": 48000000,
                "columns": [
                    {"name": "customer_id", "type": "BIGINT"},
                    {"name": "email", "type": "VARCHAR"},
                    {"name": "full_name", "type": "VARCHAR"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                    {"name": "status", "type": "VARCHAR"},
                ],
            },
        )

    except Exception as e:
        # Emit FAIL event
        import traceback
        emitter.emit_transform_fail(
            transform_name=transform_name,
            run_id=run_id,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        raise

    finally:
        # Graceful shutdown
        client.close()
```

---

## Integration Patterns

### Integration with Dagster

```python
from dagster import asset, AssetExecutionContext
from openlineage.client import OpenLineageClient

@asset
def customers_transform(context: AssetExecutionContext) -> None:
    """Transform customers data with lineage tracking."""
    client = OpenLineageClient()
    emitter = LineageEmitter(client, namespace="dagster")

    run_id = emitter.emit_transform_start(
        transform_name="customers_transform",
        sql_query="SELECT * FROM raw_customers",
    )

    try:
        # Execute dbt or SQL transformation
        # ...

        emitter.emit_transform_complete(
            transform_name="customers_transform",
            run_id=run_id,
            input_tables=[...],
            output_table={...},
        )
    except Exception as e:
        emitter.emit_transform_fail(
            transform_name="customers_transform",
            run_id=run_id,
            error_message=str(e),
        )
        raise
    finally:
        client.close()
```

### Integration with dbt

```python
from openlineage.client import OpenLineageClient
import json
from pathlib import Path

def emit_dbt_lineage(manifest_path: Path, run_results_path: Path) -> None:
    """Emit lineage from dbt artifacts.

    Args:
        manifest_path: Path to dbt manifest.json
        run_results_path: Path to dbt run_results.json
    """
    client = OpenLineageClient()
    emitter = LineageEmitter(client, namespace="dbt")

    manifest = json.loads(manifest_path.read_text())
    run_results = json.loads(run_results_path.read_text())

    for result in run_results["results"]:
        node_id = result["unique_id"]
        node = manifest["nodes"][node_id]

        # Extract metadata from dbt manifest
        transform_name = node["name"]
        sql_query = node.get("compiled_sql", node.get("raw_sql", ""))

        run_id = emitter.emit_transform_start(
            transform_name=transform_name,
            sql_query=sql_query,
        )

        if result["status"] == "success":
            # Extract input/output tables from manifest
            input_tables = [
                {
                    "name": ref,
                    "columns": manifest["nodes"][ref].get("columns", []),
                }
                for ref in node.get("depends_on", {}).get("nodes", [])
            ]

            output_table = {
                "name": node["name"],
                "columns": [
                    {"name": col, "type": meta.get("data_type", "UNKNOWN")}
                    for col, meta in node.get("columns", {}).items()
                ],
            }

            emitter.emit_transform_complete(
                transform_name=transform_name,
                run_id=run_id,
                input_tables=input_tables,
                output_table=output_table,
            )
        else:
            emitter.emit_transform_fail(
                transform_name=transform_name,
                run_id=run_id,
                error_message=result.get("message", "Unknown error"),
            )

    client.close()
```

### Standalone-First Pattern for floe-runtime

```python
from __future__ import annotations

import os
import logging
from typing import Optional

from openlineage.client import OpenLineageClient
from openlineage.client.transport.console import ConsoleTransport

logger = logging.getLogger(__name__)


def get_lineage_client() -> Optional[OpenLineageClient]:
    """Get OpenLineage client with standalone-first approach.

    Returns None if OpenLineage is disabled or unavailable.
    Falls back to console logging in development.

    Returns:
        OpenLineageClient or None
    """
    # Check if explicitly disabled
    if os.getenv("FLOE_LINEAGE_DISABLED", "false").lower() == "true":
        logger.info("OpenLineage disabled via FLOE_LINEAGE_DISABLED=true")
        return None

    # Try to create client from environment
    if os.getenv("OPENLINEAGE_URL"):
        try:
            client = OpenLineageClient()
            logger.info("OpenLineage client created from environment")
            return client
        except Exception as e:
            logger.warning(f"Failed to create OpenLineage client: {e}")

    # Fallback to console logging in development
    if os.getenv("FLOE_ENV", "development") == "development":
        logger.info("Using console transport for OpenLineage (development mode)")
        return OpenLineageClient(transport=ConsoleTransport())

    logger.info("OpenLineage not configured - lineage will not be collected")
    return None


# In floe-runtime code
client = get_lineage_client()

if client is not None:
    emitter = LineageEmitter(client)
    run_id = emitter.emit_transform_start(...)
else:
    logger.debug("Skipping lineage emission - client not available")
```

---

## Sources

- [Object Model | OpenLineage](https://openlineage.io/docs/spec/object-model/)
- [OpenLineage Specification](https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.md)
- [Python Client Documentation](https://openlineage.io/docs/client/python/)
- [Python Client Source Code](https://github.com/OpenLineage/OpenLineage/blob/main/client/python/openlineage/client/client.py)
- [HTTP Transport Tests](https://github.com/OpenLineage/OpenLineage/blob/main/client/python/tests/test_http.py)
- [Understanding and Using Facets](https://openlineage.io/docs/guides/facets/)
- [Schema Dataset Facet](https://openlineage.io/docs/spec/facets/dataset-facets/schema/)
- [Custom Facets Documentation](https://openlineage.io/docs/spec/facets/custom-facets/)
- [Tags Facet Proposal](https://github.com/OpenLineage/OpenLineage/blob/main/proposals/3169/tags_facet.md)
- [Example Lineage Events](https://openlineage.io/docs/development/examples/)
- [OpenLineage GitHub Repository](https://github.com/OpenLineage/OpenLineage)
- [Python Client Blog Post](https://openlineage.io/blog/python-client/)
- [dbt Integration](https://pypi.org/project/openlineage-dbt/)
- [OpenLineage Releases](https://github.com/OpenLineage/OpenLineage/releases)

---

## Key Takeaways for floe-runtime

1. **Standalone-First**: OpenLineage client gracefully handles unavailable backends with console fallback
2. **Retry Logic**: Built-in HTTP retry with exponential backoff (configurable)
3. **Async Emission**: Events are queued and sent asynchronously with ordering guarantees
4. **Extensible**: Custom facets allow column classifications from dbt meta tags
5. **Standard Format**: Open standard (no vendor lock-in), integrates with Marquez, Atlan, etc.
6. **Type Safety**: Use Pydantic wrappers around OpenLineage classes for validation
7. **Error Handling**: Graceful degradation when lineage backend is unavailable
8. **Column Metadata**: SchemaDatasetFacet supports nested schemas and descriptions
9. **dbt Integration**: Can parse manifest.json and run_results.json for automatic lineage
10. **Dagster Integration**: Integrate into Dagster assets for orchestration-aware lineage

---

**Next Steps**:
1. Implement `LineageEmitter` class in `floe-dagster` package
2. Extract column classifications from dbt `meta` tags
3. Emit START/COMPLETE/FAIL events from Dagster assets
4. Add configuration for OpenLineage backend URL
5. Implement graceful degradation for standalone execution
