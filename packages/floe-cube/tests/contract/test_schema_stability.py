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
        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent
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
                Path(__file__).parent.parent.parent.parent.parent.parent
                / "specs"
                / "005-consumption-layer"
                / "contracts"
                / "cube-config.schema.json"
            )
        if not schema_path.exists():
            pytest.skip("cube-config.schema.json not found")

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

    def test_generated_config_validates_against_schema(
        self,
        cube_config_schema: dict[str, Any],
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Generated config should validate against cube-config.schema.json."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        # Validate against JSON schema
        try:
            jsonschema.validate(config, cube_config_schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Generated config does not match schema: {e.message}")

    def test_all_database_types_produce_valid_configs(
        self,
        cube_config_schema: dict[str, Any],
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """All supported database types should produce schema-valid configs."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        from floe_cube.config import CubeConfigGenerator

        database_types = [
            "postgres",
            "snowflake",
            "bigquery",
            "databricks",
            "trino",
            "duckdb",
        ]

        for db_type in database_types:
            minimal_consumption_config["database_type"] = db_type
            generator = CubeConfigGenerator(minimal_consumption_config)
            config = generator.generate()

            try:
                jsonschema.validate(config, cube_config_schema)
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
        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "specs"
            / "005-consumption-layer"
            / "contracts"
            / "cube-schema.schema.json"
        )
        if not schema_path.exists():
            pytest.skip("cube-schema.schema.json not found")

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
        # This test ensures we track schema versions for compatibility
        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "specs"
            / "005-consumption-layer"
            / "contracts"
            / "cube-config.schema.json"
        )
        if not schema_path.exists():
            pytest.skip("cube-config.schema.json not found")

        schema = json.loads(schema_path.read_text())
        assert "$schema" in schema, "Schema should declare its JSON Schema version"

    def test_cube_schema_has_version(self) -> None:
        """Cube schema should have version information."""
        schema_path = (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / "specs"
            / "005-consumption-layer"
            / "contracts"
            / "cube-schema.schema.json"
        )
        if not schema_path.exists():
            pytest.skip("cube-schema.schema.json not found")

        schema = json.loads(schema_path.read_text())
        assert "$schema" in schema, "Schema should declare its JSON Schema version"
