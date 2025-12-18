"""Contract tests for schema stability.

T015: [US1] Contract test - generated config matches cube-config.schema.json
T025: [US2] Contract test - generated schemas match cube-schema.schema.json

These tests ensure that generated artifacts conform to their JSON schemas,
providing contract stability between floe-cube and downstream consumers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


class TestCubeConfigContractStability:
    """Contract tests for Cube configuration schema stability."""

    @pytest.fixture
    def cube_config_schema(self) -> dict[str, Any]:
        """Load the cube-config JSON schema."""
        # Path: packages/floe-cube/tests/contract/test_schema_stability.py
        # parent (1): packages/floe-cube/tests/contract/
        # parent (2): packages/floe-cube/tests/
        # parent (3): packages/floe-cube/
        # parent (4): packages/
        # parent (5): project root
        project_root = Path(__file__).parent.parent.parent.parent.parent

        schema_path = (
            project_root
            / "packages"
            / "floe-core"
            / "src"
            / "floe_core"
            / "schemas"
            / "json"
            / "cube-config.schema.json"
        )
        if not schema_path.exists():
            # Try alternate location in contracts directory
            schema_path = (
                project_root
                / "specs"
                / "005-consumption-layer"
                / "contracts"
                / "cube-config.schema.json"
            )
        if not schema_path.exists():
            pytest.fail(
                f"cube-config.schema.json not found. Searched:\n"
                f"  - {project_root / 'packages/floe-core/src/floe_core/schemas/json/cube-config.schema.json'}\n"
                f"  - {project_root / 'specs/005-consumption-layer/contracts/cube-config.schema.json'}"
            )

        return json.loads(schema_path.read_text())

    @pytest.fixture
    def minimal_consumption_config(self) -> dict[str, Any]:
        """Minimal ConsumptionConfig for contract testing."""
        return {
            "enabled": True,
            "database_type": "postgres",
            "port": 4000,
            "api_secret_ref": None,
            "dev_mode": False,
            "pre_aggregations": {
                "refresh_schedule": "*/30 * * * *",
                "timezone": "UTC",
            },
            "security": {
                "row_level": True,
                "filter_column": "organization_id",
            },
        }

    def test_input_config_validates_against_schema(
        self,
        cube_config_schema: dict[str, Any],
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Input consumption config should validate against cube-config.schema.json.

        Note: cube-config.schema.json defines the input configuration format
        (what goes in floe.yaml), NOT the output environment variables.
        """
        import jsonschema

        # The schema defines input configuration structure
        # Transform our test config to match schema expectations
        input_config = {
            "database_type": minimal_consumption_config["database_type"],
            "api_port": minimal_consumption_config.get("port", 4000),
            "dev_mode": minimal_consumption_config.get("dev_mode", False),
        }

        # Add optional fields if present
        if minimal_consumption_config.get("api_secret_ref"):
            input_config["api_secret_ref"] = minimal_consumption_config["api_secret_ref"]

        if minimal_consumption_config.get("pre_aggregations"):
            input_config["pre_aggregations"] = minimal_consumption_config["pre_aggregations"]

        if minimal_consumption_config.get("security"):
            security = minimal_consumption_config["security"]
            input_config["row_level_security"] = {
                "enabled": security.get("row_level", True),
                "filter_column": security.get("filter_column", "organization_id"),
            }

        # Validate against JSON schema
        try:
            jsonschema.validate(input_config, cube_config_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Input config does not match schema: {e.message}")

    def test_all_database_types_validate_against_schema(
        self,
        cube_config_schema: dict[str, Any],
    ) -> None:
        """All supported database types should be valid in schema."""
        import jsonschema

        # Database types supported by the schema
        database_types = [
            "postgres",
            "snowflake",
            "bigquery",
            "databricks",
            "trino",
        ]

        for db_type in database_types:
            input_config = {
                "database_type": db_type,
                "api_port": 4000,
            }

            try:
                jsonschema.validate(input_config, cube_config_schema)
            except jsonschema.ValidationError as e:
                pytest.fail(
                    f"Config for {db_type} does not match schema: {e.message}"
                )

    def test_config_includes_required_fields(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Generated config should include all required fields."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        # Required fields for Cube configuration
        required_fields = [
            "CUBEJS_DB_TYPE",
            "CUBEJS_API_PORT",
        ]

        for field in required_fields:
            assert field in config, f"Required field {field} missing from config"


class TestCubeSchemaContractStability:
    """Contract tests for Cube schema (cube YAML) stability.

    These tests ensure generated cube schemas match cube-schema.schema.json,
    which will be implemented as part of User Story 2 (T025).
    """

    @pytest.fixture
    def cube_schema_json_schema(self) -> dict[str, Any]:
        """Load the cube-schema JSON schema."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        schema_path = (
            project_root
            / "specs"
            / "005-consumption-layer"
            / "contracts"
            / "cube-schema.schema.json"
        )
        if not schema_path.exists():
            pytest.fail(f"cube-schema.schema.json not found at {schema_path}")

        return json.loads(schema_path.read_text())

    def test_cube_schema_model_matches_json_schema(
        self,
        cube_schema_json_schema: dict[str, Any],
    ) -> None:
        """CubeSchema Pydantic model should produce schema-compliant output."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        from floe_cube.models import (
            CubeDimension,
            CubeMeasure,
            CubeSchema,
            DimensionType,
            MeasureType,
        )

        # Create a sample CubeSchema
        schema = CubeSchema(
            name="orders",
            sql_table="public.orders",
            description="Order data",
            dimensions=[
                CubeDimension(
                    name="id",
                    sql="${CUBE}.id",
                    type=DimensionType.NUMBER,
                    primary_key=True,
                ),
                CubeDimension(
                    name="status",
                    sql="${CUBE}.status",
                    type=DimensionType.STRING,
                ),
            ],
            measures=[
                CubeMeasure(name="count", type=MeasureType.COUNT),
                CubeMeasure(
                    name="total_amount",
                    sql="${CUBE}.amount",
                    type=MeasureType.SUM,
                ),
            ],
        )

        # Convert to dict and validate
        schema_dict = schema.model_dump(mode="json")

        try:
            jsonschema.validate(schema_dict, cube_schema_json_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"CubeSchema does not match JSON schema: {e.message}")


class TestSchemaVersionStability:
    """Tests for schema version compatibility."""

    def test_config_schema_has_version(self) -> None:
        """Config schema should have version information."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        schema_path = (
            project_root
            / "specs"
            / "005-consumption-layer"
            / "contracts"
            / "cube-config.schema.json"
        )
        if not schema_path.exists():
            pytest.fail(f"cube-config.schema.json not found at {schema_path}")

        schema = json.loads(schema_path.read_text())
        assert "$schema" in schema, "Schema should declare its JSON Schema version"

    def test_cube_schema_has_version(self) -> None:
        """Cube schema should have version information."""
        project_root = Path(__file__).parent.parent.parent.parent.parent
        schema_path = (
            project_root
            / "specs"
            / "005-consumption-layer"
            / "contracts"
            / "cube-schema.schema.json"
        )
        if not schema_path.exists():
            pytest.fail(f"cube-schema.schema.json not found at {schema_path}")

        schema = json.loads(schema_path.read_text())
        assert "$schema" in schema, "Schema should declare its JSON Schema version"
