"""Sync dbt models to Cube cubes.

This module parses dbt manifest.json and generates Cube schema YAML files
with dimensions, measures, and joins.

T026: Implement dbt manifest.json parser
T027: Implement dbt-to-Cube type mapping
T028: Implement dimension extraction from dbt columns
T029: Implement measure extraction from meta.cube.measures tags
T030: Implement join extraction from dbt refs
T031: Implement CubeSchema YAML generator
T032: Implement incremental sync logic
T033: Add manifest.json existence validation

Functional Requirements:
- FR-005: Parse dbt manifest.json
- FR-006: Extract dimensions from dbt columns
- FR-007: Extract measures from meta.cube.measures
- FR-008: Extract joins from dbt relationships
- FR-009: Generate Cube schema YAML files
- FR-010: Support incremental sync
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
import yaml

from floe_cube.models import (
    CubeDimension,
    CubeJoin,
    CubeMeasure,
    CubeSchema,
    DimensionType,
    JoinRelationship,
    MeasureType,
)

logger = structlog.get_logger(__name__)

# T027: dbt-to-Cube type mapping
DBT_TO_CUBE_TYPE: dict[str, DimensionType] = {
    # String types
    "text": DimensionType.STRING,
    "varchar": DimensionType.STRING,
    "char": DimensionType.STRING,
    "string": DimensionType.STRING,
    # Number types
    "integer": DimensionType.NUMBER,
    "int": DimensionType.NUMBER,
    "bigint": DimensionType.NUMBER,
    "smallint": DimensionType.NUMBER,
    "numeric": DimensionType.NUMBER,
    "decimal": DimensionType.NUMBER,
    "float": DimensionType.NUMBER,
    "double": DimensionType.NUMBER,
    "real": DimensionType.NUMBER,
    "number": DimensionType.NUMBER,
    # Time types
    "timestamp": DimensionType.TIME,
    "timestamptz": DimensionType.TIME,
    "datetime": DimensionType.TIME,
    "date": DimensionType.TIME,
    "time": DimensionType.TIME,
    # Boolean types
    "boolean": DimensionType.BOOLEAN,
    "bool": DimensionType.BOOLEAN,
    # Geo types
    "geography": DimensionType.GEO,
    "geometry": DimensionType.GEO,
    "point": DimensionType.GEO,
}

# Measure type mapping
DBT_TO_CUBE_MEASURE: dict[str, MeasureType] = {
    "count": MeasureType.COUNT,
    "count_distinct": MeasureType.COUNT_DISTINCT,
    "count_distinct_approx": MeasureType.COUNT_DISTINCT_APPROX,
    "sum": MeasureType.SUM,
    "avg": MeasureType.AVG,
    "min": MeasureType.MIN,
    "max": MeasureType.MAX,
    "number": MeasureType.NUMBER,
}

# Join relationship mapping
DBT_TO_CUBE_JOIN: dict[str, JoinRelationship] = {
    "one_to_one": JoinRelationship.ONE_TO_ONE,
    "one_to_many": JoinRelationship.ONE_TO_MANY,
    "many_to_one": JoinRelationship.MANY_TO_ONE,
}


def get_cube_dimension_type(dbt_type: str) -> DimensionType:
    """Map dbt data type to Cube dimension type.

    Args:
        dbt_type: The dbt column data type

    Returns:
        Corresponding Cube dimension type

    Example:
        >>> get_cube_dimension_type("integer")
        DimensionType.NUMBER
        >>> get_cube_dimension_type("timestamp")
        DimensionType.TIME
    """
    normalized = dbt_type.lower().strip()
    return DBT_TO_CUBE_TYPE.get(normalized, DimensionType.STRING)


def get_cube_measure_type(measure_type: str) -> MeasureType:
    """Map dbt measure type to Cube measure type.

    Args:
        measure_type: The measure type string

    Returns:
        Corresponding Cube measure type

    Example:
        >>> get_cube_measure_type("sum")
        MeasureType.SUM
    """
    normalized = measure_type.lower().strip()
    return DBT_TO_CUBE_MEASURE.get(normalized, MeasureType.NUMBER)


def get_cube_join_relationship(relationship: str) -> JoinRelationship:
    """Map dbt join relationship to Cube join relationship.

    Args:
        relationship: The relationship string

    Returns:
        Corresponding Cube join relationship

    Example:
        >>> get_cube_join_relationship("many_to_one")
        JoinRelationship.MANY_TO_ONE
    """
    normalized = relationship.lower().strip()
    return DBT_TO_CUBE_JOIN.get(normalized, JoinRelationship.ONE_TO_ONE)


class DbtManifestParser:
    """Parser for dbt manifest.json files (T026).

    Extracts model definitions, columns, and metadata from
    dbt's compiled manifest.json file.

    Attributes:
        manifest: The parsed manifest dictionary

    Example:
        >>> parser = DbtManifestParser.from_file(Path("target/manifest.json"))
        >>> models = parser.get_models()
        >>> len(models)
        5
    """

    def __init__(self, manifest: dict[str, Any]) -> None:
        """Initialize parser with manifest dictionary.

        Args:
            manifest: Parsed manifest.json dictionary
        """
        self.manifest = manifest
        self._log = logger.bind(
            node_count=len(manifest.get("nodes", {})),
        )

    @classmethod
    def from_file(cls, path: Path) -> DbtManifestParser:
        """Load manifest from file (T033).

        Args:
            path: Path to manifest.json

        Returns:
            DbtManifestParser instance

        Raises:
            FileNotFoundError: If manifest.json doesn't exist
        """
        if not path.exists():
            msg = f"dbt manifest not found: {path}"
            raise FileNotFoundError(msg)

        manifest = json.loads(path.read_text())
        return cls(manifest)

    def get_models(self) -> list[dict[str, Any]]:
        """Get all model definitions from manifest.

        Returns:
            List of model dictionaries

        Example:
            >>> parser = DbtManifestParser(manifest)
            >>> models = parser.get_models()
            >>> models[0]["name"]
            'customers'
        """
        models = []
        nodes = self.manifest.get("nodes", {})

        for node in nodes.values():
            if node.get("resource_type") == "model":
                models.append(node)

        self._log.info("models_extracted", count=len(models))
        return models


class ModelSynchronizer:
    """Synchronizes dbt models to Cube cubes.

    This class transforms dbt model definitions into CubeSchema
    objects, extracting dimensions, measures, and joins.

    Attributes:
        parser: DbtManifestParser instance

    Example:
        >>> parser = DbtManifestParser.from_file(manifest_path)
        >>> sync = ModelSynchronizer(parser)
        >>> cubes = sync.generate_cubes()
        >>> sync.write_schemas(output_dir)
    """

    def __init__(self, parser: DbtManifestParser) -> None:
        """Initialize synchronizer with manifest parser.

        Args:
            parser: DbtManifestParser instance
        """
        self.parser = parser
        self._log = logger.bind()
        self._cubes: list[CubeSchema] | None = None

    def generate_cubes(self) -> list[CubeSchema]:
        """Generate CubeSchema objects from dbt models.

        Returns:
            List of CubeSchema instances

        Example:
            >>> sync = ModelSynchronizer(parser)
            >>> cubes = sync.generate_cubes()
            >>> cubes[0].name
            'orders'
        """
        models = self.parser.get_models()
        cubes = []

        for model in models:
            cube = self._model_to_cube(model)
            cubes.append(cube)
            self._log.info("cube_generated", cube_name=cube.name)

        self._cubes = cubes
        return cubes

    def _model_to_cube(self, model: dict[str, Any]) -> CubeSchema:
        """Convert a dbt model to CubeSchema.

        Args:
            model: dbt model dictionary

        Returns:
            CubeSchema instance
        """
        name = model["name"]

        # T028: Extract dimensions from columns
        dimensions = self._extract_dimensions(model)

        # T029: Extract measures from meta.cube.measures
        measures = self._extract_measures(model)

        # T030: Extract joins from meta.cube.joins
        joins = self._extract_joins(model)

        # Build sql_table reference
        schema = model.get("schema", "public")
        database = model.get("database")
        sql_table = f"{database}.{schema}.{name}" if database else f"{schema}.{name}"

        return CubeSchema(
            name=name,
            sql_table=sql_table,
            description=model.get("description"),
            dimensions=dimensions,
            measures=measures,
            joins=joins,
        )

    def _extract_dimensions(self, model: dict[str, Any]) -> list[CubeDimension]:
        """Extract dimensions from dbt columns (T028).

        Args:
            model: dbt model dictionary

        Returns:
            List of CubeDimension instances
        """
        dimensions = []
        columns = model.get("columns", {})
        found_primary_key = False

        for col_name, col_info in columns.items():
            data_type = col_info.get("data_type", "text")
            dim_type = get_cube_dimension_type(data_type)

            # First 'id' column of integer type becomes primary key
            is_pk = False
            if not found_primary_key and col_name == "id" and dim_type == DimensionType.NUMBER:
                is_pk = True
                found_primary_key = True

            dimension = CubeDimension(
                name=col_name,
                sql=f"${{CUBE}}.{col_name}",
                type=dim_type,
                primary_key=is_pk,
                description=col_info.get("description"),
            )
            dimensions.append(dimension)

        return dimensions

    def _extract_measures(self, model: dict[str, Any]) -> list[CubeMeasure]:
        """Extract measures from meta.cube.measures (T029).

        Args:
            model: dbt model dictionary

        Returns:
            List of CubeMeasure instances
        """
        measures = []
        cube_meta = model.get("meta", {}).get("cube", {})
        measure_defs = cube_meta.get("measures", [])

        if not measure_defs:
            # Default: add a count measure
            measures.append(
                CubeMeasure(name="count", type=MeasureType.COUNT)
            )
        else:
            for measure_def in measure_defs:
                measure_type = get_cube_measure_type(measure_def.get("type", "count"))

                measure = CubeMeasure(
                    name=measure_def["name"],
                    type=measure_type,
                    sql=measure_def.get("sql"),
                    description=measure_def.get("description"),
                )
                measures.append(measure)

        return measures

    def _extract_joins(self, model: dict[str, Any]) -> list[CubeJoin]:
        """Extract joins from meta.cube.joins (T030).

        Args:
            model: dbt model dictionary

        Returns:
            List of CubeJoin instances
        """
        joins = []
        cube_meta = model.get("meta", {}).get("cube", {})
        join_defs = cube_meta.get("joins", [])

        for join_def in join_defs:
            relationship = get_cube_join_relationship(
                join_def.get("relationship", "one_to_one")
            )

            join = CubeJoin(
                name=join_def["name"],
                relationship=relationship,
                sql=join_def["sql"],
            )
            joins.append(join)

        return joins

    def write_schemas(self, output_dir: Path) -> list[Path]:
        """Write Cube schema YAML files (T031).

        Args:
            output_dir: Directory to write YAML files

        Returns:
            List of paths to written files

        Example:
            >>> sync.write_schemas(Path(".floe/cube/schema"))
            [PosixPath('.floe/cube/schema/orders.yaml'), ...]
        """
        if self._cubes is None:
            self._cubes = self.generate_cubes()

        output_dir.mkdir(parents=True, exist_ok=True)
        written_files = []

        for cube in self._cubes:
            yaml_content = self._cube_to_yaml(cube)
            file_path = output_dir / f"{cube.name}.yaml"
            file_path.write_text(yaml_content)
            written_files.append(file_path)
            self._log.info("schema_written", path=str(file_path))

        return written_files

    def _cube_to_yaml(self, cube: CubeSchema) -> str:
        """Convert CubeSchema to YAML string.

        Args:
            cube: CubeSchema instance

        Returns:
            YAML string representation
        """
        cube_dict = {
            "cubes": [
                {
                    "name": cube.name,
                    "sql_table": cube.sql_table,
                    "dimensions": [
                        {
                            "name": d.name,
                            "sql": d.sql,
                            "type": d.type.value,
                            **({"primary_key": True} if d.primary_key else {}),
                            **({"description": d.description} if d.description else {}),
                        }
                        for d in cube.dimensions
                    ],
                    "measures": [
                        {
                            "name": m.name,
                            "type": m.type.value,
                            **({"sql": m.sql} if m.sql else {}),
                            **({"description": m.description} if m.description else {}),
                        }
                        for m in cube.measures
                    ],
                }
            ]
        }

        # Add joins if present
        if cube.joins:
            cube_dict["cubes"][0]["joins"] = [
                {
                    "name": j.name,
                    "relationship": j.relationship.value,
                    "sql": j.sql,
                }
                for j in cube.joins
            ]

        # Add description if present
        if cube.description:
            cube_dict["cubes"][0]["description"] = cube.description

        return yaml.dump(cube_dict, default_flow_style=False, sort_keys=False)


# Alias for backwards compatibility
ModelSync = ModelSynchronizer
