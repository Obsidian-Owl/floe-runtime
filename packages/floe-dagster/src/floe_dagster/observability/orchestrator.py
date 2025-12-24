"""Unified observability orchestrator combining tracing and lineage.

T090: [US6] Implement ObservabilityOrchestrator context manager
T091: [US6] Implement AssetRunContext dataclass

This module provides a unified context manager that combines OpenTelemetry tracing
with OpenLineage lineage emission. It implements the "batteries-included" philosophy
where data engineers get observability for free without boilerplate.

Key Design Decisions:
    - Graceful degradation: If tracing/lineage unavailable, execution continues
    - Exception recording: Exceptions are recorded to span before re-raising
    - Unified lifecycle: Single context manager handles both observability concerns
    - Runtime resolution: Secrets resolved at runtime, not compile time

Example:
    >>> from floe_dagster.observability import ObservabilityOrchestrator
    >>> orchestrator = ObservabilityOrchestrator.from_compiled_artifacts(artifacts)
    >>> with orchestrator.asset_run("bronze_customers", outputs=["demo.bronze"]) as ctx:
    ...     # Business logic here - observability handled automatically
    ...     ctx.set_attribute("rows_processed", 1000)
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any, Self

from floe_dagster.lineage.client import OpenLineageEmitter
from floe_dagster.lineage.config import OpenLineageConfig
from floe_dagster.lineage.events import LineageDataset
from floe_dagster.observability.config import TracingConfig
from floe_dagster.observability.tracing import TracingManager

if TYPE_CHECKING:
    from opentelemetry.trace import Span

logger = logging.getLogger(__name__)


@dataclass
class AssetRunContext:
    """Context returned by ObservabilityOrchestrator.asset_run().

    Provides access to the active span and lineage run_id, with helper methods
    for adding attributes. Both span and run_id may be None if the respective
    observability backend is unavailable - this is intentional graceful degradation.

    Attributes:
        span: Active OTel span, or None if tracing unavailable
        run_id: OpenLineage run ID, or None if lineage unavailable
        asset_name: Name of the asset being executed
        attributes: Mutable dict of attributes added during execution

    Example:
        >>> with orchestrator.asset_run("my_asset") as ctx:
        ...     ctx.set_attribute("rows", 1000)
        ...     ctx.set_attribute("status", "success")
        ...     if ctx.span:  # Only if tracing enabled
        ...         ctx.span.add_event("checkpoint")
    """

    span: Span | None = None
    run_id: str | None = None
    asset_name: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on both span and internal tracking.

        Sets the attribute on the OTel span (if available) and stores it
        for later reference. This ensures attributes are captured regardless
        of whether tracing is enabled.

        Args:
            key: Attribute key (e.g., "rows_processed", "duration_ms")
            value: Attribute value (must be OTel-compatible: str, int, float, bool)
        """
        self.attributes[key] = value
        if self.span is not None:
            try:
                self.span.set_attribute(key, value)
            except Exception as e:
                # Don't fail if span attribute setting fails
                logger.debug("Failed to set span attribute %s: %s", key, e)


class ObservabilityOrchestrator:
    """Unified tracing + lineage lifecycle management.

    Combines TracingManager (OTel) and OpenLineageEmitter into a single
    context manager that handles observability concerns automatically.
    Data engineers use this via the @floe_asset decorator without writing
    any observability boilerplate.

    Key Design Principles:
        - Observability failures NEVER break pipeline execution
        - Both tracing and lineage are optional (graceful degradation)
        - Exceptions from business logic are recorded then re-raised
        - Configuration comes from CompiledArtifacts (two-tier architecture)

    Attributes:
        tracing_manager: TracingManager instance, or None if disabled
        lineage_emitter: OpenLineageEmitter instance, or None if disabled

    Example:
        >>> # Create from CompiledArtifacts (typical usage)
        >>> orchestrator = ObservabilityOrchestrator.from_compiled_artifacts(artifacts)
        >>>
        >>> # Use in asset execution
        >>> with orchestrator.asset_run(
        ...     "bronze_customers",
        ...     outputs=["demo.bronze_customers"],
        ...     attributes={"source": "synthetic"}
        ... ) as ctx:
        ...     # Business logic - observability automatic
        ...     rows = generate_customers(1000)
        ...     ctx.set_attribute("rows_generated", rows)

    Graceful Degradation:
        >>> # When endpoints are None or unreachable
        >>> orchestrator = ObservabilityOrchestrator(None, None)
        >>> with orchestrator.asset_run("my_asset") as ctx:
        ...     # ctx.span is None, ctx.run_id is None
        ...     # But execution proceeds normally
        ...     process_data()  # Works fine
    """

    def __init__(
        self,
        tracing_manager: TracingManager | None,
        lineage_emitter: OpenLineageEmitter | None,
    ) -> None:
        """Initialize ObservabilityOrchestrator.

        Args:
            tracing_manager: TracingManager for OTel spans, or None to disable
            lineage_emitter: OpenLineageEmitter for lineage, or None to disable
        """
        self.tracing_manager = tracing_manager
        self.lineage_emitter = lineage_emitter

    @classmethod
    def from_compiled_artifacts(
        cls,
        artifacts: dict[str, Any],
        *,
        namespace: str = "floe",
    ) -> Self:
        """Create ObservabilityOrchestrator from CompiledArtifacts.

        Factory method that extracts observability configuration from
        CompiledArtifacts and creates appropriately configured managers.
        This is the primary way to create an orchestrator in production.

        Args:
            artifacts: CompiledArtifacts dict (or model_dump() result)
            namespace: Default namespace for OpenLineage events

        Returns:
            Configured ObservabilityOrchestrator

        Example:
            >>> artifacts = CompiledArtifacts.load(".floe/compiled_artifacts.json")
            >>> orchestrator = ObservabilityOrchestrator.from_compiled_artifacts(
            ...     artifacts.model_dump()
            ... )
        """
        tracing_manager: TracingManager | None = None
        lineage_emitter: OpenLineageEmitter | None = None

        try:
            tracing_config = TracingConfig.from_artifacts(artifacts)
            if tracing_config.enabled:
                tracing_manager = TracingManager(tracing_config)
                tracing_manager.configure()
                logger.info(
                    "Tracing enabled: endpoint=%s",
                    tracing_config.endpoint,
                )
            else:
                logger.debug("Tracing disabled - no endpoint configured")
        except Exception as e:
            logger.warning("Failed to initialize tracing: %s", e)

        try:
            lineage_config = OpenLineageConfig.from_artifacts(artifacts)
            # Override namespace if provided and different from artifacts
            if namespace != "floe" and lineage_config.namespace == "floe":
                lineage_config = OpenLineageConfig(
                    endpoint=lineage_config.endpoint,
                    namespace=namespace,
                    timeout=lineage_config.timeout,
                )
            if lineage_config.enabled:
                lineage_emitter = OpenLineageEmitter(lineage_config)
                logger.info(
                    "Lineage enabled: endpoint=%s, namespace=%s",
                    lineage_config.endpoint,
                    lineage_config.namespace,
                )
            else:
                logger.debug("Lineage disabled - no endpoint configured")
        except Exception as e:
            logger.warning("Failed to initialize lineage: %s", e)

        return cls(tracing_manager, lineage_emitter)

    @property
    def tracing_enabled(self) -> bool:
        """Check if tracing is enabled and configured."""
        return self.tracing_manager is not None and self.tracing_manager.enabled

    @property
    def lineage_enabled(self) -> bool:
        """Check if lineage is enabled and configured."""
        return self.lineage_emitter is not None and self.lineage_emitter.enabled

    @contextmanager
    def asset_run(
        self,
        asset_name: str,
        *,
        outputs: list[str] | None = None,
        inputs: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[AssetRunContext]:
        """Context manager for asset execution with unified observability.

        Creates an OTel span and emits OpenLineage START/COMPLETE/FAIL events
        automatically. Handles exceptions by recording them to the span and
        emitting a FAIL event before re-raising.

        Args:
            asset_name: Name of the asset being executed
            outputs: Output dataset names for lineage (e.g., ["demo.bronze_customers"])
            inputs: Input dataset names for lineage (optional)
            attributes: Initial span attributes

        Yields:
            AssetRunContext with span and run_id

        Example:
            >>> with orchestrator.asset_run(
            ...     "bronze_customers",
            ...     outputs=["demo.bronze_customers"],
            ...     attributes={"batch_id": "20241224"}
            ... ) as ctx:
            ...     # Execute asset logic
            ...     rows = process_data()
            ...     ctx.set_attribute("rows_processed", rows)

        Raises:
            Any exception from the wrapped code (after recording to observability)
        """
        # Build lineage datasets
        output_datasets = self._build_datasets(outputs) if outputs else None
        input_datasets = self._build_datasets(inputs) if inputs else None

        # Prepare span attributes
        span_attrs = {"asset.name": asset_name}
        if outputs:
            span_attrs["asset.outputs"] = ",".join(outputs)
        if inputs:
            span_attrs["asset.inputs"] = ",".join(inputs)
        if attributes:
            span_attrs.update(attributes)

        # Create context
        ctx = AssetRunContext(asset_name=asset_name)
        if attributes:
            ctx.attributes.update(attributes)

        # Start lineage run (before span for proper timing)
        if self.lineage_emitter is not None:
            try:
                ctx.run_id = self.lineage_emitter.emit_start(
                    job_name=asset_name,
                    inputs=input_datasets,
                    outputs=output_datasets,
                )
            except Exception as e:
                logger.warning("Failed to emit lineage START: %s", e)

        # Execute with tracing
        if self.tracing_manager is not None:
            with self.tracing_manager.start_span(asset_name, span_attrs) as span:
                ctx.span = span
                try:
                    yield ctx
                    # Success - mark span OK and emit COMPLETE
                    self.tracing_manager.set_status_ok(span)
                    self._emit_complete(ctx, input_datasets, output_datasets)
                except Exception as e:
                    # Record exception to span and emit FAIL
                    self.tracing_manager.record_exception(span, e)
                    self._emit_fail(ctx, e, input_datasets, output_datasets)
                    raise
        else:
            # No tracing - just handle lineage
            try:
                yield ctx
                self._emit_complete(ctx, input_datasets, output_datasets)
            except Exception as e:
                self._emit_fail(ctx, e, input_datasets, output_datasets)
                raise

    def _build_datasets(self, names: list[str]) -> list[LineageDataset]:
        """Build LineageDataset objects from dataset names.

        Args:
            names: List of dataset names (e.g., ["demo.bronze_customers"])

        Returns:
            List of LineageDataset objects
        """
        # Determine namespace from emitter config
        namespace = "default"
        if self.lineage_emitter is not None:
            namespace = self.lineage_emitter.config.namespace

        return [LineageDataset(namespace=namespace, name=name) for name in names]

    def _emit_complete(
        self,
        ctx: AssetRunContext,
        inputs: list[LineageDataset] | None,
        outputs: list[LineageDataset] | None,
    ) -> None:
        """Emit lineage COMPLETE event (graceful on failure)."""
        if self.lineage_emitter is None or ctx.run_id is None:
            return

        try:
            self.lineage_emitter.emit_complete(
                run_id=ctx.run_id,
                job_name=ctx.asset_name,
                inputs=inputs,
                outputs=outputs,
            )
        except Exception as e:
            logger.warning("Failed to emit lineage COMPLETE: %s", e)

    def _emit_fail(
        self,
        ctx: AssetRunContext,
        exception: Exception,
        inputs: list[LineageDataset] | None,
        outputs: list[LineageDataset] | None,
    ) -> None:
        """Emit lineage FAIL event (graceful on failure)."""
        if self.lineage_emitter is None or ctx.run_id is None:
            return

        try:
            self.lineage_emitter.emit_fail(
                run_id=ctx.run_id,
                job_name=ctx.asset_name,
                error_message=str(exception),
                inputs=inputs,
                outputs=outputs,
            )
        except Exception as e:
            logger.warning("Failed to emit lineage FAIL: %s", e)

    def shutdown(self) -> None:
        """Shutdown observability components.

        Flushes pending spans and releases resources. Should be called
        at application shutdown.
        """
        if self.tracing_manager is not None:
            try:
                self.tracing_manager.shutdown()
            except Exception as e:
                logger.warning("Error shutting down tracing: %s", e)

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager - shutdown observability."""
        self.shutdown()
