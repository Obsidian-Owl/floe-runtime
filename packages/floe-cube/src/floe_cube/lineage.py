"""OpenLineage event emitter for Cube query lineage.

This module provides the QueryLineageEvent model and QueryLineageEmitter
for emitting OpenLineage events for Cube query execution. Events enable
data governance teams to track query lineage and audit trails.

OpenLineage provides **data lineage** - "what data is being accessed?"
This is complementary to OpenTelemetry (tracing.py) which provides
**operational observability** - "how is the system performing?"

Key design principles:
- Non-blocking emission: Query execution continues even if emission fails
- Error sanitization: Sensitive data is never included in events
- Security-first: No PII, credentials, or filter values in events
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from openlineage.client import OpenLineageClient

logger = structlog.get_logger(__name__)

# Patterns for sensitive data that must be sanitized
_SENSITIVE_PATTERNS = [
    re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"secret\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"token\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"api_key\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"authorization:\s*bearer\s+\S+", re.IGNORECASE),
    re.compile(r"WHERE\s+\w+\s*=\s*'[^']+'", re.IGNORECASE),  # Filter values
]

# Maximum error message length (per schema)
MAX_ERROR_LENGTH = 500


class EventType(str, Enum):
    """OpenLineage event types."""

    START = "START"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"


class QueryLineageEvent(BaseModel):
    """OpenLineage event for Cube query lineage and audit.

    Represents a single OpenLineage event for query execution tracking.
    Events are emitted at START, COMPLETE, and FAIL states.

    Attributes:
        run_id: Unique query run identifier (UUID).
        job_name: Job name in format cube.{cube_name}.query.
        namespace: OpenLineage namespace (default: floe-cube).
        event_type: Event state (START, COMPLETE, FAIL).
        event_time: Event timestamp in UTC.
        inputs: Input dataset names (cubes queried).
        sql: Query SQL (for START events only).
        row_count: Result row count (for COMPLETE events only).
        error: Sanitized error message (for FAIL events only).

    Example:
        >>> event = QueryLineageEvent(
        ...     run_id="550e8400-e29b-41d4-a716-446655440000",
        ...     job_name="cube.orders.query",
        ...     namespace="floe-cube",
        ...     event_type=EventType.START,
        ...     event_time=datetime.now(tz=timezone.utc),
        ...     inputs=["orders"],
        ...     sql="SELECT * FROM orders",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(
        ...,
        description="Unique query run identifier (UUID)",
    )
    job_name: str = Field(
        ...,
        pattern=r"^cube\.[a-zA-Z_][a-zA-Z0-9_]*\.query$",
        description="Job name in format cube.{cube_name}.query",
    )
    namespace: str = Field(
        default="floe-cube",
        min_length=1,
        description="OpenLineage namespace",
    )
    event_type: EventType = Field(
        ...,
        description="Event state (START, COMPLETE, FAIL)",
    )
    event_time: datetime = Field(
        ...,
        description="Event timestamp in UTC",
    )
    inputs: list[str] = Field(
        default_factory=list,
        description="Input dataset names (cubes queried)",
    )
    sql: str | None = Field(
        default=None,
        description="Query SQL (for START events only)",
    )
    row_count: int | None = Field(
        default=None,
        ge=0,
        description="Result row count (for COMPLETE events only)",
    )
    error: str | None = Field(
        default=None,
        max_length=MAX_ERROR_LENGTH,
        description="Sanitized error message (for FAIL events only)",
    )

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str) -> str:
        """Validate that run_id is a valid UUID."""
        try:
            uuid.UUID(v)
        except ValueError as e:
            msg = f"run_id must be a valid UUID: {e}"
            raise ValueError(msg) from e
        return v

    @field_validator("event_time")
    @classmethod
    def validate_event_time_utc(cls, v: datetime) -> datetime:
        """Validate that event_time is UTC."""
        if v.tzinfo is None:
            msg = "event_time must be timezone-aware (UTC)"
            raise ValueError(msg)
        return v

    @field_validator("error", mode="before")
    @classmethod
    def sanitize_error(cls, v: str | None) -> str | None:
        """Sanitize and truncate error message before validation.

        This runs BEFORE Pydantic's max_length check, ensuring the
        message is sanitized and truncated to fit within limits.
        """
        if v is None:
            return None
        return sanitize_error_message(v)


def sanitize_error_message(message: str) -> str:
    """Sanitize error message to remove sensitive data.

    Removes passwords, tokens, API keys, and other sensitive data
    from error messages before including them in OpenLineage events.

    Args:
        message: Raw error message.

    Returns:
        Sanitized error message, truncated to MAX_ERROR_LENGTH.
    """
    sanitized = message
    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)

    # Truncate to max length
    if len(sanitized) > MAX_ERROR_LENGTH:
        sanitized = sanitized[: MAX_ERROR_LENGTH - 3] + "..."

    return sanitized


class QueryLineageEmitter:
    """OpenLineage event emitter for Cube queries.

    Emits OpenLineage events for query execution tracking with non-blocking
    behavior. If emission fails, the error is logged and query execution
    continues uninterrupted.

    Attributes:
        endpoint: OpenLineage API endpoint URL.
        namespace: OpenLineage namespace for events.
        enabled: Whether emission is enabled.

    Example:
        >>> emitter = QueryLineageEmitter(
        ...     endpoint="http://localhost:5000",
        ...     namespace="floe-cube",
        ... )
        >>> run_id = emitter.emit_start(
        ...     cube_name="orders",
        ...     inputs=["orders"],
        ...     sql="SELECT * FROM orders",
        ... )
        >>> emitter.emit_complete(run_id, "orders", row_count=100)
    """

    def __init__(
        self,
        endpoint: str | None = None,
        namespace: str = "floe-cube",
        enabled: bool = True,
    ) -> None:
        """Initialize the OpenLineage emitter.

        Args:
            endpoint: OpenLineage API endpoint URL (e.g., http://localhost:5000).
                If None, emission is disabled.
            namespace: OpenLineage namespace for events.
            enabled: Whether emission is enabled.
        """
        self.endpoint = endpoint
        self.namespace = namespace
        self.enabled = enabled and endpoint is not None
        self._client: OpenLineageClient | None = None

        if self.enabled:
            self._init_client()

    def _init_client(self) -> None:
        """Initialize the OpenLineage client."""
        if not self.endpoint:
            return

        try:
            from openlineage.client import OpenLineageClient
            from openlineage.client.transport.http import HttpConfig, HttpTransport

            # Use explicit HttpTransport (new API - url parameter is deprecated)
            http_config = HttpConfig(url=self.endpoint)
            transport = HttpTransport(http_config)
            self._client = OpenLineageClient(transport=transport)
            logger.info(
                "openlineage_client_initialized",
                endpoint=self.endpoint,
                namespace=self.namespace,
            )
        except Exception as e:
            logger.warning(
                "openlineage_client_init_failed",
                error=str(e),
                endpoint=self.endpoint,
            )
            self._client = None
            self.enabled = False

    def emit_start(
        self,
        cube_name: str,
        inputs: list[str] | None = None,
        sql: str | None = None,
        run_id: str | None = None,
    ) -> str:
        """Emit a START event for query execution.

        Args:
            cube_name: Name of the cube being queried.
            inputs: List of input dataset names.
            sql: Query SQL (optional, will be sanitized).
            run_id: Optional run ID (generated if not provided).

        Returns:
            The run ID for this query execution.
        """
        if run_id is None:
            run_id = str(uuid.uuid4())

        if not self.enabled:
            return run_id

        event = QueryLineageEvent(
            run_id=run_id,
            job_name=f"cube.{cube_name}.query",
            namespace=self.namespace,
            event_type=EventType.START,
            event_time=datetime.now(tz=timezone.utc),
            inputs=inputs or [cube_name],
            sql=sql,
        )

        self._emit_event(event)
        return run_id

    def emit_complete(
        self,
        run_id: str,
        cube_name: str,
        row_count: int | None = None,
        inputs: list[str] | None = None,
    ) -> None:
        """Emit a COMPLETE event for successful query execution.

        Args:
            run_id: The run ID from emit_start.
            cube_name: Name of the cube being queried.
            row_count: Number of rows returned.
            inputs: List of input dataset names.
        """
        if not self.enabled:
            return

        event = QueryLineageEvent(
            run_id=run_id,
            job_name=f"cube.{cube_name}.query",
            namespace=self.namespace,
            event_type=EventType.COMPLETE,
            event_time=datetime.now(tz=timezone.utc),
            inputs=inputs or [cube_name],
            row_count=row_count,
        )

        self._emit_event(event)

    def emit_fail(
        self,
        run_id: str,
        cube_name: str,
        error: str | Exception,
        inputs: list[str] | None = None,
    ) -> None:
        """Emit a FAIL event for failed query execution.

        Args:
            run_id: The run ID from emit_start.
            cube_name: Name of the cube being queried.
            error: Error message or exception (will be sanitized).
            inputs: List of input dataset names.
        """
        if not self.enabled:
            return

        error_message = str(error) if isinstance(error, Exception) else error
        sanitized_error = sanitize_error_message(error_message)

        event = QueryLineageEvent(
            run_id=run_id,
            job_name=f"cube.{cube_name}.query",
            namespace=self.namespace,
            event_type=EventType.FAIL,
            event_time=datetime.now(tz=timezone.utc),
            inputs=inputs or [cube_name],
            error=sanitized_error,
        )

        self._emit_event(event)

    def _emit_event(self, event: QueryLineageEvent) -> None:
        """Emit an OpenLineage event (non-blocking).

        Args:
            event: The event to emit.
        """
        try:
            self._emit_event_internal(event)
            logger.debug(
                "openlineage_event_emitted",
                run_id=event.run_id,
                event_type=event.event_type.value,
                job_name=event.job_name,
            )
        except Exception as e:
            # Non-blocking: log warning and continue
            logger.warning(
                "openlineage_emission_failed",
                run_id=event.run_id,
                event_type=event.event_type.value,
                error=str(e),
            )

    def _emit_event_internal(self, event: QueryLineageEvent) -> None:
        """Internal method to emit event to OpenLineage API.

        Args:
            event: The event to emit.
        """
        if self._client is None:
            return

        from openlineage.client.event_v2 import (
            InputDataset,
            Job,
            Run,
            RunEvent,
            RunState,
        )
        from openlineage.client.facet_v2 import sql_job

        # Map event type to RunState
        state_map = {
            EventType.START: RunState.START,
            EventType.COMPLETE: RunState.COMPLETE,
            EventType.FAIL: RunState.FAIL,
        }

        # Build facets
        facets: dict[str, Any] = {}
        if event.sql and event.event_type == EventType.START:
            facets["sql"] = sql_job.SQLJobFacet(query=event.sql)

        # Build input datasets
        inputs = [InputDataset(namespace=self.namespace, name=name) for name in event.inputs]

        # Create run event
        run_event = RunEvent(
            eventType=state_map[event.event_type],
            eventTime=event.event_time.isoformat(),
            run=Run(runId=event.run_id),
            job=Job(namespace=self.namespace, name=event.job_name, facets=facets),
            inputs=inputs,
            outputs=[],
        )

        self._client.emit(run_event)
