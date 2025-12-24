"""Unit tests for ObservabilityOrchestrator.

T092: [US6] Add unit tests for graceful degradation
T093: [US6] Add unit tests for exception handling
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


class TestAssetRunContext:
    """Tests for AssetRunContext dataclass."""

    def test_create_context_with_defaults(self) -> None:
        """Test creating context with default values."""
        from floe_dagster.observability.orchestrator import AssetRunContext

        ctx = AssetRunContext()

        assert ctx.span is None
        assert ctx.run_id is None
        assert ctx.asset_name == ""
        assert ctx.attributes == {}

    def test_create_context_with_values(self) -> None:
        """Test creating context with provided values."""
        from floe_dagster.observability.orchestrator import AssetRunContext

        mock_span = MagicMock()
        ctx = AssetRunContext(
            span=mock_span,
            run_id="test-run-id",
            asset_name="bronze_customers",
        )

        assert ctx.span == mock_span
        assert ctx.run_id == "test-run-id"
        assert ctx.asset_name == "bronze_customers"

    def test_set_attribute_stores_in_dict(self) -> None:
        """Test set_attribute stores value in attributes dict."""
        from floe_dagster.observability.orchestrator import AssetRunContext

        ctx = AssetRunContext()
        ctx.set_attribute("rows_processed", 1000)

        assert ctx.attributes["rows_processed"] == 1000

    def test_set_attribute_updates_span(self) -> None:
        """Test set_attribute updates the OTel span if present."""
        from floe_dagster.observability.orchestrator import AssetRunContext

        mock_span = MagicMock()
        ctx = AssetRunContext(span=mock_span)

        ctx.set_attribute("batch_id", "20241224")

        mock_span.set_attribute.assert_called_once_with("batch_id", "20241224")

    def test_set_attribute_handles_no_span(self) -> None:
        """Test set_attribute works when span is None."""
        from floe_dagster.observability.orchestrator import AssetRunContext

        ctx = AssetRunContext(span=None)

        # Should not raise
        ctx.set_attribute("key", "value")
        assert ctx.attributes["key"] == "value"

    def test_set_attribute_handles_span_error(self) -> None:
        """Test set_attribute gracefully handles span errors."""
        from floe_dagster.observability.orchestrator import AssetRunContext

        mock_span = MagicMock()
        mock_span.set_attribute.side_effect = RuntimeError("Span error")
        ctx = AssetRunContext(span=mock_span)

        # Should not raise, should still store attribute
        ctx.set_attribute("key", "value")
        assert ctx.attributes["key"] == "value"


class TestObservabilityOrchestrator:
    """Tests for ObservabilityOrchestrator."""

    @pytest.fixture
    def mock_tracing_manager(self) -> MagicMock:
        """Create mock TracingManager."""
        manager = MagicMock()
        manager.enabled = True

        # Set up start_span as a context manager
        mock_span = MagicMock()
        manager.start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        manager.start_span.return_value.__exit__ = MagicMock(return_value=False)

        return manager

    @pytest.fixture
    def mock_lineage_emitter(self) -> MagicMock:
        """Create mock OpenLineageEmitter."""
        emitter = MagicMock()
        emitter.enabled = True
        emitter.emit_start.return_value = "test-run-id-123"
        emitter.config.namespace = "test-namespace"
        return emitter

    def test_create_orchestrator_with_components(
        self,
        mock_tracing_manager: MagicMock,
        mock_lineage_emitter: MagicMock,
    ) -> None:
        """Test creating orchestrator with both components."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            tracing_manager=mock_tracing_manager,
            lineage_emitter=mock_lineage_emitter,
        )

        assert orchestrator.tracing_manager == mock_tracing_manager
        assert orchestrator.lineage_emitter == mock_lineage_emitter

    def test_create_orchestrator_without_components(self) -> None:
        """Test creating orchestrator with None components (graceful degradation)."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            tracing_manager=None,
            lineage_emitter=None,
        )

        assert orchestrator.tracing_manager is None
        assert orchestrator.lineage_emitter is None
        assert orchestrator.tracing_enabled is False
        assert orchestrator.lineage_enabled is False

    def test_tracing_enabled_property(
        self,
        mock_tracing_manager: MagicMock,
    ) -> None:
        """Test tracing_enabled property."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(mock_tracing_manager, None)
        assert orchestrator.tracing_enabled is True

        mock_tracing_manager.enabled = False
        assert orchestrator.tracing_enabled is False

    def test_lineage_enabled_property(
        self,
        mock_lineage_emitter: MagicMock,
    ) -> None:
        """Test lineage_enabled property."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(None, mock_lineage_emitter)
        assert orchestrator.lineage_enabled is True

        mock_lineage_emitter.enabled = False
        assert orchestrator.lineage_enabled is False


class TestObservabilityOrchestratorAssetRun:
    """Tests for ObservabilityOrchestrator.asset_run() context manager."""

    @pytest.fixture
    def mock_tracing_manager(self) -> MagicMock:
        """Create mock TracingManager with context manager behavior."""
        manager = MagicMock()
        manager.enabled = True

        # Create mock span
        mock_span = MagicMock()

        # Make start_span work as a context manager
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=mock_span)
        cm.__exit__ = MagicMock(return_value=False)
        manager.start_span.return_value = cm

        return manager

    @pytest.fixture
    def mock_lineage_emitter(self) -> MagicMock:
        """Create mock OpenLineageEmitter."""
        emitter = MagicMock()
        emitter.enabled = True
        emitter.emit_start.return_value = "test-run-id-123"
        emitter.config.namespace = "test-namespace"
        return emitter

    def test_asset_run_creates_span_and_lineage(
        self,
        mock_tracing_manager: MagicMock,
        mock_lineage_emitter: MagicMock,
    ) -> None:
        """Test asset_run creates span and emits lineage START."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            mock_tracing_manager,
            mock_lineage_emitter,
        )

        with orchestrator.asset_run("bronze_customers") as ctx:
            assert ctx.asset_name == "bronze_customers"
            assert ctx.run_id == "test-run-id-123"
            assert ctx.span is not None

        # Verify lineage events
        mock_lineage_emitter.emit_start.assert_called_once()
        mock_lineage_emitter.emit_complete.assert_called_once()

    def test_asset_run_with_outputs(
        self,
        mock_tracing_manager: MagicMock,
        mock_lineage_emitter: MagicMock,
    ) -> None:
        """Test asset_run creates datasets from output names."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            mock_tracing_manager,
            mock_lineage_emitter,
        )

        with orchestrator.asset_run(
            "bronze_customers",
            outputs=["demo.bronze_customers"],
        ) as ctx:
            assert ctx is not None

        # Verify outputs passed to lineage
        call_args = mock_lineage_emitter.emit_start.call_args
        outputs = call_args.kwargs.get("outputs") or call_args[1].get("outputs")
        assert len(outputs) == 1
        assert outputs[0].name == "demo.bronze_customers"

    def test_asset_run_with_inputs(
        self,
        mock_tracing_manager: MagicMock,
        mock_lineage_emitter: MagicMock,
    ) -> None:
        """Test asset_run creates datasets from input names."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            mock_tracing_manager,
            mock_lineage_emitter,
        )

        with orchestrator.asset_run(
            "silver_orders",
            inputs=["demo.bronze_orders", "demo.bronze_customers"],
            outputs=["demo.silver_orders"],
        ) as ctx:
            assert ctx is not None

        # Verify inputs passed to lineage
        call_args = mock_lineage_emitter.emit_start.call_args
        inputs = call_args.kwargs.get("inputs") or call_args[1].get("inputs")
        assert len(inputs) == 2

    def test_asset_run_with_attributes(
        self,
        mock_tracing_manager: MagicMock,
        mock_lineage_emitter: MagicMock,
    ) -> None:
        """Test asset_run passes attributes to span."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            mock_tracing_manager,
            mock_lineage_emitter,
        )

        with orchestrator.asset_run(
            "bronze_customers",
            attributes={"batch_id": "20241224"},
        ) as ctx:
            assert ctx.attributes["batch_id"] == "20241224"

        # Verify span was created with attributes
        mock_tracing_manager.start_span.assert_called_once()
        call_args = mock_tracing_manager.start_span.call_args
        span_attrs = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
        assert "asset.name" in span_attrs

    def test_asset_run_emits_fail_on_exception(
        self,
        mock_tracing_manager: MagicMock,
        mock_lineage_emitter: MagicMock,
    ) -> None:
        """Test asset_run emits FAIL event on exception."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            mock_tracing_manager,
            mock_lineage_emitter,
        )

        with pytest.raises(ValueError), orchestrator.asset_run("failing_asset"):
            raise ValueError("Something went wrong")

        # Verify FAIL was emitted instead of COMPLETE
        mock_lineage_emitter.emit_complete.assert_not_called()
        mock_lineage_emitter.emit_fail.assert_called_once()

        # Verify error message
        call_args = mock_lineage_emitter.emit_fail.call_args
        error_msg = call_args.kwargs.get("error_message", call_args[1].get("error_message", ""))
        assert "Something went wrong" in error_msg

    def test_asset_run_records_exception_to_span(
        self,
        mock_tracing_manager: MagicMock,
        mock_lineage_emitter: MagicMock,
    ) -> None:
        """Test asset_run records exception to span before re-raising."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            mock_tracing_manager,
            mock_lineage_emitter,
        )

        with pytest.raises(RuntimeError), orchestrator.asset_run("failing_asset"):
            raise RuntimeError("Pipeline failed")

        # Verify exception was recorded
        mock_tracing_manager.record_exception.assert_called_once()
        call_args = mock_tracing_manager.record_exception.call_args
        exception = call_args[0][1]
        assert isinstance(exception, RuntimeError)
        assert str(exception) == "Pipeline failed"


class TestObservabilityOrchestratorGracefulDegradation:
    """Tests for graceful degradation when observability unavailable."""

    def test_asset_run_without_tracing(self) -> None:
        """Test asset_run works when tracing is None."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        mock_emitter = MagicMock()
        mock_emitter.enabled = True
        mock_emitter.emit_start.return_value = "run-id"
        mock_emitter.config.namespace = "test"

        orchestrator = ObservabilityOrchestrator(
            tracing_manager=None,
            lineage_emitter=mock_emitter,
        )

        with orchestrator.asset_run("my_asset") as ctx:
            assert ctx.span is None  # No tracing
            assert ctx.run_id == "run-id"  # But lineage works

        mock_emitter.emit_complete.assert_called_once()

    def test_asset_run_without_lineage(self) -> None:
        """Test asset_run works when lineage is None."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        mock_manager = MagicMock()
        mock_manager.enabled = True
        mock_span = MagicMock()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=mock_span)
        cm.__exit__ = MagicMock(return_value=False)
        mock_manager.start_span.return_value = cm

        orchestrator = ObservabilityOrchestrator(
            tracing_manager=mock_manager,
            lineage_emitter=None,
        )

        with orchestrator.asset_run("my_asset") as ctx:
            assert ctx.span is not None  # Tracing works
            assert ctx.run_id is None  # No lineage

        mock_manager.start_span.assert_called_once()

    def test_asset_run_without_both(self) -> None:
        """Test asset_run works when both are None."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        orchestrator = ObservabilityOrchestrator(
            tracing_manager=None,
            lineage_emitter=None,
        )

        # Should not raise, should execute normally
        result = None
        with orchestrator.asset_run("my_asset") as ctx:
            assert ctx.span is None
            assert ctx.run_id is None
            result = "executed"

        assert result == "executed"

    def test_asset_run_handles_lineage_start_failure(self) -> None:
        """Test asset_run continues if lineage emit_start fails."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        mock_emitter = MagicMock()
        mock_emitter.enabled = True
        mock_emitter.emit_start.side_effect = RuntimeError("Network error")
        mock_emitter.config.namespace = "test"

        orchestrator = ObservabilityOrchestrator(
            tracing_manager=None,
            lineage_emitter=mock_emitter,
        )

        # Should not raise - graceful degradation
        result = None
        with orchestrator.asset_run("my_asset") as ctx:
            result = "executed"
            assert ctx.run_id is None  # Failed to get run_id

        assert result == "executed"

    def test_asset_run_handles_lineage_complete_failure(self) -> None:
        """Test asset_run continues if lineage emit_complete fails."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        mock_emitter = MagicMock()
        mock_emitter.enabled = True
        mock_emitter.emit_start.return_value = "run-id"
        mock_emitter.emit_complete.side_effect = RuntimeError("Network error")
        mock_emitter.config.namespace = "test"

        orchestrator = ObservabilityOrchestrator(
            tracing_manager=None,
            lineage_emitter=mock_emitter,
        )

        # Should not raise - graceful degradation
        result = None
        with orchestrator.asset_run("my_asset"):
            result = "executed"

        assert result == "executed"

    def test_asset_run_exception_still_raised_after_lineage_fail_failure(self) -> None:
        """Test business exceptions are raised even if lineage fail fails."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        mock_emitter = MagicMock()
        mock_emitter.enabled = True
        mock_emitter.emit_start.return_value = "run-id"
        mock_emitter.emit_fail.side_effect = RuntimeError("Lineage network error")
        mock_emitter.config.namespace = "test"

        orchestrator = ObservabilityOrchestrator(
            tracing_manager=None,
            lineage_emitter=mock_emitter,
        )

        # Business exception should still be raised
        with (
            pytest.raises(ValueError, match="Business error"),
            orchestrator.asset_run("my_asset"),
        ):
            raise ValueError("Business error")


class TestObservabilityOrchestratorFromArtifacts:
    """Tests for ObservabilityOrchestrator.from_compiled_artifacts()."""

    def test_from_compiled_artifacts_with_observability(self) -> None:
        """Test creating orchestrator from artifacts with observability config."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        artifacts = {
            "observability": {
                "tracing": {
                    "endpoint": "http://localhost:4317",
                    "service_name": "test-service",
                },
                "lineage": {
                    "endpoint": "http://localhost:5000/api/v1/lineage",
                    "namespace": "test",
                },
            },
        }

        orchestrator = ObservabilityOrchestrator.from_compiled_artifacts(artifacts)

        assert orchestrator.tracing_manager is not None
        assert orchestrator.lineage_emitter is not None

    def test_from_compiled_artifacts_without_observability(self) -> None:
        """Test creating orchestrator from artifacts without observability config."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        artifacts: dict[str, Any] = {}

        orchestrator = ObservabilityOrchestrator.from_compiled_artifacts(artifacts)

        # Should still create orchestrator with disabled components
        assert orchestrator.tracing_enabled is False
        assert orchestrator.lineage_enabled is False

    def test_from_compiled_artifacts_uses_namespace(self) -> None:
        """Test namespace parameter is used in lineage config."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        artifacts = {
            "observability": {
                "lineage": {
                    "endpoint": "http://localhost:5000/api/v1/lineage",
                },
            },
        }

        orchestrator = ObservabilityOrchestrator.from_compiled_artifacts(
            artifacts,
            namespace="custom-namespace",
        )

        assert orchestrator.lineage_emitter is not None
        assert orchestrator.lineage_emitter.config.namespace == "custom-namespace"


class TestObservabilityOrchestratorLifecycle:
    """Tests for ObservabilityOrchestrator lifecycle management."""

    def test_shutdown_calls_tracing_shutdown(self) -> None:
        """Test shutdown calls tracing manager shutdown."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        mock_manager = MagicMock()
        orchestrator = ObservabilityOrchestrator(mock_manager, None)

        orchestrator.shutdown()

        mock_manager.shutdown.assert_called_once()

    def test_shutdown_handles_errors(self) -> None:
        """Test shutdown handles errors gracefully."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        mock_manager = MagicMock()
        mock_manager.shutdown.side_effect = RuntimeError("Shutdown error")
        orchestrator = ObservabilityOrchestrator(mock_manager, None)

        # Should not raise
        orchestrator.shutdown()

    def test_context_manager_interface(self) -> None:
        """Test orchestrator can be used as context manager."""
        from floe_dagster.observability.orchestrator import ObservabilityOrchestrator

        mock_manager = MagicMock()
        orchestrator = ObservabilityOrchestrator(mock_manager, None)

        with orchestrator as orch:
            assert orch is orchestrator

        mock_manager.shutdown.assert_called_once()
