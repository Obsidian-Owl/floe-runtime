"""OpenLineage emitter client.

T062: [US3] Implement OpenLineageEmitter.emit_start
T063: [US3] Implement OpenLineageEmitter.emit_complete with schema facets
T064: [US3] Implement OpenLineageEmitter.emit_fail with error details
T065: [US3] Implement graceful degradation (NoOp) when endpoint unavailable
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from floe_dagster.lineage.config import OpenLineageConfig
from floe_dagster.lineage.events import LineageDataset, LineageEvent, LineageEventType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class OpenLineageEmitter:
    """OpenLineage event emitter for data lineage tracking.

    Emits OpenLineage RunEvents (START, COMPLETE, FAIL) to a configured
    backend. Implements graceful degradation when no endpoint is configured
    or when the endpoint is unavailable.

    Attributes:
        config: OpenLineage configuration
        enabled: Whether lineage emission is enabled

    Example:
        >>> config = OpenLineageConfig(
        ...     endpoint="http://localhost:5000/api/v1/lineage",
        ...     namespace="analytics",
        ... )
        >>> emitter = OpenLineageEmitter(config)
        >>> run_id = emitter.emit_start(job_name="stg_customers")
        >>> # ... execute job ...
        >>> emitter.emit_complete(run_id=run_id, job_name="stg_customers")

    Graceful Degradation:
        When endpoint is None or unavailable, all emit methods are no-ops.
        This allows pipelines to run without requiring a lineage backend.

        >>> disabled_config = OpenLineageConfig()  # endpoint=None
        >>> emitter = OpenLineageEmitter(disabled_config)
        >>> emitter.enabled
        False
        >>> emitter.emit_start(...)  # No-op, returns dummy run_id
    """

    def __init__(self, config: OpenLineageConfig) -> None:
        """Initialize OpenLineageEmitter.

        Args:
            config: OpenLineage configuration.
        """
        self.config = config

    @property
    def enabled(self) -> bool:
        """Check if lineage emission is enabled.

        Returns:
            True if endpoint is configured, False otherwise.
        """
        return self.config.enabled

    def emit_start(
        self,
        job_name: str,
        inputs: list[LineageDataset] | None = None,
        outputs: list[LineageDataset] | None = None,
    ) -> str:
        """Emit START event for a job run.

        Creates and sends a START event to mark the beginning of a job.
        Returns a run_id that should be used for subsequent events.

        Args:
            job_name: Name of the job (typically dbt model name).
            inputs: Optional input datasets.
            outputs: Optional output datasets.

        Returns:
            Run ID (UUID string) for tracking the run.

        Note:
            When disabled, returns a dummy run_id but doesn't send anything.
        """
        run_id = self._generate_run_id()

        if not self.enabled:
            logger.debug(
                "OpenLineage disabled - skipping START event for %s",
                job_name,
            )
            return run_id

        event = LineageEvent(
            event_type=LineageEventType.START,
            run_id=run_id,
            job_namespace=self.config.namespace,
            job_name=job_name,
            inputs=inputs or [],
            outputs=outputs or [],
        )

        self._send_event(event)

        return run_id

    def emit_complete(
        self,
        run_id: str,
        job_name: str,
        inputs: list[LineageDataset] | None = None,
        outputs: list[LineageDataset] | None = None,
    ) -> None:
        """Emit COMPLETE event for a job run.

        Creates and sends a COMPLETE event to mark successful job completion.
        Output datasets can include schema facets with column information.

        Args:
            run_id: Run ID from emit_start.
            job_name: Name of the job.
            inputs: Input datasets.
            outputs: Output datasets (may include schema facets).
        """
        if not self.enabled:
            logger.debug(
                "OpenLineage disabled - skipping COMPLETE event for %s",
                job_name,
            )
            return

        event = LineageEvent(
            event_type=LineageEventType.COMPLETE,
            run_id=run_id,
            job_namespace=self.config.namespace,
            job_name=job_name,
            inputs=inputs or [],
            outputs=outputs or [],
        )

        self._send_event(event)

    def emit_fail(
        self,
        run_id: str,
        job_name: str,
        error_message: str,
        inputs: list[LineageDataset] | None = None,
        outputs: list[LineageDataset] | None = None,
    ) -> None:
        """Emit FAIL event for a job run.

        Creates and sends a FAIL event with error details when a job fails.

        Args:
            run_id: Run ID from emit_start.
            job_name: Name of the job.
            error_message: Error message describing the failure.
            inputs: Input datasets (if known at failure time).
            outputs: Output datasets (if known at failure time).
        """
        if not self.enabled:
            logger.debug(
                "OpenLineage disabled - skipping FAIL event for %s",
                job_name,
            )
            return

        event = LineageEvent(
            event_type=LineageEventType.FAIL,
            run_id=run_id,
            job_namespace=self.config.namespace,
            job_name=job_name,
            inputs=inputs or [],
            outputs=outputs or [],
            error_message=error_message,
        )

        self._send_event(event)

    @contextmanager
    def run_context(
        self,
        job_name: str,
        inputs: list[LineageDataset] | None = None,
        outputs: list[LineageDataset] | None = None,
    ) -> Iterator[str]:
        """Context manager for tracking a job run.

        Emits START on entry, COMPLETE on clean exit, and FAIL on exception.
        Provides automatic lifecycle management for lineage events.

        Args:
            job_name: Name of the job.
            inputs: Input datasets.
            outputs: Output datasets.

        Yields:
            Run ID for the tracked run.

        Example:
            >>> with emitter.run_context("my_model", inputs, outputs) as run_id:
            ...     # Execute job
            ...     pass
            # COMPLETE emitted automatically

            >>> with emitter.run_context("my_model") as run_id:
            ...     raise ValueError("Something went wrong")
            # FAIL emitted automatically, exception re-raised
        """
        run_id = self.emit_start(
            job_name=job_name,
            inputs=inputs,
            outputs=outputs,
        )

        try:
            yield run_id
            # Clean exit - emit COMPLETE
            self.emit_complete(
                run_id=run_id,
                job_name=job_name,
                inputs=inputs,
                outputs=outputs,
            )
        except Exception as e:
            # Exception - emit FAIL and re-raise
            self.emit_fail(
                run_id=run_id,
                job_name=job_name,
                error_message=str(e),
                inputs=inputs,
                outputs=outputs,
            )
            raise

    def _send_event(self, event: LineageEvent) -> None:
        """Send event to OpenLineage backend.

        Implements graceful degradation - logs errors but doesn't raise
        to avoid breaking pipeline execution due to lineage issues.

        Args:
            event: LineageEvent to send.
        """
        try:
            import httpx

            payload = event.to_openlineage_dict()

            response = httpx.post(
                str(self.config.endpoint),
                json=payload,
                timeout=self.config.timeout,
            )

            if response.status_code >= 400:
                logger.warning(
                    "OpenLineage endpoint returned %s: %s",
                    response.status_code,
                    response.text[:200],
                )
            else:
                logger.debug(
                    "Sent %s event for %s (run_id=%s)",
                    event.event_type.value,
                    event.job_name,
                    event.run_id,
                )

        except ImportError:
            logger.warning(
                "httpx not installed - cannot send OpenLineage events. "
                "Install with: pip install httpx"
            )
        except Exception as e:
            # Graceful degradation - log but don't raise
            logger.warning(
                "Failed to send OpenLineage event: %s",
                str(e),
            )

    def _generate_run_id(self) -> str:
        """Generate a new run ID (UUID).

        Returns:
            UUID string for run identification.
        """
        return str(uuid.uuid4())
