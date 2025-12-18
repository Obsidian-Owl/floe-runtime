"""Unit tests for floe_cube.model_sync dbt-to-Cube synchronization.

T021: [US2] Unit test - model_sync extracts dimensions from dbt columns
T022: [US2] Unit test - model_sync extracts measures from meta.cube.measures tags
T023: [US2] Unit test - model_sync creates joins from dbt relationships
T024: [US2] Unit test - model_sync handles incremental updates

Tests FR-005 through FR-010, FR-028:
- FR-005: Parse dbt manifest.json
- FR-006: Extract dimensions from dbt columns
- FR-007: Extract measures from meta.cube.measures
- FR-008: Extract joins from dbt relationships
- FR-009: Generate Cube schema YAML files
- FR-010: Support incremental sync
- FR-028: Watch manifest.json for changes
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


class TestDbtManifestParser:
    """Tests for dbt manifest.json parsing."""

    @pytest.fixture
    def sample_manifest(self) -> dict[str, Any]:
        """Sample dbt manifest.json for testing."""
        return {
            "nodes": {
                "model.my_project.customers": {
                    "name": "customers",
                    "resource_type": "model",
                    "schema": "public",
                    "database": "analytics",
                    "columns": {
                        "id": {
                            "name": "id",
                            "description": "Customer ID",
                            "data_type": "integer",
                        },
                        "email": {
                            "name": "email",
                            "description": "Customer email",
                            "data_type": "text",
                        },
                        "created_at": {
                            "name": "created_at",
                            "description": "Creation timestamp",
                            "data_type": "timestamp",
                        },
                        "is_active": {
                            "name": "is_active",
                            "description": "Active status",
                            "data_type": "boolean",
                        },
                    },
                },
                "model.my_project.orders": {
                    "name": "orders",
                    "resource_type": "model",
                    "schema": "public",
                    "database": "analytics",
                    "columns": {
                        "id": {
                            "name": "id",
                            "description": "Order ID",
                            "data_type": "integer",
                        },
                        "customer_id": {
                            "name": "customer_id",
                            "description": "Customer FK",
                            "data_type": "integer",
                        },
                        "amount": {
                            "name": "amount",
                            "description": "Order amount",
                            "data_type": "numeric",
                        },
                        "status": {
                            "name": "status",
                            "description": "Order status",
                            "data_type": "text",
                        },
                    },
                    "meta": {
                        "cube": {
                            "measures": [
                                {"name": "count", "type": "count"},
                                {
                                    "name": "total_amount",
                                    "type": "sum",
                                    "sql": "${CUBE}.amount",
                                },
                                {
                                    "name": "avg_amount",
                                    "type": "avg",
                                    "sql": "${CUBE}.amount",
                                },
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
            "sources": {},
        }

    def test_parse_manifest_extracts_models(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """Parser should extract model definitions from manifest."""
        from floe_cube.model_sync import DbtManifestParser

        parser = DbtManifestParser(sample_manifest)
        models = parser.get_models()

        assert len(models) == 2
        assert "customers" in [m["name"] for m in models]
        assert "orders" in [m["name"] for m in models]

    def test_parse_manifest_from_file(self, tmp_path: Path) -> None:
        """Parser should load manifest from file."""
        from floe_cube.model_sync import DbtManifestParser

        manifest = {
            "nodes": {
                "model.test.users": {
                    "name": "users",
                    "resource_type": "model",
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
                }
            },
            "sources": {},
        }

        manifest_path = tmp_path / "target" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(manifest))

        parser = DbtManifestParser.from_file(manifest_path)
        models = parser.get_models()

        assert len(models) == 1
        assert models[0]["name"] == "users"

    def test_parse_manifest_missing_file_raises(self, tmp_path: Path) -> None:
        """Parser should raise FileNotFoundError for missing manifest."""
        from floe_cube.model_sync import DbtManifestParser

        with pytest.raises(FileNotFoundError):
            DbtManifestParser.from_file(tmp_path / "nonexistent" / "manifest.json")


class TestDimensionExtraction:
    """T021: Tests for extracting dimensions from dbt columns."""

    @pytest.fixture
    def sample_manifest(self) -> dict[str, Any]:
        """Manifest with various column types."""
        return {
            "nodes": {
                "model.test.products": {
                    "name": "products",
                    "resource_type": "model",
                    "columns": {
                        "id": {"name": "id", "data_type": "integer"},
                        "name": {"name": "name", "data_type": "text"},
                        "price": {"name": "price", "data_type": "numeric"},
                        "created_at": {"name": "created_at", "data_type": "timestamp"},
                        "is_available": {"name": "is_available", "data_type": "boolean"},
                        "location": {"name": "location", "data_type": "geography"},
                    },
                }
            },
            "sources": {},
        }

    def test_extracts_dimensions_from_columns(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """Should extract dimensions from all dbt columns."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        assert len(cubes) == 1
        products_cube = cubes[0]
        assert len(products_cube.dimensions) == 6

    def test_dimension_names_match_columns(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """Dimension names should match dbt column names."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        dim_names = {d.name for d in cubes[0].dimensions}
        expected = {"id", "name", "price", "created_at", "is_available", "location"}
        assert dim_names == expected

    def test_type_mapping_text_to_string(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """dbt 'text' type should map to Cube 'string' dimension type."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import DimensionType

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        name_dim = next(d for d in cubes[0].dimensions if d.name == "name")
        assert name_dim.type == DimensionType.STRING

    def test_type_mapping_integer_to_number(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """dbt 'integer' type should map to Cube 'number' dimension type."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import DimensionType

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        id_dim = next(d for d in cubes[0].dimensions if d.name == "id")
        assert id_dim.type == DimensionType.NUMBER

    def test_type_mapping_numeric_to_number(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """dbt 'numeric' type should map to Cube 'number' dimension type."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import DimensionType

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        price_dim = next(d for d in cubes[0].dimensions if d.name == "price")
        assert price_dim.type == DimensionType.NUMBER

    def test_type_mapping_timestamp_to_time(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """dbt 'timestamp' type should map to Cube 'time' dimension type."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import DimensionType

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        created_dim = next(d for d in cubes[0].dimensions if d.name == "created_at")
        assert created_dim.type == DimensionType.TIME

    def test_type_mapping_boolean_to_boolean(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """dbt 'boolean' type should map to Cube 'boolean' dimension type."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import DimensionType

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        available_dim = next(d for d in cubes[0].dimensions if d.name == "is_available")
        assert available_dim.type == DimensionType.BOOLEAN

    def test_type_mapping_geography_to_geo(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """dbt 'geography' type should map to Cube 'geo' dimension type."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import DimensionType

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        location_dim = next(d for d in cubes[0].dimensions if d.name == "location")
        assert location_dim.type == DimensionType.GEO

    def test_first_integer_column_is_primary_key(
        self,
        sample_manifest: dict[str, Any],
    ) -> None:
        """First integer column named 'id' should be marked as primary key."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        id_dim = next(d for d in cubes[0].dimensions if d.name == "id")
        assert id_dim.primary_key is True


class TestMeasureExtraction:
    """T022: Tests for extracting measures from meta.cube.measures tags."""

    @pytest.fixture
    def manifest_with_measures(self) -> dict[str, Any]:
        """Manifest with cube measures in meta tags."""
        return {
            "nodes": {
                "model.test.sales": {
                    "name": "sales",
                    "resource_type": "model",
                    "columns": {
                        "id": {"name": "id", "data_type": "integer"},
                        "amount": {"name": "amount", "data_type": "numeric"},
                        "quantity": {"name": "quantity", "data_type": "integer"},
                    },
                    "meta": {
                        "cube": {
                            "measures": [
                                {"name": "count", "type": "count"},
                                {
                                    "name": "total_amount",
                                    "type": "sum",
                                    "sql": "${CUBE}.amount",
                                },
                                {
                                    "name": "avg_amount",
                                    "type": "avg",
                                    "sql": "${CUBE}.amount",
                                },
                                {
                                    "name": "total_quantity",
                                    "type": "sum",
                                    "sql": "${CUBE}.quantity",
                                },
                            ]
                        }
                    },
                }
            },
            "sources": {},
        }

    def test_extracts_measures_from_meta(
        self,
        manifest_with_measures: dict[str, Any],
    ) -> None:
        """Should extract measures from meta.cube.measures."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(manifest_with_measures)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        assert len(cubes) == 1
        assert len(cubes[0].measures) == 4

    def test_measure_count_type(
        self,
        manifest_with_measures: dict[str, Any],
    ) -> None:
        """COUNT measure should be created correctly."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import MeasureType

        parser = DbtManifestParser(manifest_with_measures)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        count_measure = next(m for m in cubes[0].measures if m.name == "count")
        assert count_measure.type == MeasureType.COUNT
        assert count_measure.sql is None  # COUNT doesn't need sql

    def test_measure_sum_type_with_sql(
        self,
        manifest_with_measures: dict[str, Any],
    ) -> None:
        """SUM measure should have correct type and sql."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import MeasureType

        parser = DbtManifestParser(manifest_with_measures)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        total_measure = next(m for m in cubes[0].measures if m.name == "total_amount")
        assert total_measure.type == MeasureType.SUM
        assert total_measure.sql == "${CUBE}.amount"

    def test_measure_avg_type(
        self,
        manifest_with_measures: dict[str, Any],
    ) -> None:
        """AVG measure should be created correctly."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import MeasureType

        parser = DbtManifestParser(manifest_with_measures)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        avg_measure = next(m for m in cubes[0].measures if m.name == "avg_amount")
        assert avg_measure.type == MeasureType.AVG

    def test_model_without_measures_gets_default_count(self) -> None:
        """Model without meta.cube.measures should get default count measure."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import MeasureType

        manifest = {
            "nodes": {
                "model.test.events": {
                    "name": "events",
                    "resource_type": "model",
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
                }
            },
            "sources": {},
        }

        parser = DbtManifestParser(manifest)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        # Should have at least a count measure by default
        assert len(cubes[0].measures) >= 1
        count_measure = cubes[0].measures[0]
        assert count_measure.type == MeasureType.COUNT


class TestJoinExtraction:
    """T023: Tests for extracting joins from dbt relationships."""

    @pytest.fixture
    def manifest_with_joins(self) -> dict[str, Any]:
        """Manifest with cube joins in meta tags."""
        return {
            "nodes": {
                "model.test.customers": {
                    "name": "customers",
                    "resource_type": "model",
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
                },
                "model.test.orders": {
                    "name": "orders",
                    "resource_type": "model",
                    "columns": {
                        "id": {"name": "id", "data_type": "integer"},
                        "customer_id": {"name": "customer_id", "data_type": "integer"},
                    },
                    "meta": {
                        "cube": {
                            "joins": [
                                {
                                    "name": "customers",
                                    "relationship": "many_to_one",
                                    "sql": "${CUBE}.customer_id = ${customers}.id",
                                }
                            ]
                        }
                    },
                },
            },
            "sources": {},
        }

    def test_extracts_joins_from_meta(
        self,
        manifest_with_joins: dict[str, Any],
    ) -> None:
        """Should extract joins from meta.cube.joins."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(manifest_with_joins)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        orders_cube = next(c for c in cubes if c.name == "orders")
        assert len(orders_cube.joins) == 1

    def test_join_relationship_type(
        self,
        manifest_with_joins: dict[str, Any],
    ) -> None:
        """Join relationship should map correctly."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
        from floe_cube.models import JoinRelationship

        parser = DbtManifestParser(manifest_with_joins)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        orders_cube = next(c for c in cubes if c.name == "orders")
        join = orders_cube.joins[0]
        assert join.relationship == JoinRelationship.MANY_TO_ONE

    def test_join_sql_expression(
        self,
        manifest_with_joins: dict[str, Any],
    ) -> None:
        """Join SQL should be preserved."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(manifest_with_joins)
        sync = ModelSynchronizer(parser)
        cubes = sync.generate_cubes()

        orders_cube = next(c for c in cubes if c.name == "orders")
        join = orders_cube.joins[0]
        assert "${customers}.id" in join.sql
        assert "${CUBE}.customer_id" in join.sql


class TestIncrementalSync:
    """T024: Tests for incremental sync handling."""

    @pytest.fixture
    def initial_manifest(self) -> dict[str, Any]:
        """Initial manifest state."""
        return {
            "nodes": {
                "model.test.users": {
                    "name": "users",
                    "resource_type": "model",
                    "columns": {
                        "id": {"name": "id", "data_type": "integer"},
                        "name": {"name": "name", "data_type": "text"},
                    },
                }
            },
            "sources": {},
        }

    @pytest.fixture
    def updated_manifest(self) -> dict[str, Any]:
        """Updated manifest with new column."""
        return {
            "nodes": {
                "model.test.users": {
                    "name": "users",
                    "resource_type": "model",
                    "columns": {
                        "id": {"name": "id", "data_type": "integer"},
                        "name": {"name": "name", "data_type": "text"},
                        "email": {"name": "email", "data_type": "text"},  # new column
                    },
                }
            },
            "sources": {},
        }

    def test_sync_detects_new_columns(
        self,
        initial_manifest: dict[str, Any],
        updated_manifest: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Incremental sync should detect new columns."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        # Initial sync
        parser1 = DbtManifestParser(initial_manifest)
        sync1 = ModelSynchronizer(parser1)
        cubes1 = sync1.generate_cubes()
        assert len(cubes1[0].dimensions) == 2

        # Updated sync
        parser2 = DbtManifestParser(updated_manifest)
        sync2 = ModelSynchronizer(parser2)
        cubes2 = sync2.generate_cubes()
        assert len(cubes2[0].dimensions) == 3

        # New dimension should be present
        dim_names = {d.name for d in cubes2[0].dimensions}
        assert "email" in dim_names

    def test_sync_does_not_duplicate_cubes(
        self,
        initial_manifest: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Repeated sync should not create duplicate cubes."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(initial_manifest)
        sync = ModelSynchronizer(parser)

        # Generate multiple times
        cubes1 = sync.generate_cubes()
        cubes2 = sync.generate_cubes()

        assert len(cubes1) == len(cubes2) == 1
        assert cubes1[0].name == cubes2[0].name

    def test_sync_handles_removed_models(self, tmp_path: Path) -> None:
        """Sync should handle removed models gracefully."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        # Manifest with two models
        manifest1 = {
            "nodes": {
                "model.test.users": {
                    "name": "users",
                    "resource_type": "model",
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
                },
                "model.test.posts": {
                    "name": "posts",
                    "resource_type": "model",
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
                },
            },
            "sources": {},
        }

        # Manifest with one model removed
        manifest2 = {
            "nodes": {
                "model.test.users": {
                    "name": "users",
                    "resource_type": "model",
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
                }
            },
            "sources": {},
        }

        parser1 = DbtManifestParser(manifest1)
        sync1 = ModelSynchronizer(parser1)
        cubes1 = sync1.generate_cubes()
        assert len(cubes1) == 2

        parser2 = DbtManifestParser(manifest2)
        sync2 = ModelSynchronizer(parser2)
        cubes2 = sync2.generate_cubes()
        assert len(cubes2) == 1


class TestCubeSchemaYamlGeneration:
    """Tests for generating Cube schema YAML files."""

    @pytest.fixture
    def sample_manifest(self) -> dict[str, Any]:
        """Sample manifest for YAML generation."""
        return {
            "nodes": {
                "model.test.orders": {
                    "name": "orders",
                    "resource_type": "model",
                    "columns": {
                        "id": {"name": "id", "data_type": "integer"},
                        "amount": {"name": "amount", "data_type": "numeric"},
                    },
                    "meta": {
                        "cube": {
                            "measures": [
                                {"name": "count", "type": "count"},
                                {
                                    "name": "total_amount",
                                    "type": "sum",
                                    "sql": "${CUBE}.amount",
                                },
                            ]
                        }
                    },
                }
            },
            "sources": {},
        }

    def test_write_yaml_creates_file(
        self,
        sample_manifest: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Should write YAML file to output directory."""
        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        output_dir = tmp_path / ".floe" / "cube" / "schema"

        sync.write_schemas(output_dir)

        assert (output_dir / "orders.yaml").exists()

    def test_yaml_content_is_valid(
        self,
        sample_manifest: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Generated YAML should be valid and parseable."""
        import yaml

        from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer

        parser = DbtManifestParser(sample_manifest)
        sync = ModelSynchronizer(parser)
        output_dir = tmp_path / ".floe" / "cube" / "schema"

        sync.write_schemas(output_dir)

        yaml_content = (output_dir / "orders.yaml").read_text()
        parsed = yaml.safe_load(yaml_content)

        assert "cubes" in parsed
        assert len(parsed["cubes"]) == 1
        assert parsed["cubes"][0]["name"] == "orders"


class TestPreAggregationYamlGeneration:
    """T090: Unit test pre-aggregation config generates correct YAML."""

    def test_pre_aggregation_generates_yaml(self) -> None:
        """Pre-aggregation should be included in generated YAML."""
        import yaml

        from floe_cube.model_sync import ModelSynchronizer
        from floe_cube.models import (
            CubeDimension,
            CubeMeasure,
            CubePreAggregation,
            CubeSchema,
            DimensionType,
            MeasureType,
            TimeGranularity,
        )

        # Create cube with pre-aggregation
        cube = CubeSchema(
            name="orders",
            sql_table="public.orders",
            dimensions=[
                CubeDimension(
                    name="created_at", sql="${CUBE}.created_at", type=DimensionType.TIME
                ),
                CubeDimension(name="status", sql="${CUBE}.status", type=DimensionType.STRING),
            ],
            measures=[
                CubeMeasure(name="count", type=MeasureType.COUNT),
                CubeMeasure(
                    name="total_amount", type=MeasureType.SUM, sql="${CUBE}.amount"
                ),
            ],
            pre_aggregations=[
                CubePreAggregation(
                    name="daily_orders",
                    measures=["count", "total_amount"],
                    dimensions=["status"],
                    time_dimension="created_at",
                    granularity=TimeGranularity.DAY,
                    refresh_every="0 * * * *",
                    external=True,
                )
            ],
        )

        # Use internal _cube_to_yaml method
        sync = ModelSynchronizer.__new__(ModelSynchronizer)
        yaml_content = sync._cube_to_yaml(cube)
        parsed = yaml.safe_load(yaml_content)

        # Verify pre_aggregations is in YAML
        assert "pre_aggregations" in parsed["cubes"][0]
        pre_aggs = parsed["cubes"][0]["pre_aggregations"]
        assert len(pre_aggs) == 1
        assert pre_aggs[0]["name"] == "daily_orders"

    def test_pre_aggregation_measures_in_yaml(self) -> None:
        """Pre-aggregation measures should be in YAML."""
        import yaml

        from floe_cube.model_sync import ModelSynchronizer
        from floe_cube.models import (
            CubeMeasure,
            CubePreAggregation,
            CubeSchema,
            MeasureType,
        )

        cube = CubeSchema(
            name="orders",
            sql_table="public.orders",
            measures=[
                CubeMeasure(name="count", type=MeasureType.COUNT),
                CubeMeasure(name="total", type=MeasureType.SUM, sql="${CUBE}.amount"),
            ],
            pre_aggregations=[
                CubePreAggregation(
                    name="main",
                    measures=["count", "total"],
                )
            ],
        )

        sync = ModelSynchronizer.__new__(ModelSynchronizer)
        yaml_content = sync._cube_to_yaml(cube)
        parsed = yaml.safe_load(yaml_content)

        pre_agg = parsed["cubes"][0]["pre_aggregations"][0]
        assert pre_agg["measures"] == ["count", "total"]

    def test_pre_aggregation_dimensions_in_yaml(self) -> None:
        """Pre-aggregation dimensions should be in YAML."""
        import yaml

        from floe_cube.model_sync import ModelSynchronizer
        from floe_cube.models import (
            CubeDimension,
            CubePreAggregation,
            CubeSchema,
            DimensionType,
        )

        cube = CubeSchema(
            name="orders",
            sql_table="public.orders",
            dimensions=[
                CubeDimension(name="status", sql="${CUBE}.status", type=DimensionType.STRING),
                CubeDimension(name="region", sql="${CUBE}.region", type=DimensionType.STRING),
            ],
            pre_aggregations=[
                CubePreAggregation(
                    name="by_status_region",
                    dimensions=["status", "region"],
                )
            ],
        )

        sync = ModelSynchronizer.__new__(ModelSynchronizer)
        yaml_content = sync._cube_to_yaml(cube)
        parsed = yaml.safe_load(yaml_content)

        pre_agg = parsed["cubes"][0]["pre_aggregations"][0]
        assert pre_agg["dimensions"] == ["status", "region"]

    def test_pre_aggregation_granularity_in_yaml(self) -> None:
        """Pre-aggregation granularity should be in YAML."""
        import yaml

        from floe_cube.model_sync import ModelSynchronizer
        from floe_cube.models import (
            CubeDimension,
            CubePreAggregation,
            CubeSchema,
            DimensionType,
            TimeGranularity,
        )

        cube = CubeSchema(
            name="orders",
            sql_table="public.orders",
            dimensions=[
                CubeDimension(
                    name="created_at", sql="${CUBE}.created_at", type=DimensionType.TIME
                ),
            ],
            pre_aggregations=[
                CubePreAggregation(
                    name="hourly",
                    time_dimension="created_at",
                    granularity=TimeGranularity.HOUR,
                )
            ],
        )

        sync = ModelSynchronizer.__new__(ModelSynchronizer)
        yaml_content = sync._cube_to_yaml(cube)
        parsed = yaml.safe_load(yaml_content)

        pre_agg = parsed["cubes"][0]["pre_aggregations"][0]
        assert pre_agg["time_dimension"] == "created_at"
        assert pre_agg["granularity"] == "hour"

    def test_pre_aggregation_refresh_key_in_yaml(self) -> None:
        """Pre-aggregation refresh_key should contain cron expression."""
        import yaml

        from floe_cube.model_sync import ModelSynchronizer
        from floe_cube.models import CubePreAggregation, CubeSchema

        cube = CubeSchema(
            name="orders",
            sql_table="public.orders",
            pre_aggregations=[
                CubePreAggregation(
                    name="hourly",
                    refresh_every="0 * * * *",
                )
            ],
        )

        sync = ModelSynchronizer.__new__(ModelSynchronizer)
        yaml_content = sync._cube_to_yaml(cube)
        parsed = yaml.safe_load(yaml_content)

        pre_agg = parsed["cubes"][0]["pre_aggregations"][0]
        assert "refresh_key" in pre_agg
        assert pre_agg["refresh_key"]["every"] == "0 * * * *"

    def test_pre_aggregation_external_flag_in_yaml(self) -> None:
        """Pre-aggregation external flag should be in YAML."""
        import yaml

        from floe_cube.model_sync import ModelSynchronizer
        from floe_cube.models import CubePreAggregation, CubeSchema

        cube = CubeSchema(
            name="orders",
            sql_table="public.orders",
            pre_aggregations=[
                CubePreAggregation(name="external_agg", external=True),
                CubePreAggregation(name="internal_agg", external=False),
            ],
        )

        sync = ModelSynchronizer.__new__(ModelSynchronizer)
        yaml_content = sync._cube_to_yaml(cube)
        parsed = yaml.safe_load(yaml_content)

        pre_aggs = parsed["cubes"][0]["pre_aggregations"]
        external_agg = next(p for p in pre_aggs if p["name"] == "external_agg")
        internal_agg = next(p for p in pre_aggs if p["name"] == "internal_agg")

        assert external_agg["external"] is True
        assert internal_agg["external"] is False

    def test_cube_without_pre_aggregations_no_section(self) -> None:
        """Cube without pre-aggregations should not have pre_aggregations section."""
        import yaml

        from floe_cube.model_sync import ModelSynchronizer
        from floe_cube.models import CubeMeasure, CubeSchema, MeasureType

        cube = CubeSchema(
            name="orders",
            sql_table="public.orders",
            measures=[CubeMeasure(name="count", type=MeasureType.COUNT)],
        )

        sync = ModelSynchronizer.__new__(ModelSynchronizer)
        yaml_content = sync._cube_to_yaml(cube)
        parsed = yaml.safe_load(yaml_content)

        assert "pre_aggregations" not in parsed["cubes"][0]
