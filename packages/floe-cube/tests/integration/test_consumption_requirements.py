"""Integration tests for Consumption Layer requirements.

These tests cover the remaining 7 gaps in Feature 005 traceability:
- FR-001: Generate Cube config from ConsumptionConfig
- FR-002: Support all database_type values (postgres, snowflake, bigquery, databricks, trino)
- FR-003: Reference K8s secrets for credentials (never embed)
- FR-004: Generate valid cube.js configuration file
- FR-009: Handle incremental sync (update existing cubes, not duplicate)
- FR-028: Auto-trigger model sync when manifest.json changes
- FR-030: Rename tenant_column to filter_column, default to "organization_id"

Run with:
    ./testing/docker/scripts/run-integration-tests.sh \
        -k "test_consumption_requirements"
"""

from __future__ import annotations

import json
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import pytest

from floe_cube.config import (
    SUPPORTED_DATABASE_TYPES,
    CubeConfigGenerator,
    get_cube_driver_type,
    validate_database_type,
)
from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
from floe_cube.watcher import ManifestWatcher, WatcherError, WatcherState


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_consumption_config() -> dict[str, Any]:
    """Provide a sample ConsumptionConfig dictionary."""
    return {
        "enabled": True,
        "database_type": "postgres",
        "port": 4000,
        "api_secret_ref": "cube-api-secret",
        "security": {
            "row_level": True,
            "filter_column": "organization_id",
        },
        "pre_aggregations": {
            "enabled": True,
            "refresh_schedule": "0 0 * * *",
            "timezone": "America/New_York",
        },
        "observability": {
            "openlineage_endpoint": "http://marquez:5000/api/v1/lineage",
            "openlineage_namespace": "floe-cube",
        },
    }


@pytest.fixture
def sample_dbt_manifest() -> dict[str, Any]:
    """Provide a sample dbt manifest.json structure."""
    return {
        "metadata": {"dbt_schema_version": "1.0"},
        "nodes": {
            "model.test.customers": {
                "name": "customers",
                "resource_type": "model",
                "schema": "public",
                "database": "analytics",
                "description": "Customer dimension table",
                "columns": {
                    "id": {"name": "id", "data_type": "integer", "description": "Primary key"},
                    "name": {"name": "name", "data_type": "varchar", "description": "Customer name"},
                    "email": {"name": "email", "data_type": "text"},
                    "created_at": {"name": "created_at", "data_type": "timestamp"},
                    "organization_id": {"name": "organization_id", "data_type": "integer"},
                },
                "meta": {
                    "cube": {
                        "measures": [
                            {"name": "count", "type": "count"},
                            {"name": "unique_count", "type": "count_distinct", "sql": "id"},
                        ]
                    }
                },
            },
            "model.test.orders": {
                "name": "orders",
                "resource_type": "model",
                "schema": "public",
                "database": "analytics",
                "description": "Order fact table",
                "columns": {
                    "id": {"name": "id", "data_type": "integer"},
                    "customer_id": {"name": "customer_id", "data_type": "integer"},
                    "amount": {"name": "amount", "data_type": "numeric"},
                    "order_date": {"name": "order_date", "data_type": "date"},
                },
                "meta": {
                    "cube": {
                        "measures": [
                            {"name": "count", "type": "count"},
                            {"name": "total_amount", "type": "sum", "sql": "amount"},
                        ],
                        "joins": [
                            {
                                "name": "customers",
                                "relationship": "many_to_one",
                                "sql": "${CUBE}.customer_id = ${customers}.id",
                            }
                        ],
                    }
                },
            },
        },
    }


# =============================================================================
# Configuration Generation Tests (FR-001, FR-002, FR-003, FR-004)
# =============================================================================


class TestConfigurationGeneration:
    """Tests for Cube configuration generation (005-FR-001, 002, 003, 004)."""

    @pytest.mark.requirement("005-FR-001")
    def test_generate_cube_config_from_consumption_config(
        self,
        sample_consumption_config: dict[str, Any],
    ) -> None:
        """Test generating Cube config from ConsumptionConfig.

        Covers:
        - 005-FR-001: System MUST generate Cube configuration from ConsumptionConfig
        """
        generator = CubeConfigGenerator(sample_consumption_config)
        config = generator.generate()

        # Verify essential config values are present
        assert "CUBEJS_DB_TYPE" in config
        assert "CUBEJS_API_PORT" in config
        assert config["CUBEJS_DB_TYPE"] == "postgres"
        assert config["CUBEJS_API_PORT"] == "4000"

    @pytest.mark.requirement("005-FR-002")
    def test_all_database_types_supported(self) -> None:
        """Test that all required database types are supported.

        Covers:
        - 005-FR-002: System MUST support all database_type values:
                      postgres, snowflake, bigquery, databricks, trino
        """
        required_types = {"postgres", "snowflake", "bigquery", "databricks", "trino"}

        # All required types should be in SUPPORTED_DATABASE_TYPES
        for db_type in required_types:
            assert db_type in SUPPORTED_DATABASE_TYPES, f"{db_type} not in supported types"

        # Each type should map to a valid Cube driver
        driver_mappings = {
            "postgres": "postgres",
            "snowflake": "snowflake",
            "bigquery": "bigquery",
            "databricks": "databricks-jdbc",
            "trino": "trino",
        }

        for db_type, expected_driver in driver_mappings.items():
            actual_driver = get_cube_driver_type(db_type)
            assert actual_driver == expected_driver

    @pytest.mark.requirement("005-FR-002")
    def test_generate_config_for_each_database_type(self) -> None:
        """Test configuration generation for each database type.

        Covers:
        - 005-FR-002: System MUST support all database_type values
        """
        for db_type in ["postgres", "snowflake", "bigquery", "databricks", "trino"]:
            config = {"database_type": db_type, "port": 4000}
            generator = CubeConfigGenerator(config)
            result = generator.generate()

            assert "CUBEJS_DB_TYPE" in result
            # Validate no error was raised

    @pytest.mark.requirement("005-FR-003")
    def test_kubernetes_secret_references(
        self,
        sample_consumption_config: dict[str, Any],
    ) -> None:
        """Test that secrets are referenced, not embedded.

        Covers:
        - 005-FR-003: System MUST reference Kubernetes secrets for API credentials
        """
        generator = CubeConfigGenerator(sample_consumption_config)
        config = generator.generate()

        # API secret should be a reference, not embedded
        assert "CUBEJS_API_SECRET" in config
        api_secret_value = config["CUBEJS_API_SECRET"]

        # Should use K8s secret reference syntax ${SECRET_NAME}
        assert api_secret_value.startswith("${")
        assert api_secret_value.endswith("}")
        assert "cube-api-secret" in api_secret_value

    @pytest.mark.requirement("005-FR-003")
    def test_no_plaintext_secrets_in_config(self) -> None:
        """Test that plaintext secrets are never embedded.

        Covers:
        - 005-FR-003: System MUST reference Kubernetes secrets (never embed secrets)
        """
        config_with_secret_ref = {
            "database_type": "postgres",
            "port": 4000,
            "api_secret_ref": "my-api-secret",
            "cube_store": {
                "s3_access_key_ref": "s3-access-key-secret",
                "s3_secret_key_ref": "s3-secret-key-secret",
            },
        }

        generator = CubeConfigGenerator(config_with_secret_ref)
        result = generator.generate()

        # All secret values should use reference syntax
        for key, value in result.items():
            if "SECRET" in key or "ACCESS_KEY" in key:
                assert value.startswith("${"), f"{key} should use secret reference syntax"

    @pytest.mark.requirement("005-FR-004")
    def test_generate_valid_cube_js_file(
        self,
        sample_consumption_config: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test generating valid cube.js configuration file.

        Covers:
        - 005-FR-004: System MUST generate valid cube.js configuration file format
        """
        generator = CubeConfigGenerator(sample_consumption_config)
        content = generator.generate_file_content()

        # Should be valid JavaScript module
        assert "module.exports" in content
        assert "// Cube configuration generated by floe-cube" in content

        # Write and verify the file can be parsed
        output_path = generator.write_config(tmp_path)
        assert output_path.exists()
        assert output_path.name == "cube.js"

        # Content should be readable
        written_content = output_path.read_text()
        assert "CUBEJS_DB_TYPE" in written_content


# =============================================================================
# Model Sync Tests (FR-009)
# =============================================================================


class TestModelSync:
    """Tests for model synchronization (005-FR-009)."""

    @pytest.mark.requirement("005-FR-009")
    def test_incremental_sync_updates_not_duplicates(
        self,
        sample_dbt_manifest: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test that sync updates existing cubes without duplicating.

        Covers:
        - 005-FR-009: System MUST handle incremental sync (update existing cubes, not duplicate)
        """
        output_dir = tmp_path / "cube_schemas"

        # First sync
        parser1 = DbtManifestParser(sample_dbt_manifest)
        sync1 = ModelSynchronizer(parser1)
        files1 = sync1.write_schemas(output_dir)

        initial_file_count = len(files1)
        assert initial_file_count == 2  # customers and orders

        # Get initial content
        customers_content_1 = (output_dir / "customers.yaml").read_text()

        # Modify manifest (add column to customers)
        sample_dbt_manifest["nodes"]["model.test.customers"]["columns"]["status"] = {
            "name": "status",
            "data_type": "varchar",
            "description": "Customer status",
        }

        # Second sync (incremental)
        parser2 = DbtManifestParser(sample_dbt_manifest)
        sync2 = ModelSynchronizer(parser2)
        files2 = sync2.write_schemas(output_dir)

        # Should still have same number of files (updated, not duplicated)
        assert len(files2) == initial_file_count

        # Content should be updated (has new column)
        customers_content_2 = (output_dir / "customers.yaml").read_text()
        assert "status" in customers_content_2
        assert customers_content_1 != customers_content_2

        # Verify no duplicate files
        yaml_files = list(output_dir.glob("*.yaml"))
        assert len(yaml_files) == initial_file_count

    @pytest.mark.requirement("005-FR-009")
    def test_sync_removes_nothing_preserves_all(
        self,
        sample_dbt_manifest: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test that sync preserves existing cubes when models change.

        Covers:
        - 005-FR-009: System MUST handle incremental sync
        """
        output_dir = tmp_path / "cube_schemas"

        # First sync with both models
        parser1 = DbtManifestParser(sample_dbt_manifest)
        sync1 = ModelSynchronizer(parser1)
        sync1.write_schemas(output_dir)

        assert (output_dir / "customers.yaml").exists()
        assert (output_dir / "orders.yaml").exists()

        # Add a new model to manifest
        sample_dbt_manifest["nodes"]["model.test.products"] = {
            "name": "products",
            "resource_type": "model",
            "schema": "public",
            "database": "analytics",
            "columns": {
                "id": {"name": "id", "data_type": "integer"},
                "name": {"name": "name", "data_type": "varchar"},
            },
            "meta": {},
        }

        # Second sync
        parser2 = DbtManifestParser(sample_dbt_manifest)
        sync2 = ModelSynchronizer(parser2)
        sync2.write_schemas(output_dir)

        # All three should exist
        assert (output_dir / "customers.yaml").exists()
        assert (output_dir / "orders.yaml").exists()
        assert (output_dir / "products.yaml").exists()


# =============================================================================
# Manifest Watcher Tests (FR-028)
# =============================================================================


class TestManifestWatcher:
    """Tests for manifest.json change detection (005-FR-028)."""

    @pytest.mark.requirement("005-FR-028")
    def test_watcher_detects_manifest_changes(
        self,
        sample_dbt_manifest: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test that watcher detects manifest.json changes.

        Covers:
        - 005-FR-028: System MUST automatically trigger model sync when
                      manifest.json changes are detected
        """
        manifest_dir = tmp_path / "target"
        manifest_dir.mkdir()
        manifest_path = manifest_dir / "manifest.json"
        output_dir = tmp_path / "cube_schemas"

        # Write initial manifest
        manifest_path.write_text(json.dumps(sample_dbt_manifest))

        # Track sync callbacks
        sync_count = 0
        synced_manifests: list[dict[str, Any]] = []

        def on_sync(manifest: dict[str, Any]) -> None:
            nonlocal sync_count
            sync_count += 1
            synced_manifests.append(manifest)

        # Create and start watcher
        watcher = ManifestWatcher(
            manifest_path=manifest_path,
            output_dir=output_dir,
            debounce_seconds=0.1,  # Short debounce for testing
            on_sync=on_sync,
        )

        try:
            watcher.start()
            assert watcher.state == WatcherState.RUNNING

            # Modify manifest
            sample_dbt_manifest["nodes"]["model.test.products"] = {
                "name": "products",
                "resource_type": "model",
                "schema": "public",
                "columns": {"id": {"name": "id", "data_type": "integer"}},
                "meta": {},
            }
            manifest_path.write_text(json.dumps(sample_dbt_manifest))

            # Wait for debounce + processing
            time.sleep(0.5)

            # Verify sync was triggered
            assert sync_count >= 1, "Sync should have been triggered"

        finally:
            watcher.stop()
            assert watcher.state == WatcherState.STOPPED

    @pytest.mark.requirement("005-FR-028")
    def test_watcher_context_manager(
        self,
        sample_dbt_manifest: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test watcher context manager functionality.

        Covers:
        - 005-FR-028: System MUST automatically trigger model sync
        """
        manifest_dir = tmp_path / "target"
        manifest_dir.mkdir()
        manifest_path = manifest_dir / "manifest.json"
        manifest_path.write_text(json.dumps(sample_dbt_manifest))
        output_dir = tmp_path / "cube_schemas"

        with ManifestWatcher(
            manifest_path=manifest_path,
            output_dir=output_dir,
            debounce_seconds=0.1,
        ) as watcher:
            assert watcher.state == WatcherState.RUNNING

        # Should be stopped after context exit
        assert watcher.state == WatcherState.STOPPED

    @pytest.mark.requirement("005-FR-028")
    def test_watcher_directory_must_exist(
        self,
        tmp_path: Path,
    ) -> None:
        """Test watcher fails if directory doesn't exist.

        Covers:
        - 005-FR-028: Auto-trigger model sync when manifest.json changes detected
        """
        non_existent_path = tmp_path / "nonexistent" / "manifest.json"

        with pytest.raises(WatcherError) as exc_info:
            ManifestWatcher(
                manifest_path=non_existent_path,
                output_dir=tmp_path / "output",
            )

        assert "does not exist" in str(exc_info.value)


# =============================================================================
# Schema Field Rename Tests (FR-030)
# =============================================================================


class TestFilterColumnRename:
    """Tests for tenant_column -> filter_column rename (005-FR-030)."""

    @pytest.mark.requirement("005-FR-030")
    def test_filter_column_exists_in_security_config(self) -> None:
        """Test that filter_column field exists in CubeSecurityConfig.

        Covers:
        - 005-FR-030: System MUST update floe-core CubeSecurityConfig schema
                      to rename `tenant_column` to `filter_column`
        """
        from floe_core.schemas import CubeSecurityConfig

        # Create config with filter_column
        config = CubeSecurityConfig(
            row_level=True,
            filter_column="department_id",
        )

        assert hasattr(config, "filter_column")
        assert config.filter_column == "department_id"

    @pytest.mark.requirement("005-FR-030")
    def test_filter_column_default_is_organization_id(self) -> None:
        """Test that filter_column default is 'organization_id'.

        Covers:
        - 005-FR-030: Change default from `"tenant_id"` to `"organization_id"`
        """
        from floe_core.schemas import CubeSecurityConfig

        # Create config without specifying filter_column
        config = CubeSecurityConfig(row_level=True)

        # Default should be organization_id (not tenant_id)
        assert config.filter_column == "organization_id"

    @pytest.mark.requirement("005-FR-030")
    def test_filter_column_in_consumption_config_security(self) -> None:
        """Test that filter_column is available via ConsumptionConfig.security.

        Covers:
        - 005-FR-030: Update floe-core CubeSecurityConfig schema
        """
        from floe_core.schemas import ConsumptionConfig, CubeSecurityConfig

        config = ConsumptionConfig(
            enabled=True,
            database_type="postgres",
            port=4000,
            security=CubeSecurityConfig(
                row_level=True,
                filter_column="region_id",
            ),
        )

        assert config.security is not None
        assert config.security.filter_column == "region_id"

    @pytest.mark.requirement("005-FR-030")
    def test_filter_column_serializes_correctly(self) -> None:
        """Test that filter_column serializes correctly in JSON.

        Covers:
        - 005-FR-030: Rename tenant_column to filter_column
        """
        from floe_core.schemas import CubeSecurityConfig

        config = CubeSecurityConfig(
            row_level=True,
            filter_column="organization_id",
        )

        json_data = config.model_dump()

        assert "filter_column" in json_data
        assert json_data["filter_column"] == "organization_id"

        # Should NOT have tenant_column
        assert "tenant_column" not in json_data
