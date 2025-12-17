"""Integration tests for Dagster asset materialization with Iceberg IOManager.

These tests require a running Polaris + MinIO stack. Use Docker Compose to start:

    cd testing/docker
    docker compose --profile storage up -d

Run tests with:

    pytest -m integration packages/floe-iceberg/tests/integration/

Environment variables:
    POLARIS_URI: Polaris REST API URL (default: http://localhost:8181/api/catalog)
    POLARIS_WAREHOUSE: Warehouse name (default: warehouse)
    POLARIS_CLIENT_ID: OAuth2 client ID (default: root)
    POLARIS_CLIENT_SECRET: OAuth2 client secret (default: s3cr3t)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Generator

import pandas as pd
import pyarrow as pa
import pytest
from dagster import (
    AssetIn,
    AssetKey,
    DailyPartitionsDefinition,
    Definitions,
    InputContext,
    OutputContext,
    asset,
    build_input_context,
    build_output_context,
    materialize,
)

from floe_iceberg import (
    IcebergIOManager,
    IcebergIOManagerConfig,
    IcebergTableManager,
    WriteMode,
    create_io_manager,
)
from floe_polaris import (
    PolarisCatalog,
    PolarisCatalogConfig,
    create_catalog,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Test Configuration
# =============================================================================


def get_test_config() -> PolarisCatalogConfig:
    """Get Polaris configuration from environment or defaults."""
    return PolarisCatalogConfig(
        uri=os.environ.get("POLARIS_URI", "http://localhost:8181/api/catalog"),
        warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
        client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
        client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
    )


def get_io_manager_config(namespace: str) -> IcebergIOManagerConfig:
    """Get Iceberg IOManager configuration."""
    return IcebergIOManagerConfig(
        catalog_uri=os.environ.get("POLARIS_URI", "http://localhost:8181/api/catalog"),
        warehouse=os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
        client_id=os.environ.get("POLARIS_CLIENT_ID", "root"),
        client_secret=os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
        default_namespace=namespace,
        write_mode=WriteMode.APPEND,
        auto_create_tables=True,
        schema_evolution_enabled=True,
    )


def is_polaris_available() -> bool:
    """Check if Polaris is available for testing."""
    import socket

    try:
        with socket.create_connection(("localhost", 8181), timeout=2):
            return True
    except (OSError, ConnectionRefusedError):
        return False


# Skip all tests if Polaris is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not is_polaris_available(),
        reason="Polaris server not available at localhost:8181",
    ),
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def catalog() -> Generator[PolarisCatalog, None, None]:
    """Provide connected catalog instance for the module."""
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
    try:
        catalog.drop_namespace(ns_name)
    except Exception:
        pass


@pytest.fixture
def io_manager_config(test_namespace: str) -> IcebergIOManagerConfig:
    """Provide IOManager configuration."""
    return get_io_manager_config(test_namespace)


@pytest.fixture
def io_manager(
    io_manager_config: IcebergIOManagerConfig,
    catalog: PolarisCatalog,
) -> IcebergIOManager:
    """Provide configured IOManager instance."""
    return create_io_manager(io_manager_config, catalog=catalog.inner_catalog)


# =============================================================================
# IOManager Basic Tests (US4)
# =============================================================================


class TestIOManagerBasics:
    """Tests for basic IOManager functionality."""

    def test_create_io_manager(
        self,
        io_manager_config: IcebergIOManagerConfig,
    ) -> None:
        """Test IOManager creation from config."""
        io_manager = create_io_manager(io_manager_config)

        assert io_manager is not None
        assert io_manager.catalog_uri == io_manager_config.catalog_uri
        assert io_manager.warehouse == io_manager_config.warehouse

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

        data = pa.Table.from_pydict({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
        })

        try:
            # Initialize IOManager
            io_manager.setup_for_execution(None)

            # Write output
            io_manager.handle_output(context, data)

            # Verify data was written
            result = table_manager.scan(full_table)
            assert result.num_rows == 3
        finally:
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass

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

        data = pd.DataFrame({
            "id": [1, 2, 3],
            "value": ["a", "b", "c"],
        })

        try:
            io_manager.setup_for_execution(None)
            io_manager.handle_output(context, data)

            result = table_manager.scan(full_table)
            assert result.num_rows == 3
        finally:
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass

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
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass

    def test_handle_output_overwrite_mode(
        self,
        io_manager_config: IcebergIOManagerConfig,
        catalog: PolarisCatalog,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test overwrite mode replaces all data."""
        # Create IOManager with overwrite mode
        config = IcebergIOManagerConfig(
            catalog_uri=io_manager_config.catalog_uri,
            warehouse=io_manager_config.warehouse,
            client_id=io_manager_config.client_id,
            client_secret=io_manager_config.client_secret,
            default_namespace=test_namespace,
            write_mode=WriteMode.OVERWRITE,
            auto_create_tables=True,
        )
        io_manager = create_io_manager(config, catalog=catalog.inner_catalog)

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
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass


# =============================================================================
# Load Input Tests (US5)
# =============================================================================


class TestLoadInput:
    """Tests for load_input (reading assets from Iceberg)."""

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
        schema = pa.schema([
            pa.field("id", pa.int64()),
            pa.field("name", pa.string()),
        ])
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
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass

    def test_load_input_with_columns(
        self,
        io_manager: IcebergIOManager,
        table_manager: IcebergTableManager,
        test_namespace: str,
    ) -> None:
        """Test column projection in load_input."""
        table_name = f"input_cols_{uuid.uuid4().hex[:8]}"
        full_table = f"{test_namespace}.{table_name}"

        schema = pa.schema([
            pa.field("id", pa.int64()),
            pa.field("name", pa.string()),
            pa.field("value", pa.float64()),
        ])
        data = pa.Table.from_pydict({
            "id": [1, 2],
            "name": ["a", "b"],
            "value": [1.0, 2.0],
        })

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
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass

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
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass


# =============================================================================
# Full Dagster Integration Tests
# =============================================================================


class TestDagsterIntegration:
    """End-to-end tests with Dagster materialize()."""

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
            return pa.Table.from_pydict({
                "id": [1, 2, 3],
                "message": ["hello", "world", "!"],
            })

        try:
            defs = Definitions(
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
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass

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
            return pa.Table.from_pydict({
                "id": [1, 2, 3],
                "value": [10, 20, 30],
            })

        @asset(
            key=[test_namespace, derived_table],
            deps=[AssetKey([test_namespace, source_table])],
        )
        def derived_asset() -> pa.Table:
            # In a real scenario, this would read from source
            return pa.Table.from_pydict({
                "id": [1, 2, 3],
                "value_doubled": [20, 40, 60],
            })

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
                try:
                    table_manager.drop_table(t)
                except Exception:
                    pass


# =============================================================================
# Schema Evolution Tests
# =============================================================================


class TestSchemaEvolutionIntegration:
    """Tests for schema evolution during asset materialization."""

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
            context1 = build_output_context(
                asset_key=AssetKey([test_namespace, table_name])
            )
            data1 = pa.Table.from_pydict({"id": [1], "name": ["Alice"]})
            io_manager.handle_output(context1, data1)

            # Second write with additional column
            context2 = build_output_context(
                asset_key=AssetKey([test_namespace, table_name])
            )
            data2 = pa.Table.from_pydict({
                "id": [2],
                "name": ["Bob"],
                "email": ["bob@example.com"],  # New column!
            })
            io_manager.handle_output(context2, data2)

            # Verify schema evolved
            result = table_manager.scan(full_table)
            assert "email" in result.column_names
            assert result.num_rows == 2
        finally:
            try:
                table_manager.drop_table(full_table)
            except Exception:
                pass
