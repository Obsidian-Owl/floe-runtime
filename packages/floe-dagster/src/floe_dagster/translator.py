"""Custom Dagster dbt translator for floe-runtime.

T043: [US1] Implement FloeTranslator (extends DagsterDbtTranslator)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from dagster import AssetKey, MetadataValue
from dagster_dbt import DagsterDbtTranslator


class FloeTranslator(DagsterDbtTranslator):
    """Custom translator for dbt assets with floe-specific metadata.

    Extends DagsterDbtTranslator to include floe-specific metadata
    from the meta.floe namespace in dbt models.

    Features:
        - Extracts owner from meta.floe.owner
        - Includes column classifications in metadata
        - Maps dbt tags to Dagster groups
        - Includes governance metadata for lineage

    Example:
        >>> translator = FloeTranslator()
        >>> asset_key = translator.get_asset_key(dbt_node)
        >>> metadata = translator.get_metadata(dbt_node)
    """

    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        """Get asset key from dbt resource properties.

        Creates a hierarchical asset key based on database, schema, and alias.

        Args:
            dbt_resource_props: dbt manifest node properties.

        Returns:
            AssetKey with hierarchical path.
        """
        database = dbt_resource_props.get("database", "")
        schema = dbt_resource_props.get("schema", "")
        alias = dbt_resource_props.get("alias") or dbt_resource_props.get("name", "")

        # Create hierarchical key: database/schema/table
        key_parts = [p for p in [database, schema, alias] if p]

        if not key_parts:
            key_parts = [dbt_resource_props.get("name", "unknown")]

        return AssetKey(key_parts)

    def get_metadata(self, dbt_resource_props: Mapping[str, Any]) -> Mapping[str, Any]:
        """Get metadata from dbt resource properties.

        Extracts both standard dbt metadata and floe-specific metadata
        from the meta.floe namespace.

        Args:
            dbt_resource_props: dbt manifest node properties.

        Returns:
            Metadata dictionary for Dagster asset.
        """
        metadata: dict[str, Any] = {}

        # Standard dbt metadata
        if description := dbt_resource_props.get("description"):
            metadata["description"] = MetadataValue.md(description)

        if tags := dbt_resource_props.get("tags"):
            metadata["tags"] = MetadataValue.text(", ".join(tags))

        # Materialization type
        config = dbt_resource_props.get("config", {})
        if materialized := config.get("materialized"):
            metadata["materialization"] = MetadataValue.text(materialized)

        # Schema and database
        if schema := dbt_resource_props.get("schema"):
            metadata["schema"] = MetadataValue.text(schema)
        if database := dbt_resource_props.get("database"):
            metadata["database"] = MetadataValue.text(database)

        # Floe-specific metadata from meta.floe
        floe_meta = dbt_resource_props.get("meta", {}).get("floe", {})

        if owner := floe_meta.get("owner"):
            metadata["owner"] = MetadataValue.text(owner)

        if classification := floe_meta.get("classification"):
            metadata["classification"] = MetadataValue.text(classification)

        # Column count
        if columns := dbt_resource_props.get("columns"):
            metadata["column_count"] = MetadataValue.int(len(columns))

        return metadata

    def get_description(self, dbt_resource_props: Mapping[str, Any]) -> str:
        """Get description from dbt resource properties.

        Args:
            dbt_resource_props: dbt manifest node properties.

        Returns:
            Description string (empty string if not found).
        """
        description = dbt_resource_props.get("description", "")
        return str(description) if description else ""

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        """Get group name from dbt resource properties.

        Uses schema as group name, falling back to package name.

        Args:
            dbt_resource_props: dbt manifest node properties.

        Returns:
            Group name string or None.
        """
        # Try schema first
        if schema := dbt_resource_props.get("schema"):
            return str(schema)

        # Fall back to package name
        if package := dbt_resource_props.get("package_name"):
            return str(package)

        return None

    def get_owners(self, dbt_resource_props: Mapping[str, Any]) -> Sequence[str] | None:
        """Get owners from dbt resource properties.

        Extracts owner from meta.floe.owner namespace.

        Args:
            dbt_resource_props: dbt manifest node properties.

        Returns:
            List of owner strings or None.
        """
        floe_meta = dbt_resource_props.get("meta", {}).get("floe", {})

        if owner := floe_meta.get("owner"):
            return [owner]

        return None

    def get_tags(self, dbt_resource_props: Mapping[str, Any]) -> Mapping[str, str]:
        """Get tags from dbt resource properties.

        Converts dbt tags to Dagster tag format.

        Args:
            dbt_resource_props: dbt manifest node properties.

        Returns:
            Dictionary of tag key-value pairs.
        """
        tags: dict[str, str] = {}

        # Add dbt tags as dagster tags
        dbt_tags = dbt_resource_props.get("tags", [])
        for tag in dbt_tags:
            tags[f"dbt:{tag}"] = "true"

        # Add materialization as tag
        config = dbt_resource_props.get("config", {})
        if materialized := config.get("materialized"):
            tags["materialization"] = materialized

        # Add floe classification as tag
        floe_meta = dbt_resource_props.get("meta", {}).get("floe", {})
        if classification := floe_meta.get("classification"):
            tags["classification"] = classification

        return tags
