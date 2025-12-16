"""Data models for floe-dagster.

T040: [P] [US1] Create DbtModelMetadata model
T041: [P] [US1] Create ColumnMetadata model
T042: [P] [US1] Create AssetMaterializationResult model
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnMetadata(BaseModel):
    """Column metadata from dbt manifest.

    Captures column information including data type, description,
    and floe-specific metadata from the meta.floe namespace.

    Attributes:
        name: Column name.
        data_type: SQL data type (if available).
        description: Column description from dbt.
        floe_meta: Floe-specific metadata from meta.floe namespace.

    Example:
        >>> col = ColumnMetadata(
        ...     name="email",
        ...     data_type="varchar",
        ...     description="Customer email",
        ...     floe_meta={"classification": "pii", "pii_type": "email"}
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    data_type: str | None = None
    description: str | None = None
    floe_meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Floe-specific metadata from meta.floe namespace",
    )


class DbtModelMetadata(BaseModel):
    """Metadata extracted from dbt manifest.json node.

    Represents all metadata needed to create a Dagster asset from
    a dbt model, including dependencies, columns, and governance info.

    Attributes:
        unique_id: dbt unique identifier (e.g., model.project.name).
        name: Model name.
        alias: Table/view alias.
        database: Target database.
        schema_name: Target schema (uses alias to avoid Python keyword).
        description: Model description.
        tags: dbt tags.
        owner: Model owner from meta.floe namespace.
        depends_on: Upstream model unique_ids.
        columns: Column metadata dictionary.
        materialization: Materialization type (view, table, incremental, ephemeral).

    Example:
        >>> metadata = DbtModelMetadata.from_manifest_node(node_dict)
        >>> metadata.name
        'customers'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    unique_id: str = Field(description="dbt unique identifier (model.project.name)")
    name: str = Field(description="Model name")
    alias: str = Field(description="Table/view alias")
    database: str = Field(default="", description="Target database")
    schema_name: str = Field(default="", description="Target schema")
    description: str = Field(default="", description="Model description")
    tags: list[str] = Field(default_factory=list, description="dbt tags")
    owner: str | None = Field(default=None, description="Model owner from meta.floe")
    depends_on: list[str] = Field(
        default_factory=list,
        description="Upstream model unique_ids",
    )
    columns: dict[str, ColumnMetadata] = Field(
        default_factory=dict,
        description="Column metadata",
    )
    materialization: str = Field(
        default="view",
        description="Materialization type (view, table, incremental, ephemeral)",
    )

    @classmethod
    def from_manifest_node(cls, node: dict[str, Any]) -> DbtModelMetadata:
        """Create from dbt manifest node.

        Extracts all relevant metadata from a dbt manifest.json node,
        including floe-specific metadata from the meta.floe namespace.

        Args:
            node: dbt manifest node dictionary.

        Returns:
            DbtModelMetadata instance.
        """
        # Extract floe-specific metadata from meta.floe namespace
        floe_meta = node.get("meta", {}).get("floe", {})

        # Build column metadata
        columns = {
            col_name: ColumnMetadata(
                name=col_name,
                data_type=col_info.get("data_type"),
                description=col_info.get("description"),
                floe_meta=col_info.get("meta", {}).get("floe", {}),
            )
            for col_name, col_info in node.get("columns", {}).items()
        }

        return cls(
            unique_id=node["unique_id"],
            name=node["name"],
            alias=node.get("alias") or node["name"],
            database=node.get("database", ""),
            schema_name=node.get("schema", ""),
            description=node.get("description", ""),
            tags=node.get("tags", []),
            owner=floe_meta.get("owner"),
            depends_on=node.get("depends_on", {}).get("nodes", []),
            columns=columns,
            materialization=node.get("config", {}).get("materialized", "view"),
        )


class MaterializationStatus(str, Enum):
    """dbt model execution status."""

    SUCCESS = "success"
    ERROR = "error"
    FAIL = "fail"
    SKIPPED = "skipped"


class AssetMaterializationResult(BaseModel):
    """Result of a dbt asset materialization.

    Captures the outcome of executing a dbt model, including
    timing, row counts, and any error information.

    Attributes:
        model_unique_id: dbt model unique identifier.
        status: Execution status (success, error, fail, skipped).
        execution_time: Execution time in seconds.
        rows_affected: Number of rows affected (if available).
        error_message: Error message (if failed).

    Example:
        >>> result = AssetMaterializationResult(
        ...     model_unique_id="model.proj.customers",
        ...     status="success",
        ...     execution_time=1.5,
        ...     rows_affected=1000
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    model_unique_id: str = Field(description="dbt model unique identifier")
    status: str = Field(description="Execution status (success, error, fail, skipped)")
    execution_time: float = Field(description="Execution time in seconds")
    rows_affected: int | None = Field(
        default=None,
        description="Number of rows affected",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if failed",
    )
