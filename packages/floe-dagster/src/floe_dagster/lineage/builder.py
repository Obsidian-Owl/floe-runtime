"""LineageDatasetBuilder for building OpenLineage datasets from dbt nodes.

T060: [US3] Implement LineageDatasetBuilder.build_from_dbt_node
T061: [US3] Implement LineageDatasetBuilder.build_classification_facet
"""

from __future__ import annotations

from typing import Any

from floe_dagster.lineage.events import LineageDataset
from floe_dagster.lineage.facets import ColumnClassification, build_classification_facet


class LineageDatasetBuilder:
    """Builder for creating OpenLineage datasets from dbt manifest nodes.

    Extracts dataset information from dbt model and source nodes,
    including schema facets, data source facets, and column-level
    classification metadata from the meta.floe namespace.

    Attributes:
        namespace_prefix: Prefix for dataset namespaces (e.g., "snowflake://account")
        include_classifications: Whether to include classification facets

    Example:
        >>> builder = LineageDatasetBuilder(
        ...     namespace_prefix="snowflake://my-account",
        ...     include_classifications=True,
        ... )
        >>> dataset = builder.build_from_dbt_node(dbt_model_node)
        >>> dataset.name
        'analytics.staging.stg_customers'
    """

    def __init__(
        self,
        namespace_prefix: str,
        include_classifications: bool = False,
    ) -> None:
        """Initialize LineageDatasetBuilder.

        Args:
            namespace_prefix: Prefix for dataset namespaces.
            include_classifications: Whether to include classification facets.
        """
        self.namespace_prefix = namespace_prefix
        self.include_classifications = include_classifications

    def build_from_dbt_node(self, node: dict[str, Any]) -> LineageDataset:
        """Build LineageDataset from dbt manifest node.

        Creates an OpenLineage dataset from a dbt model or source node,
        extracting database, schema, and table information along with
        facets for schema and data source.

        Args:
            node: dbt manifest node (model or source).

        Returns:
            LineageDataset with populated facets.

        Example:
            >>> node = {
            ...     "database": "analytics_db",
            ...     "schema": "staging",
            ...     "alias": "stg_customers",
            ...     "columns": {...},
            ... }
            >>> dataset = builder.build_from_dbt_node(node)
        """
        # Extract table identifier
        database = node.get("database", "")
        schema = node.get("schema", "")

        # Use alias if available, otherwise name
        # For sources, use source_name + name pattern
        if "source_name" in node:
            # Source node
            table = node.get("name", "")
        else:
            # Model node - prefer alias
            table = node.get("alias") or node.get("name", "")

        # Build fully qualified name
        name_parts = [p for p in [database, schema, table] if p]
        name = ".".join(name_parts)

        # Build facets
        facets: dict[str, Any] = {}

        # Schema facet
        schema_facet = self._build_schema_facet(node)
        if schema_facet:
            facets["schema"] = schema_facet

        # DataSource facet
        facets["dataSource"] = {
            "name": database or schema or "unknown",
            "uri": self.namespace_prefix,
        }

        # Classification facet (if enabled)
        if self.include_classifications:
            classification_facet = self.build_classification_facet(node)
            if classification_facet:
                facets["columnClassification"] = classification_facet

        return LineageDataset(
            namespace=self.namespace_prefix,
            name=name,
            facets=facets,
        )

    def build_classification_facet(self, node: dict[str, Any]) -> dict[str, Any] | None:
        """Build classification facet from dbt node columns.

        Extracts column-level classifications from the meta.floe
        namespace of column definitions.

        Args:
            node: dbt manifest node with columns.

        Returns:
            OpenLineage classification facet, or None if no classifications.

        Example:
            >>> node = {
            ...     "columns": {
            ...         "email": {
            ...             "meta": {
            ...                 "floe": {"classification": "pii", "pii_type": "email"}
            ...             }
            ...         }
            ...     }
            ... }
            >>> facet = builder.build_classification_facet(node)
        """
        columns = node.get("columns", {})

        classifications: list[ColumnClassification] = []

        for col_name, col_info in columns.items():
            meta = col_info.get("meta", {})
            classification = ColumnClassification.from_dbt_meta(col_name, meta)
            if classification:
                classifications.append(classification)

        return build_classification_facet(classifications)

    def _build_schema_facet(self, node: dict[str, Any]) -> dict[str, Any] | None:
        """Build schema facet from dbt node columns.

        Args:
            node: dbt manifest node with columns.

        Returns:
            OpenLineage schema facet, or None if no columns.
        """
        columns = node.get("columns", {})

        if not columns:
            return None

        fields = []
        for col_name, col_info in columns.items():
            field: dict[str, Any] = {
                "name": col_name,
            }

            data_type = col_info.get("data_type")
            if data_type:
                field["type"] = data_type

            description = col_info.get("description")
            if description:
                field["description"] = description

            fields.append(field)

        return {
            "_producer": "floe-dagster",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
            "fields": fields,
        }

    def build_inputs_from_manifest(
        self,
        node: dict[str, Any],
        manifest: dict[str, Any],
    ) -> list[LineageDataset]:
        """Build input datasets from a node's depends_on.

        Resolves upstream dependencies and creates LineageDataset
        objects for each input.

        Args:
            node: dbt manifest node with depends_on.
            manifest: Full dbt manifest dictionary.

        Returns:
            List of input LineageDatasets.
        """
        depends_on = node.get("depends_on", {}).get("nodes", [])

        inputs: list[LineageDataset] = []

        for dep_id in depends_on:
            # Look up in nodes first (models), then sources
            dep_node = manifest.get("nodes", {}).get(dep_id)

            if not dep_node:
                dep_node = manifest.get("sources", {}).get(dep_id)

            if dep_node:
                inputs.append(self.build_from_dbt_node(dep_node))

        return inputs
