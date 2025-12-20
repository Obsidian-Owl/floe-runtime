"""Integration tests for Dagster asset materialization with Iceberg IOManager.

These tests require a running Polaris + LocalStack stack. Use Docker Compose to start:

    cd testing/docker
    docker compose --profile storage up -d

Run tests with:

    pytest -m integration packages/floe-iceberg/tests/integration/

Environment variables:
    POLARIS_URI: Polaris REST API URL (default: http://localhost:8181/api/catalog)
    POLARIS_WAREHOUSE: Warehouse name (default: warehouse)
    POLARIS_CLIENT_ID: OAuth2 client ID (default: root)
    POLARIS_CLIENT_SECRET: OAuth2 client secret (default: s3cr3t)
    LOCALSTACK_ENDPOINT: LocalStack S3 endpoint (default: http://localhost:4566)
"""

from __future__ import annotations

import contextlib
import os
import uuid
import warnings
from collections.abc import Generator

import pandas as pd
import pyarrow as pa
import pytest
from dagster import (
    AssetKey,
    Definitions,
    asset,
    build_input_context,
    build_output_context,
    materialize,
)
from floe_polaris import (
    PolarisCatalog,
    PolarisCatalogConfig,
    create_catalog,
)

from floe_iceberg import (
    IcebergIOManager,
    IcebergIOManagerConfig,
    IcebergTableManager,
    WriteMode,
    create_io_manager,
)

# =============================================================================
# Test Configuration
# =============================================================================


def get_test_config() -> PolarisCatalogConfig:
    """Get Polaris configuration for TESTING ONLY.

    Note: scope="PRINCIPAL_ROLE:ALL" grants maximum privileges and should
    ONLY be used in test environments. Production deployments must use
    narrowly-scoped principal roles following least privilege principle.
    """
    return PolarisCatalogConfig(
        uri=os.environ.get("POLARIS_URI", "http://localhost:8181/api/catalog"),
        warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
        client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
        client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
        # TESTING ONLY: PRINCIPAL_ROLE:ALL grants all roles - never use in production!
        scope=os.environ.get("POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL"),
    )


def get_io_manager_config(namespace: str) -> IcebergIOManagerConfig:
    """Get Iceberg IOManager configuration for TESTING ONLY.

    Note: scope="PRINCIPAL_ROLE:ALL" grants maximum privileges and should
    ONLY be used in test environments. Production deployments must use
    narrowly-scoped principal roles following least privilege principle.

    LocalStack provides proper STS credential vending support, but we still
    provide static S3 credentials as a fallback for simpler test setups.
    In production with AWS S3, vended credentials would be used instead.
    """
    return IcebergIOManagerConfig(
        catalog_uri=os.environ.get("POLARIS_URI", "http://localhost:8181/api/catalog"),
        warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
        client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
        client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
        # TESTING ONLY: PRINCIPAL_ROLE:ALL grants all roles - never use in production!
        scope=os.environ.get("POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL"),
        default_namespace=namespace,
        write_mode=WriteMode.APPEND,
        auto_create_tables=True,
        schema_evolution_enabled=True,
        # LocalStack S3 credentials - static credentials for local testing
        # In production with AWS S3, vended credentials from Polaris would be used instead
        s3_endpoint=os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566"),
        s3_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        s3_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        s3_region=os.environ.get("AWS_REGION", "us-east-1"),
    )


def is_polaris_available() -> bool:
    """Check if Polaris is available for testing.

    Uses context-aware hostname detection:
    - Inside Docker container (DOCKER_CONTAINER=1): connects to 'polaris:8181'
    - On host machine: connects to 'localhost:8181'
    """
    import socket

    # Use internal hostname when running in Docker container
    host = "polaris" if os.environ.get("DOCKER_CONTAINER") == "1" else "localhost"

    try:
        with socket.create_connection((host, 8181), timeout=2):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def get_polaris_host() -> str:
    """Get the Polaris hostname based on execution context."""
    return "polaris" if os.environ.get("DOCKER_CONTAINER") == "1" else "localhost"


# Skip all tests if Polaris is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not is_polaris_available(),
        reason=f"Polaris server not available at {get_polaris_host()}:8181",
    ),
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def catalog() -> Generator[PolarisCatalog, None, None]:
    """Provide connected catalog instance for the module."""
    # Suppress expected warning for PRINCIPAL_ROLE:ALL in test environment
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
        config = get_test_config()
        cat = create_catalog(config)
    yield cat


@pytest.fixture(scope="module")
def table_manager(catalog: PolarisCatalog) -> IcebergTableManager:
    """Provide IcebergTableManager instance."""
    return IcebergTableManager(catalog)


@pytest.fixture(scope="module")
def test_namespace(catalog: PolarisCatalog) -> Generator[str, None, None]:
    """Provide a unique test namespace for the module."""
    ns_name = f"dagster_test_{uuid.uuid4().hex[:8]}"

    # Create namespace
    catalog.create_namespace(ns_name)

    yield ns_name

    # Cleanup: Drop namespace (tables cleaned up by individual tests)
    with contextlib.suppress(Exception):
        catalog.drop_namespace(ns_name)


@pytest.fixture
def io_manager_config(test_namespace: str) -> IcebergIOManagerConfig:
    """Provide IOManager configuration."""
    # Suppress expected warning for PRINCIPAL_ROLE:ALL in test environment
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
        return get_io_manager_config(test_namespace)


@pytest.fixture
def io_manager(
    io_manager_config: IcebergIOManagerConfig,
) -> IcebergIOManager:
    """Provide configured IOManager instance.

    Note: We don't pass a pre-configured catalog here because the IOManager
    needs to create its own catalog with S3 credentials for LocalStack access.
    """
    return create_io_manager(io_manager_config)


# =============================================================================
# IOManager Basic Tests (US4)
# =============================================================================


class TestIOManagerBasics:
    """Tests for basic IOManager functionality."""

    @pytest.mark.requirement("006-FR-014")
    def test_create_io_manager(
        self,
        io_manager_config: IcebergIOManagerConfig,
    ) -> None:
        """Test IOManager creation from config."""
        io_manager = create_io_manager(io_manager_config)

        assert io_manager is not None
        assert io_manager.catalog_uri == io_manager_config.catalog_uri
        assert io_manager.warehouse == io_manager_config.warehouse

    @pytest.mark.requirement("006-FR-014")
    def test_get_table_identifier_single_part(
        self,
        io_manager: IcebergIOManager,
        test_namespace: str,
    ) -> None:
        """Test asset key mapping for single-part keys."""
        context = build_output_context(
            asset_key=AssetKey(["customers"]),
        )

        table_id = io_manager.get_table_identifier(context)

        assert table_id == f"{test_namespace}.customers"

    @pytest.mark.requirement("006-FR-014")
    def test_get_table_identifier_two_parts(
        self,
        io_manager: IcebergIOManager,
    ) -> None:
        """Test asset key mapping for two-part keys."""
        context = build_output_context(
            asset_key=AssetKey(["bronze", "customers"]),
        )

        table_id = io_manager.get_table_identifier(context)

        assert table_id == "bronze.customers"

    @pytest.mark.requirement("006-FR-014")
    def test_get_table_identifier_multi_parts(
        self,
        io_manager: IcebergIOManager,
    ) -> None:
        """Test asset key mapping for multi-part keys."""
        context = build_output_context(
            asset_key=AssetKey(["gold", "metrics", "daily"]),
        )

        table_id = io_manager.get_table_identifier(context)

        assert table_id == "gold.metrics_daily"


# =============================================================================
# Handle Output Tests (US4)
# =============================================================================


class TestHandleOutput:
    """Tests for handle_output (writing assets to Iceberg)."""

    @pytest.mark.requirement("006-FR-014")
    def test_handle_output_arrow_table(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test writing PyArrow Table output."""
        table_name = f"output_arrow_{uuid.uuid4().hex[:8]}"
        asset_key = AssetKey([test_namespace, table_name])
        full_table = f"{test_namespace}.{table_name}"

        context = build_output_context(asset_key=asset_key)

        data = pa.Table.from_pydict(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
            }
        )

        try:
            # Initialize IOManager
            io_manager.setup_for_execution(None)

            # Write output
            io_manager.handle_output(context, data)

            # Verify data was written
            result = table_manager.scan(full_table)
            assert result.num_rows == 3
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)

    @pytest.mark.requirement("006-FR-014")
    def test_handle_output_dataframe(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test writing Pandas DataFrame output."""
        table_name = f"output_df_{uuid.uuid4().hex[:8]}"
        asset_key = AssetKey([test_namespace, table_name])
        full_table = f"{test_namespace}.{table_name}"

        context = build_output_context(asset_key=asset_key)

        data = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "value": ["a", "b", "c"],
            }
        )

        try:
            io_manager.setup_for_execution(None)
            io_manager.handle_output(context, data)

            result = table_manager.scan(full_table)
            assert result.num_rows == 3
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)

    @pytest.mark.requirement("006-FR-014")
    def test_handle_output_append_mode(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test multiple appends accumulate data."""
        table_name = f"output_append_{uuid.uuid4().hex[:8]}"
        asset_key = AssetKey([test_namespace, table_name])
        full_table = f"{test_namespace}.{table_name}"

        context = build_output_context(asset_key=asset_key)

        batch1 = pa.Table.from_pydict({"id": [1, 2], "value": ["a", "b"]})
        batch2 = pa.Table.from_pydict({"id": [3, 4], "value": ["c", "d"]})

        try:
            io_manager.setup_for_execution(None)

            # First write
            io_manager.handle_output(context, batch1)
            # Second write (append)
            io_manager.handle_output(context, batch2)

            result = table_manager.scan(full_table)
            assert result.num_rows == 4
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)

    @pytest.mark.requirement("006-FR-014")
    def test_handle_output_overwrite_mode(
        self,
        io_manager_config: IcebergIOManagerConfig,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test overwrite mode replaces all data."""
        # Create IOManager with overwrite mode - inherit all config from fixture
        # Note: Don't pass pre-configured catalog - let IOManager create its own with S3 creds
        # Suppress expected warning for PRINCIPAL_ROLE:ALL in test environment
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="scope='PRINCIPAL_ROLE:ALL'")
            config = IcebergIOManagerConfig(
                catalog_uri=io_manager_config.catalog_uri,
                warehouse=io_manager_config.warehouse,
                client_id=io_manager_config.client_id,
                client_secret=io_manager_config.client_secret,
                scope=io_manager_config.scope,  # TESTING ONLY: inherit scope from fixture
                default_namespace=test_namespace,
                write_mode=WriteMode.OVERWRITE,
                auto_create_tables=True,
                # Inherit S3 config from fixture for LocalStack testing
                s3_endpoint=io_manager_config.s3_endpoint,
                s3_access_key_id=io_manager_config.s3_access_key_id,
                s3_secret_access_key=io_manager_config.s3_secret_access_key,
                s3_region=io_manager_config.s3_region,
            )
        io_manager = create_io_manager(config)

        table_name = f"output_overwrite_{uuid.uuid4().hex[:8]}"
        asset_key = AssetKey([test_namespace, table_name])
        full_table = f"{test_namespace}.{table_name}"

        context = build_output_context(asset_key=asset_key)

        batch1 = pa.Table.from_pydict({"id": [1, 2], "value": ["a", "b"]})
        batch2 = pa.Table.from_pydict({"id": [100], "value": ["replaced"]})

        try:
            io_manager.setup_for_execution(None)

            # First write
            io_manager.handle_output(context, batch1)
            # Second write (overwrite)
            io_manager.handle_output(context, batch2)

            result = table_manager.scan(full_table)
            assert result.num_rows == 1  # Only replacement data
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)


# =============================================================================
# Load Input Tests (US5)
# =============================================================================


class TestLoadInput:
    """Tests for load_input (reading assets from Iceberg)."""

    @pytest.mark.requirement("006-FR-014")
    def test_load_input_all_data(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test reading all data from a table."""
        table_name = f"input_all_{uuid.uuid4().hex[:8]}"
        full_table = f"{test_namespace}.{table_name}"

        # Create table and write data
        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("name", pa.string()),
            ]
        )
        data = pa.Table.from_pydict({"id": [1, 2, 3], "name": ["a", "b", "c"]})

        try:
            table_manager.create_table(full_table, schema)
            table_manager.append(full_table, data)

            io_manager.setup_for_execution(None)

            # Create input context
            context = build_input_context(
                asset_key=AssetKey([test_namespace, table_name]),
            )

            result = io_manager.load_input(context)

            assert isinstance(result, pa.Table)
            assert result.num_rows == 3
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)

    @pytest.mark.requirement("006-FR-014")
    def test_load_input_with_columns(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test column projection in load_input."""
        table_name = f"input_cols_{uuid.uuid4().hex[:8]}"
        full_table = f"{test_namespace}.{table_name}"

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("name", pa.string()),
                pa.field("value", pa.float64()),
            ]
        )
        data = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
                "value": [1.0, 2.0],
            }
        )

        try:
            table_manager.create_table(full_table, schema)
            table_manager.append(full_table, data)

            io_manager.setup_for_execution(None)

            # Request only specific columns
            context = build_input_context(
                asset_key=AssetKey([test_namespace, table_name]),
                metadata={"columns": ["id", "name"]},
            )

            result = io_manager.load_input(context)

            assert result.num_columns == 2
            assert "id" in result.column_names
            assert "name" in result.column_names
            assert "value" not in result.column_names
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)

    @pytest.mark.requirement("006-FR-014")
    def test_load_input_with_limit(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test row limit in load_input."""
        table_name = f"input_limit_{uuid.uuid4().hex[:8]}"
        full_table = f"{test_namespace}.{table_name}"

        schema = pa.schema([pa.field("id", pa.int64())])
        data = pa.Table.from_pydict({"id": list(range(100))})

        try:
            table_manager.create_table(full_table, schema)
            table_manager.append(full_table, data)

            io_manager.setup_for_execution(None)

            context = build_input_context(
                asset_key=AssetKey([test_namespace, table_name]),
                metadata={"limit": 10},
            )

            result = io_manager.load_input(context)

            assert result.num_rows == 10
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)


# =============================================================================
# Full Dagster Integration Tests
# =============================================================================


class TestDagsterIntegration:
    """End-to-end tests with Dagster materialize()."""

    @pytest.mark.requirement("006-FR-014")
    def test_materialize_simple_asset(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test materializing a simple asset."""
        table_name = f"simple_asset_{uuid.uuid4().hex[:8]}"
        full_table = f"{test_namespace}.{table_name}"

        @asset(key=[test_namespace, table_name])
        def simple_asset() -> pa.Table:
            return pa.Table.from_pydict(
                {
                    "id": [1, 2, 3],
                    "message": ["hello", "world", "!"],
                }
            )

        try:
            Definitions(
                assets=[simple_asset],
                resources={"io_manager": io_manager},
            )

            result = materialize(
                [simple_asset],
                resources={"io_manager": io_manager},
            )

            assert result.success

            # Verify data in Iceberg
            data = table_manager.scan(full_table)
            assert data.num_rows == 3
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)

    @pytest.mark.requirement("006-FR-014")
    def test_materialize_asset_chain(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test materializing dependent assets."""
        source_table = f"chain_source_{uuid.uuid4().hex[:8]}"
        derived_table = f"chain_derived_{uuid.uuid4().hex[:8]}"
        full_source = f"{test_namespace}.{source_table}"
        full_derived = f"{test_namespace}.{derived_table}"

        @asset(key=[test_namespace, source_table])
        def source_asset() -> pa.Table:
            return pa.Table.from_pydict(
                {
                    "id": [1, 2, 3],
                    "value": [10, 20, 30],
                }
            )

        @asset(
            key=[test_namespace, derived_table],
            deps=[AssetKey([test_namespace, source_table])],
        )
        def derived_asset() -> pa.Table:
            # In a real scenario, this would read from source
            return pa.Table.from_pydict(
                {
                    "id": [1, 2, 3],
                    "value_doubled": [20, 40, 60],
                }
            )

        try:
            result = materialize(
                [source_asset, derived_asset],
                resources={"io_manager": io_manager},
            )

            assert result.success

            # Verify both tables exist
            source_data = table_manager.scan(full_source)
            derived_data = table_manager.scan(full_derived)

            assert source_data.num_rows == 3
            assert derived_data.num_rows == 3
        finally:
            for t in [full_source, full_derived]:
                with contextlib.suppress(Exception):
                    table_manager.drop_table(t)


# =============================================================================
# Schema Evolution Tests
# =============================================================================


class TestSchemaEvolutionIntegration:
    """Tests for schema evolution during asset materialization."""

    @pytest.mark.requirement("006-FR-014")
    def test_auto_add_columns(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test that new columns are added automatically."""
        table_name = f"schema_evo_{uuid.uuid4().hex[:8]}"
        full_table = f"{test_namespace}.{table_name}"

        try:
            io_manager.setup_for_execution(None)

            # First write with basic schema
            context1 = build_output_context(asset_key=AssetKey([test_namespace, table_name]))
            data1 = pa.Table.from_pydict({"id": [1], "name": ["Alice"]})
            io_manager.handle_output(context1, data1)

            # Second write with additional column
            context2 = build_output_context(asset_key=AssetKey([test_namespace, table_name]))
            data2 = pa.Table.from_pydict(
                {
                    "id": [2],
                    "name": ["Bob"],
                    "email": ["bob@example.com"],  # New column!
                }
            )
            io_manager.handle_output(context2, data2)

            # Verify schema evolved
            result = table_manager.scan(full_table)
            assert "email" in result.column_names
            assert result.num_rows == 2
        finally:
            with contextlib.suppress(Exception):
                table_manager.drop_table(full_table)
