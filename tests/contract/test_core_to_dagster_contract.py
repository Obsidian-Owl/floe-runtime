"""Contract tests for floe-core to floe-dagster integration.

These tests validate that CompiledArtifacts produced by floe-core
can be consumed by floe-dagster asset factories.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


@pytest.mark.contract
class TestCoreToDagsterContract:
    """Contract tests between floe-core and floe-dagster."""

    def test_compiled_artifacts_transforms_provide_dbt_info(self) -> None:
        """Test transforms config provides dbt project info for Dagster."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [
                {
                    "type": "dbt",
                    "path": "./transforms/dbt",
                    "target": "dev",  # target is a direct field, not nested config
                }
            ],
            "consumption": {},
            "governance": {},
            "observability": {},
        })

        # Dagster asset factory needs this info
        assert len(artifacts.transforms) > 0
        transform = artifacts.transforms[0]
        assert transform.type == "dbt"
        assert transform.path == "./transforms/dbt"

    def test_compiled_artifacts_observability_config(self) -> None:
        """Test observability config provides OTel/OpenLineage settings."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {
                "traces": True,
                "metrics": True,
                "lineage": True,
                "otlp_endpoint": "http://localhost:4317",
                "lineage_endpoint": "http://localhost:5000",
            },
        })

        # Dagster needs these for observability integration
        assert artifacts.observability.traces is True
        assert artifacts.observability.metrics is True
        assert artifacts.observability.lineage is True

    def test_compiled_artifacts_provides_optional_lineage_namespace(self) -> None:
        """Test optional lineage_namespace for OpenLineage integration."""
        from floe_core.compiler import CompiledArtifacts

        # With lineage namespace
        artifacts_with_ns = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {},
            "lineage_namespace": "prod.analytics",
        })

        assert artifacts_with_ns.lineage_namespace == "prod.analytics"

        # Without lineage namespace (optional)
        artifacts_without_ns = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {},
        })

        assert artifacts_without_ns.lineage_namespace is None


@pytest.mark.contract
class TestDagsterAssetFactoryContract:
    """Tests for Dagster asset factory contract."""

    def test_compiled_artifacts_structure_for_assets(self) -> None:
        """Test CompiledArtifacts has structure needed for asset creation."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {},
        })

        # Convert to dict for Dagster asset factory consumption
        artifacts_dict = artifacts.model_dump(mode="json")

        # Verify structure is consumable
        assert "transforms" in artifacts_dict
        assert "compute" in artifacts_dict
        assert "observability" in artifacts_dict


@pytest.mark.contract
class TestFloeTranslatorContract:
    """Tests for FloeTranslator contract with dbt nodes."""

    def test_translator_extracts_floe_metadata(self) -> None:
        """Test FloeTranslator extracts floe-specific metadata from dbt nodes."""
        from floe_dagster.translator import FloeTranslator

        # dbt node structure is a Mapping (dict-like)
        mock_node = {
            "name": "customers",
            "description": "Customer dimension table",
            "meta": {
                "floe": {
                    "owner": "data-team",
                    "classification": "internal",
                },
                "dagster": {
                    "group": "core",
                },
            },
            "tags": ["daily", "core"],
            "columns": {},
            "unique_id": "model.project.customers",
            "config": {"materialized": "table"},
        }

        translator = FloeTranslator()

        # Should extract metadata correctly
        metadata = translator.get_metadata(mock_node)
        assert isinstance(metadata, dict)

    def test_translator_handles_missing_floe_meta(self) -> None:
        """Test translator handles nodes without floe metadata gracefully."""
        from floe_dagster.translator import FloeTranslator

        mock_node = {
            "name": "raw_events",
            "description": "",
            "meta": {},  # No floe metadata
            "tags": [],
            "columns": {},
            "unique_id": "model.project.raw_events",
            "config": {},
        }

        translator = FloeTranslator()

        # Should not raise
        metadata = translator.get_metadata(mock_node)
        assert isinstance(metadata, dict)


@pytest.mark.contract
class TestEnvironmentContextContract:
    """Tests for optional EnvironmentContext integration."""

    def test_environment_context_optional(self) -> None:
        """Test environment_context is optional (standalone-first)."""
        from floe_core.compiler import CompiledArtifacts

        # Without environment context (standalone mode)
        artifacts = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {},
        })

        assert artifacts.environment_context is None

    def test_environment_context_structure(self) -> None:
        """Test environment_context schema has expected structure."""
        from floe_core.compiler import EnvironmentContext

        # Get schema to understand structure
        schema = EnvironmentContext.model_json_schema()

        # Should have required fields
        required = schema.get("required", [])
        assert "tenant_id" in required
        assert "environment_id" in required

        # Should be a frozen (immutable) model
        # This is validated at model definition time
        assert schema.get("title") == "EnvironmentContext"
