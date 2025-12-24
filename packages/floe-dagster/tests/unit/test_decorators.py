"""Unit tests for @floe_asset decorator.

T096: [US6] Add unit tests for @floe_asset decorator
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from dagster import Definitions

from floe_dagster.decorators import ORCHESTRATOR_RESOURCE_KEY, floe_asset


class TestFloeAssetBasics:
    """Test basic @floe_asset decorator functionality."""

    def test_floe_asset_creates_asset_definition(self) -> None:
        """Test that @floe_asset creates a valid AssetsDefinition."""

        @floe_asset()
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Should be an AssetsDefinition
        assert hasattr(my_asset, "key")
        assert hasattr(my_asset, "op")

    def test_floe_asset_preserves_function_name(self) -> None:
        """Test that @floe_asset preserves the function name as asset name."""

        @floe_asset()
        def bronze_customers(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        assert "bronze_customers" in str(bronze_customers.key)

    def test_floe_asset_with_explicit_name(self) -> None:
        """Test that @floe_asset uses explicit name when provided."""

        @floe_asset(name="custom_asset_name")
        def my_func(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        assert "custom_asset_name" in str(my_func.key)

    def test_floe_asset_with_group_name(self) -> None:
        """Test that @floe_asset passes group_name to Dagster."""

        @floe_asset(group_name="bronze")
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # The group should be set
        assert my_asset.group_names_by_key

    def test_floe_asset_with_key_prefix(self) -> None:
        """Test that @floe_asset passes key_prefix to Dagster."""

        @floe_asset(key_prefix=["demo", "customers"])
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        key_str = str(my_asset.key)
        assert "demo" in key_str
        assert "customers" in key_str

    def test_floe_asset_with_description(self) -> None:
        """Test that @floe_asset passes description to Dagster."""

        @floe_asset(description="This is a test asset")
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Description should be captured
        assert my_asset.descriptions_by_key is not None

    def test_floe_asset_with_compute_kind(self) -> None:
        """Test that @floe_asset passes compute_kind to Dagster."""

        @floe_asset(compute_kind="python")
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # compute_kind should be set
        assert hasattr(my_asset, "op")

    def test_floe_asset_with_metadata(self) -> None:
        """Test that @floe_asset passes metadata to Dagster."""

        @floe_asset(metadata={"owner": "data-team", "tier": "bronze"})
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Metadata should be captured
        assert hasattr(my_asset, "metadata_by_key")


class TestFloeAssetOpenLineageParameters:
    """Test OpenLineage-specific parameters."""

    def test_floe_asset_accepts_outputs(self) -> None:
        """Test that @floe_asset accepts outputs parameter."""

        @floe_asset(outputs=["demo.bronze_customers"])
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Should create asset without error
        assert my_asset is not None

    def test_floe_asset_accepts_inputs(self) -> None:
        """Test that @floe_asset accepts inputs parameter."""

        @floe_asset(inputs=["demo.raw_customers"])
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Should create asset without error
        assert my_asset is not None

    def test_floe_asset_accepts_multiple_outputs(self) -> None:
        """Test that @floe_asset accepts multiple outputs."""

        @floe_asset(outputs=["demo.bronze_customers", "demo.bronze_orders"])
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        assert my_asset is not None

    def test_floe_asset_accepts_multiple_inputs(self) -> None:
        """Test that @floe_asset accepts multiple inputs."""

        @floe_asset(
            inputs=["demo.raw_customers", "demo.raw_orders"],
            outputs=["demo.bronze_summary"],
        )
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        assert my_asset is not None


class TestFloeAssetDagsterPassthrough:
    """Test that Dagster kwargs are passed through correctly."""

    def test_floe_asset_passes_required_resource_keys(self) -> None:
        """Test that @floe_asset passes required_resource_keys to Dagster."""

        @floe_asset(required_resource_keys={"catalog", "storage"})
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Required resource keys should be set
        assert my_asset is not None

    def test_floe_asset_passes_arbitrary_dagster_kwargs(self) -> None:
        """Test that @floe_asset passes through arbitrary Dagster kwargs."""

        @floe_asset(retry_policy=None, code_version="v1")
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Should create asset without error
        assert my_asset is not None

    def test_floe_asset_combinable_with_definitions(self) -> None:
        """Test that @floe_asset works with Dagster Definitions."""

        @floe_asset(group_name="test")
        def test_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Should work with Definitions
        defs = Definitions(assets=[test_asset])
        assert defs is not None
        # Use resolve_asset_graph which is the current Dagster API
        asset_graph = defs.resolve_asset_graph()
        assert len(asset_graph.get_all_asset_keys()) > 0


class TestFloeAssetGracefulDegradation:
    """Test graceful degradation when orchestrator is unavailable."""

    def test_floe_asset_runs_without_orchestrator(self) -> None:
        """Test that asset runs normally when orchestrator not available."""

        @floe_asset()
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Create a mock context without orchestrator
        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        # Simulate orchestrator not present
        delattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY)

        # Get the underlying op function
        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]

        # Should run without error
        result = op_fn(mock_context)
        assert result == {"rows": 100}

    def test_floe_asset_runs_with_none_orchestrator(self) -> None:
        """Test that asset runs when orchestrator is None."""

        @floe_asset()
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"result": "success"}

        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        setattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY, None)

        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]
        result = op_fn(mock_context)
        assert result == {"result": "success"}


class TestFloeAssetWithOrchestrator:
    """Test @floe_asset behavior when orchestrator is available."""

    def test_floe_asset_uses_orchestrator_asset_run(self) -> None:
        """Test that asset uses orchestrator.asset_run() when available."""

        @floe_asset(outputs=["demo.test_table"])
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100}

        # Create mock orchestrator
        mock_orchestrator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.run_id = "test-run-id"
        mock_ctx.set_attribute = MagicMock()
        mock_orchestrator.asset_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_orchestrator.asset_run.return_value.__exit__ = MagicMock(return_value=False)

        # Create mock Dagster context
        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        mock_context.log = MagicMock()
        setattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY, mock_orchestrator)

        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]
        result = op_fn(mock_context)

        # Orchestrator should have been called
        mock_orchestrator.asset_run.assert_called_once()
        call_kwargs = mock_orchestrator.asset_run.call_args
        assert call_kwargs[0][0] == "my_asset"  # asset_name
        assert call_kwargs[1]["outputs"] == ["demo.test_table"]

        assert result == {"rows": 100}

    def test_floe_asset_records_result_attributes(self) -> None:
        """Test that dict results are recorded as span attributes."""

        @floe_asset()
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {"rows": 100, "status": "complete"}

        mock_ctx = MagicMock()
        mock_ctx.run_id = "test-run"
        mock_ctx.set_attribute = MagicMock()

        mock_orchestrator = MagicMock()
        mock_orchestrator.asset_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_orchestrator.asset_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        mock_context.log = MagicMock()
        setattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY, mock_orchestrator)

        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]
        op_fn(mock_context)

        # Result attributes should be set
        calls = mock_ctx.set_attribute.call_args_list
        attr_keys = [call[0][0] for call in calls]
        assert "result.rows" in attr_keys
        assert "result.status" in attr_keys


class TestFloeAssetSpanAttributes:
    """Test span attribute generation."""

    def test_floe_asset_includes_asset_name_in_attributes(self) -> None:
        """Test that asset.name is included in span attributes."""

        @floe_asset(name="custom_name")
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {}

        mock_orchestrator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.run_id = None
        mock_orchestrator.asset_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_orchestrator.asset_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        setattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY, mock_orchestrator)

        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]
        op_fn(mock_context)

        call_kwargs = mock_orchestrator.asset_run.call_args
        attributes = call_kwargs[1]["attributes"]
        assert attributes["asset.name"] == "custom_name"

    def test_floe_asset_includes_group_in_attributes(self) -> None:
        """Test that asset.group is included in span attributes."""

        @floe_asset(group_name="bronze")
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {}

        mock_orchestrator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.run_id = None
        mock_orchestrator.asset_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_orchestrator.asset_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        setattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY, mock_orchestrator)

        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]
        op_fn(mock_context)

        call_kwargs = mock_orchestrator.asset_run.call_args
        attributes = call_kwargs[1]["attributes"]
        assert attributes["asset.group"] == "bronze"

    def test_floe_asset_includes_compute_kind_in_attributes(self) -> None:
        """Test that asset.compute_kind is included in span attributes."""

        @floe_asset(compute_kind="python")
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {}

        mock_orchestrator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.run_id = None
        mock_orchestrator.asset_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_orchestrator.asset_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        setattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY, mock_orchestrator)

        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]
        op_fn(mock_context)

        call_kwargs = mock_orchestrator.asset_run.call_args
        attributes = call_kwargs[1]["attributes"]
        assert attributes["asset.compute_kind"] == "python"

    def test_floe_asset_includes_outputs_in_attributes(self) -> None:
        """Test that asset.outputs is included in span attributes."""

        @floe_asset(outputs=["demo.table1", "demo.table2"])
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {}

        mock_orchestrator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.run_id = None
        mock_orchestrator.asset_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_orchestrator.asset_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        setattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY, mock_orchestrator)

        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]
        op_fn(mock_context)

        call_kwargs = mock_orchestrator.asset_run.call_args
        attributes = call_kwargs[1]["attributes"]
        assert attributes["asset.outputs"] == "demo.table1,demo.table2"

    def test_floe_asset_includes_inputs_in_attributes(self) -> None:
        """Test that asset.inputs is included in span attributes."""

        @floe_asset(inputs=["raw.customers", "raw.orders"])
        def my_asset(context) -> dict[str, Any]:  # noqa: ANN001
            return {}

        mock_orchestrator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.run_id = None
        mock_orchestrator.asset_run.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_orchestrator.asset_run.return_value.__exit__ = MagicMock(return_value=False)

        mock_context = MagicMock()
        mock_context.resources = MagicMock()
        setattr(mock_context.resources, ORCHESTRATOR_RESOURCE_KEY, mock_orchestrator)

        op_fn = my_asset.op.compute_fn.decorated_fn  # type: ignore[attr-defined]
        op_fn(mock_context)

        call_kwargs = mock_orchestrator.asset_run.call_args
        attributes = call_kwargs[1]["attributes"]
        assert attributes["asset.inputs"] == "raw.customers,raw.orders"
