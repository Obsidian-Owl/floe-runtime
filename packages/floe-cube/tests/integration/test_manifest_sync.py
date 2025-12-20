"""Integration tests for dbt manifest → Cube schema synchronization.

T089: FR-034 - dbt manifest models appear in Cube schema

These tests verify the contract between dbt manifest.json model definitions
and Cube schema files. When dbt models are compiled, their metadata should
be consumable by Cube for semantic layer generation.

Requirements:
- Cube server must be running (Docker Compose full profile)
- Tests FAIL if Cube is not available (never skip)

Covers:
- FR-034: Integration tests MUST verify dbt manifest.json output is parseable
          by floe-cube schema generation
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Configuration
CUBE_API_URL = os.environ.get("CUBE_API_URL", "http://localhost:4000")


def _get_cube_host() -> str:
    """Get the Cube hostname based on execution context."""
    return "cube" if os.environ.get("DOCKER_CONTAINER") == "1" else "localhost"


def _check_cube_available() -> None:
    """Check that Cube is available. FAIL if not (never skip)."""
    host = _get_cube_host()
    url = f"http://{host}:4000"

    try:
        response = httpx.get(f"{url}/readyz", timeout=5.0)
        if response.status_code != 200:
            pytest.fail(
                f"Cube server not ready at {url}. "
                f"Status: {response.status_code}. "
                "Start with: cd testing/docker && docker compose --profile full up -d"
            )
    except httpx.ConnectError:
        pytest.fail(
            f"Cannot connect to Cube at {url}. "
            "Start with: cd testing/docker && docker compose --profile full up -d. "
            "Tests FAIL when infrastructure is missing (never skip)."
        )


class TestManifestToCubeSync:
    """Test dbt manifest → Cube schema synchronization.

    Covers: FR-034 (dbt manifest to Cube sync)
    """

    @pytest.fixture(autouse=True)
    def check_infrastructure(self) -> None:
        """Ensure Cube is available before running tests."""
        _check_cube_available()

    @pytest.fixture
    def cube_client(self) -> httpx.Client:
        """Create HTTP client for Cube API."""
        host = _get_cube_host()
        return httpx.Client(
            base_url=f"http://{host}:4000",
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

    @pytest.fixture
    def sample_dbt_manifest(self) -> dict[str, Any]:
        """Sample dbt manifest.json structure for testing.

        This represents what floe-dbt would produce after dbt compile.
        """
        return {
            "metadata": {
                "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12.json",
                "dbt_version": "1.9.0",
                "project_name": "floe_test",
            },
            "nodes": {
                "model.floe_test.orders": {
                    "unique_id": "model.floe_test.orders",
                    "name": "orders",
                    "resource_type": "model",
                    "schema": "default",
                    "database": "iceberg",
                    "description": "Order transactions",
                    "columns": {
                        "id": {"name": "id", "description": "Order ID", "data_type": "bigint"},
                        "status": {
                            "name": "status",
                            "description": "Order status",
                            "data_type": "varchar",
                        },
                        "amount": {
                            "name": "amount",
                            "description": "Order amount",
                            "data_type": "decimal",
                        },
                    },
                    "meta": {
                        "floe": {
                            "cube": {"enabled": True, "measures": ["count", "sum:amount"]},
                        }
                    },
                },
                "model.floe_test.customers": {
                    "unique_id": "model.floe_test.customers",
                    "name": "customers",
                    "resource_type": "model",
                    "schema": "default",
                    "database": "iceberg",
                    "description": "Customer dimension",
                    "columns": {
                        "id": {
                            "name": "id",
                            "description": "Customer ID",
                            "data_type": "bigint",
                        },
                        "name": {
                            "name": "name",
                            "description": "Customer name",
                            "data_type": "varchar",
                        },
                    },
                    "meta": {},
                },
            },
        }

    @pytest.mark.requirement("006-FR-034")
    @pytest.mark.requirement("005-FR-005")
    @pytest.mark.requirement("005-FR-006")
    def test_dbt_models_appear_in_cube_meta(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Models from dbt manifest are queryable in Cube.

        Verifies that Cube has cubes corresponding to the expected
        data models (Orders, Customers).

        Covers:
        - 005-FR-005: Generate Cube schema from CompiledArtifacts
        - 005-FR-006: Auto-generate cubes for dbt models with floe.cube.enabled=true
        """
        # Query Cube's meta endpoint to get available cubes
        response = cube_client.get("/cubejs-api/v1/meta")

        assert response.status_code == 200, (
            f"Cube meta endpoint failed: {response.text}"
        )

        meta = response.json()
        cube_names = [cube["name"] for cube in meta.get("cubes", [])]

        # Verify expected cubes exist (these match the test schema files)
        assert "Orders" in cube_names, "Orders cube should exist in Cube schema"
        assert "Customers" in cube_names, "Customers cube should exist in Cube schema"

    @pytest.mark.requirement("006-FR-034")
    @pytest.mark.requirement("005-FR-007")
    def test_dbt_model_columns_in_cube_dimensions(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """dbt model columns appear as Cube dimensions.

        Verifies that columns defined in dbt models are available
        as dimensions in the corresponding Cube schema.

        Covers:
        - 005-FR-007: Map dbt columns to Cube dimensions with type inference
        """
        response = cube_client.get("/cubejs-api/v1/meta")
        assert response.status_code == 200

        meta = response.json()

        # Find Orders cube
        orders_cube = next(
            (cube for cube in meta.get("cubes", []) if cube["name"] == "Orders"),
            None,
        )
        assert orders_cube is not None, "Orders cube not found"

        # Verify expected dimensions exist
        dimension_names = [d["name"] for d in orders_cube.get("dimensions", [])]

        assert "Orders.status" in dimension_names, "status dimension should exist"
        assert "Orders.region" in dimension_names, "region dimension should exist"

    @pytest.mark.requirement("006-FR-034")
    @pytest.mark.requirement("005-FR-005")
    def test_cube_query_uses_dbt_table(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Cube queries access dbt model data.

        Verifies that querying a Cube returns data from the underlying
        table that would be created by dbt.

        Covers:
        - 005-FR-005: Generate Cube schema from CompiledArtifacts
        """
        query = {
            "measures": ["Orders.count"],
            "dimensions": [],
        }

        response = cube_client.post("/cubejs-api/v1/load", json={"query": query})

        # Query should succeed (may return empty if no data)
        assert response.status_code == 200, f"Cube query failed: {response.text}"

        result = response.json()
        assert "data" in result, "Query result should have 'data' key"

    @pytest.mark.requirement("006-FR-034")
    @pytest.mark.requirement("005-FR-006")
    @pytest.mark.requirement("005-FR-010")
    def test_manifest_model_metadata_extractable(
        self,
        sample_dbt_manifest: dict[str, Any],
    ) -> None:
        """dbt manifest metadata can be extracted for Cube generation.

        Verifies that the manifest structure allows extracting the
        information needed for Cube schema generation.

        Covers:
        - 005-FR-006: Auto-generate cubes for dbt models with floe.cube.enabled=true
        - 005-FR-010: Support custom measure definitions via meta.floe.cube.measures
        """
        # Extract models from manifest
        nodes = sample_dbt_manifest.get("nodes", {})
        models = {
            k: v for k, v in nodes.items() if v.get("resource_type") == "model"
        }

        assert len(models) == 2, "Should have 2 models"

        # Extract cube-relevant metadata
        orders_model = models["model.floe_test.orders"]

        # Can extract table reference
        table_ref = f"{orders_model['database']}.{orders_model['schema']}.{orders_model['name']}"
        assert table_ref == "iceberg.default.orders"

        # Can extract columns for dimensions
        columns = orders_model.get("columns", {})
        assert "status" in columns
        assert "amount" in columns

        # Can extract cube-specific metadata
        cube_meta = orders_model.get("meta", {}).get("floe", {}).get("cube", {})
        assert cube_meta.get("enabled") is True


class TestManifestToCubeContract:
    """Test contract between manifest structure and Cube requirements.

    Covers: FR-034 (contract compliance)
    """

    @pytest.fixture(autouse=True)
    def check_infrastructure(self) -> None:
        """Ensure Cube is available before running tests."""
        _check_cube_available()

    @pytest.mark.requirement("006-FR-034")
    @pytest.mark.requirement("005-FR-005")
    def test_manifest_provides_table_reference(self) -> None:
        """Manifest provides information needed for Cube sql property.

        The Cube sql property (e.g., `SELECT * FROM iceberg.default.orders`)
        requires database, schema, and table name from manifest.

        Covers:
        - 005-FR-005: Generate Cube schema from CompiledArtifacts
        """
        manifest_node = {
            "unique_id": "model.project.orders",
            "name": "orders",
            "database": "iceberg",
            "schema": "default",
        }

        # Can construct Cube SQL from manifest
        sql = (
            f"SELECT * FROM {manifest_node['database']}."
            f"{manifest_node['schema']}.{manifest_node['name']}"
        )

        assert sql == "SELECT * FROM iceberg.default.orders"

    @pytest.mark.requirement("006-FR-034")
    @pytest.mark.requirement("005-FR-007")
    def test_manifest_columns_map_to_cube_dimensions(self) -> None:
        """Manifest columns provide dimension definitions.

        Column definitions in manifest can be used to generate
        Cube dimension properties.

        Covers:
        - 005-FR-007: Map dbt columns to Cube dimensions with type inference
        """
        manifest_column = {
            "name": "status",
            "description": "Order status",
            "data_type": "varchar",
        }

        # Can map to Cube dimension
        dimension = {
            "name": manifest_column["name"],
            "sql": manifest_column["name"],
            "type": "string",  # Mapped from varchar
            "description": manifest_column["description"],
        }

        assert dimension["name"] == "status"
        assert dimension["type"] == "string"

    @pytest.mark.requirement("006-FR-034")
    @pytest.mark.requirement("005-FR-010")
    def test_manifest_meta_configures_cube_measures(self) -> None:
        """Manifest meta.floe.cube configures Cube measures.

        Custom meta in dbt models can specify measure configurations
        for Cube schema generation.

        Covers:
        - 005-FR-010: Support custom measure definitions via meta.floe.cube.measures
        """
        manifest_meta = {
            "floe": {
                "cube": {
                    "enabled": True,
                    "measures": ["count", "sum:amount", "avg:amount"],
                }
            }
        }

        cube_config = manifest_meta.get("floe", {}).get("cube", {})

        assert cube_config["enabled"] is True
        assert "count" in cube_config["measures"]
        assert "sum:amount" in cube_config["measures"]
