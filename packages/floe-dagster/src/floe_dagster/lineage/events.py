"""OpenLineage event models.

T056: [US3] Create LineageEventType enum
T057: [US3] Create LineageDataset model
T058: [US3] Create LineageEvent model
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LineageEventType(str, Enum):
    """OpenLineage run event types.

    These map directly to OpenLineage RunState values:
    https://openlineage.io/docs/spec/run-cycle

    Attributes:
        START: Run has started
        RUNNING: Run is in progress (optional intermediate state)
        COMPLETE: Run completed successfully
        FAIL: Run failed with an error
        ABORT: Run was aborted/cancelled
    """

    START = "START"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"
    ABORT = "ABORT"


class LineageDataset(BaseModel):
    """OpenLineage dataset representation.

    A dataset represents a physical data entity (table, file, topic)
    with optional facets containing metadata.

    Attributes:
        namespace: Dataset namespace (e.g., "snowflake://account")
        name: Dataset name (e.g., "database.schema.table")
        facets: Dataset facets (schema, dataSource, etc.)

    Example:
        >>> dataset = LineageDataset(
        ...     namespace="snowflake://my-account",
        ...     name="analytics.staging.stg_customers",
        ...     facets={
        ...         "schema": {
        ...             "fields": [
        ...                 {"name": "id", "type": "INTEGER"},
        ...                 {"name": "email", "type": "VARCHAR"},
        ...             ]
        ...         }
        ...     }
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    namespace: str = Field(description="Dataset namespace (e.g., snowflake://account)")
    name: str = Field(description="Dataset name (e.g., database.schema.table)")
    facets: dict[str, Any] = Field(
        default_factory=dict,
        description="Dataset facets (schema, dataSource, etc.)",
    )

    def to_openlineage_dict(self) -> dict[str, Any]:
        """Convert to OpenLineage-compatible dictionary.

        Returns:
            Dictionary matching OpenLineage dataset schema.
        """
        return {
            "namespace": self.namespace,
            "name": self.name,
            "facets": self.facets,
        }


class LineageEvent(BaseModel):
    """OpenLineage run event for emission.

    Represents a lifecycle event for a job run (START, COMPLETE, FAIL, etc.)
    with optional input/output datasets and error information.

    Attributes:
        event_type: Type of run event (START, COMPLETE, FAIL, etc.)
        run_id: Unique run identifier (UUID)
        job_namespace: Job namespace
        job_name: Job name (typically model name)
        event_time: When the event occurred
        inputs: Input datasets
        outputs: Output datasets
        error_message: Error details for FAIL events

    Example:
        >>> event = LineageEvent(
        ...     event_type=LineageEventType.START,
        ...     run_id="550e8400-e29b-41d4-a716-446655440000",
        ...     job_namespace="floe",
        ...     job_name="stg_customers",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: LineageEventType
    run_id: str = Field(description="Unique run identifier (UUID)")
    job_namespace: str = Field(description="Job namespace")
    job_name: str = Field(description="Job name (typically model name)")
    event_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the event occurred",
    )
    inputs: list[LineageDataset] = Field(
        default_factory=list,
        description="Input datasets",
    )
    outputs: list[LineageDataset] = Field(
        default_factory=list,
        description="Output datasets",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details for FAIL events",
    )

    def to_openlineage_dict(self) -> dict[str, Any]:
        """Convert to OpenLineage-compatible dictionary.

        Returns:
            Dictionary matching OpenLineage RunEvent schema:
            https://openlineage.io/docs/spec/run-cycle

        Example:
            >>> event.to_openlineage_dict()
            {
                "eventType": "START",
                "eventTime": "2024-01-15T10:30:00Z",
                "run": {"runId": "..."},
                "job": {"namespace": "floe", "name": "stg_customers"},
                "inputs": [...],
                "outputs": [...]
            }
        """
        result: dict[str, Any] = {
            "eventType": self.event_type.value,
            "eventTime": self.event_time.isoformat(),
            "run": {
                "runId": self.run_id,
            },
            "job": {
                "namespace": self.job_namespace,
                "name": self.job_name,
            },
            "inputs": [d.to_openlineage_dict() for d in self.inputs],
            "outputs": [d.to_openlineage_dict() for d in self.outputs],
            "producer": "floe-dagster",
            "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json#/definitions/RunEvent",
        }

        # Add error facet for FAIL events
        if self.event_type == LineageEventType.FAIL and self.error_message:
            result["run"]["facets"] = {
                "errorMessage": {
                    "_producer": "floe-dagster",
                    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ErrorMessageRunFacet.json",
                    "message": self.error_message,
                    "programmingLanguage": "python",
                }
            }

        return result
