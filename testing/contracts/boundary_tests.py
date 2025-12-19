"""Boundary tests for verifying package contracts.

These tests verify that the contracts between packages are properly
maintained and that models can be correctly serialized/deserialized
across package boundaries.

T022: Core → Dagster boundary
T023: Core → dbt boundary
T024: dbt → Cube boundary
T025: Core → Polaris boundary
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import Any


class TestCoreToDagsterBoundary:
    """Tests for floe-core → floe-dagster contract boundary.

    Verifies that CompiledArtifacts can be properly created in floe-core
    and consumed by floe-dagster.
    """

    @pytest.mark.requirement("FR-006")
    def test_compiled_artifacts_creation(self) -> None:
        """Verify CompiledArtifacts can be created with valid data."""
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

        compute = ComputeConfig(
            target=ComputeTarget.duckdb,
            properties={"path": ":memory:", "threads": 4},
        )

        transforms = [
            TransformConfig(type="dbt", path="./dbt"),
        ]

        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        assert artifacts.version == "1.0.0"
        assert artifacts.metadata.floe_core_version == "0.1.0"
        assert artifacts.compute.target == ComputeTarget.duckdb
        assert len(artifacts.transforms) == 1

    @pytest.mark.requirement("FR-006")
    def test_compiled_artifacts_json_serialization(self) -> None:
        """Verify CompiledArtifacts can be serialized to JSON."""
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123def456",
        )

        compute = ComputeConfig(
            target=ComputeTarget.postgres,
            connection_secret_ref="postgres-creds",
            properties={"host": "localhost", "port": 5432, "database": "test"},
        )

        transforms = [
            TransformConfig(type="dbt", path="./transforms/dbt", target="dev"),
        ]

        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        # Serialize to JSON
        json_str = artifacts.model_dump_json()
        assert isinstance(json_str, str)

        # Parse and verify structure
        data = json.loads(json_str)
        assert data["version"] == "1.0.0"
        assert data["compute"]["target"] == "postgres"
        assert data["transforms"][0]["path"] == "./transforms/dbt"

    @pytest.mark.requirement("FR-006")
    def test_compiled_artifacts_json_deserialization(self) -> None:
        """Verify CompiledArtifacts can be deserialized from JSON."""
        from floe_core.compiler.models import CompiledArtifacts
        from floe_core.schemas import ComputeTarget

        # Create JSON representation
        json_data: dict[str, Any] = {
            "version": "1.0.0",
            "metadata": {
                "compiled_at": "2024-01-01T12:00:00Z",
                "floe_core_version": "0.2.0",
                "source_hash": "deadbeef",
            },
            "compute": {
                "target": "snowflake",
                "connection_secret_ref": "snowflake-prod",
                "properties": {
                    "account": "xy12345.us-east-1",
                    "warehouse": "COMPUTE_WH",
                },
            },
            "transforms": [
                {"type": "dbt", "path": "./dbt", "target": "prod"},
            ],
        }

        # Deserialize
        artifacts = CompiledArtifacts.model_validate(json_data)

        assert artifacts.version == "1.0.0"
        assert artifacts.metadata.floe_core_version == "0.2.0"
        assert artifacts.compute.target == ComputeTarget.snowflake
        assert artifacts.compute.connection_secret_ref == "snowflake-prod"

    @pytest.mark.requirement("FR-006")
    def test_compiled_artifacts_immutability(self) -> None:
        """Verify CompiledArtifacts is immutable (frozen)."""
        from pydantic import ValidationError

        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="test123",
        )

        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        # Attempting to modify should raise error
        with pytest.raises(ValidationError):
            artifacts.version = "2.0.0"  # type: ignore[misc]

    @pytest.mark.requirement("FR-006")
    def test_compiled_artifacts_rejects_extra_fields(self) -> None:
        """Verify CompiledArtifacts rejects unknown fields (extra='forbid')."""
        from pydantic import ValidationError

        from floe_core.compiler.models import CompiledArtifacts

        json_data: dict[str, Any] = {
            "version": "1.0.0",
            "metadata": {
                "compiled_at": "2024-01-01T12:00:00Z",
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "unknown_field": "should_fail",  # Extra field
        }

        with pytest.raises(ValidationError) as exc_info:
            CompiledArtifacts.model_validate(json_data)

        assert "unknown_field" in str(exc_info.value)

    @pytest.mark.requirement("FR-006")
    def test_compiled_artifacts_schema_export(self) -> None:
        """Verify CompiledArtifacts can export JSON Schema."""
        from floe_core.compiler.models import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "version" in schema["properties"]
        assert "metadata" in schema["properties"]
        assert "compute" in schema["properties"]
        assert "transforms" in schema["properties"]


class TestCoreToDbtBoundary:
    """Tests for floe-core → floe-dbt contract boundary.

    Verifies that compute configuration can be used for dbt profile generation.
    """

    @pytest.mark.requirement("FR-006")
    def test_compute_config_for_dbt_profiles(self) -> None:
        """Verify ComputeConfig structure supports dbt profile generation."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        # Test various dbt adapter configurations
        configs = [
            ComputeConfig(
                target=ComputeTarget.duckdb,
                properties={"path": "/data/warehouse.duckdb", "threads": 4},
            ),
            ComputeConfig(
                target=ComputeTarget.postgres,
                connection_secret_ref="pg-creds",
                properties={"host": "localhost", "port": 5432, "database": "analytics"},
            ),
            ComputeConfig(
                target=ComputeTarget.snowflake,
                connection_secret_ref="sf-creds",
                properties={
                    "account": "xy12345",
                    "warehouse": "COMPUTE_WH",
                    "database": "ANALYTICS",
                    "schema": "PUBLIC",
                },
            ),
        ]

        for config in configs:
            # Verify target is a valid dbt adapter name
            assert config.target.value in [
                "duckdb",
                "snowflake",
                "bigquery",
                "redshift",
                "databricks",
                "postgres",
                "spark",
            ]

            # Verify serialization works
            data = config.model_dump()
            assert "target" in data
            assert "properties" in data


class TestDbtToCubeBoundary:
    """Tests for floe-dbt → floe-cube contract boundary.

    Verifies that transform configurations support Cube integration.
    """

    @pytest.mark.requirement("FR-006")
    def test_transform_config_for_cube_integration(self) -> None:
        """Verify TransformConfig can be used for Cube dbt references."""
        from floe_core.schemas import TransformConfig

        config = TransformConfig(
            type="dbt",
            path="./dbt",
            target="prod",
        )

        # Verify structure supports cube_dbt integration
        assert config.type == "dbt"
        assert config.path.startswith("./")
        assert config.target == "prod"

        # Serialize and verify
        data = config.model_dump()
        assert data["type"] == "dbt"
        assert data["path"] == "./dbt"


class TestCoreToPolarisTestBoundary:
    """Tests for floe-core → floe-polaris contract boundary.

    Verifies that CatalogConfig supports Polaris REST catalog integration.
    """

    @pytest.mark.requirement("FR-006")
    def test_catalog_config_for_polaris(self) -> None:
        """Verify CatalogConfig supports Polaris catalog configuration."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
            credential_secret_ref="polaris-creds",
            warehouse="floe_warehouse",
            scope="PRINCIPAL_ROLE:DATA_ENGINEER",
            token_refresh_enabled=True,
            access_delegation="vended-credentials",
        )

        assert config.type == "polaris"
        assert config.uri == "http://polaris:8181/api/catalog"
        assert config.scope == "PRINCIPAL_ROLE:DATA_ENGINEER"
        assert config.token_refresh_enabled is True

    @pytest.mark.requirement("FR-006")
    def test_catalog_config_serialization(self) -> None:
        """Verify CatalogConfig can be serialized for floe-polaris consumption."""
        from floe_core.schemas import CatalogConfig

        config = CatalogConfig(
            type="polaris",
            uri="http://localhost:8181/api/catalog",
            scope="PRINCIPAL_ROLE:TEST_ROLE",
        )

        # Serialize to dict
        data = config.model_dump()
        assert data["type"] == "polaris"
        assert data["uri"] == "http://localhost:8181/api/catalog"
        assert data["scope"] == "PRINCIPAL_ROLE:TEST_ROLE"

        # JSON serialization
        json_str = config.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["type"] == "polaris"

    @pytest.mark.requirement("FR-006")
    def test_catalog_config_in_compiled_artifacts(self) -> None:
        """Verify CatalogConfig integrates with CompiledArtifacts."""
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import (
            CatalogConfig,
            ComputeConfig,
            ComputeTarget,
            TransformConfig,
        )

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="catalog_test_hash",
        )

        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        catalog = CatalogConfig(
            type="polaris",
            uri="http://polaris:8181/api/catalog",
            scope="PRINCIPAL_ROLE:DATA_ENGINEER",
            warehouse="test_warehouse",
        )

        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
            catalog=catalog,
        )

        assert artifacts.catalog is not None
        assert artifacts.catalog.type == "polaris"
        assert artifacts.catalog.warehouse == "test_warehouse"
