"""Unit tests for LineageDatasetBuilder.

T053: [US3] Unit tests for LineageDatasetBuilder
"""

from __future__ import annotations

from typing import Any

import pytest


class TestLineageDatasetBuilder:
    """Tests for LineageDatasetBuilder."""

    @pytest.fixture
    def dbt_model_node(self) -> dict[str, Any]:
        """Create sample dbt model node from manifest."""
        return {
            "unique_id": "model.analytics.stg_customers",
            "name": "stg_customers",
            "alias": "stg_customers",
            "database": "analytics_db",
            "schema": "staging",
            "description": "Staged customer data",
            "depends_on": {
                "nodes": [
                    "source.analytics.raw.customers",
                    "model.analytics.stg_orders",
                ]
            },
            "config": {
                "materialized": "table",
            },
            "columns": {
                "customer_id": {
                    "name": "customer_id",
                    "description": "Primary key",
                    "data_type": "INTEGER",
                    "meta": {},
                },
                "email": {
                    "name": "email",
                    "description": "Customer email",
                    "data_type": "VARCHAR",
                    "meta": {
                        "floe": {
                            "classification": "pii",
                            "pii_type": "email",
                            "sensitivity": "high",
                        }
                    },
                },
                "name": {
                    "name": "name",
                    "description": "Customer name",
                    "data_type": "VARCHAR",
                    "meta": {
                        "floe": {
                            "classification": "pii",
                            "pii_type": "name",
                            "sensitivity": "medium",
                        }
                    },
                },
            },
            "meta": {
                "floe": {
                    "owner": "data-team",
                }
            },
        }

    @pytest.fixture
    def dbt_source_node(self) -> dict[str, Any]:
        """Create sample dbt source node from manifest."""
        return {
            "unique_id": "source.analytics.raw.customers",
            "name": "customers",
            "source_name": "raw",
            "database": "raw_db",
            "schema": "public",
            "description": "Raw customer data from operational system",
            "columns": {
                "id": {
                    "name": "id",
                    "description": "Source ID",
                    "data_type": "INTEGER",
                },
            },
        }

    def test_build_from_dbt_node_creates_dataset(
        self, dbt_model_node: dict[str, Any]
    ) -> None:
        """Test building LineageDataset from dbt model node."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder
        from floe_dagster.lineage.events import LineageDataset

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        dataset = builder.build_from_dbt_node(dbt_model_node)

        assert isinstance(dataset, LineageDataset)
        assert dataset.namespace == "snowflake://account"
        assert dataset.name == "analytics_db.staging.stg_customers"

    def test_build_from_dbt_node_includes_schema_facet(
        self, dbt_model_node: dict[str, Any]
    ) -> None:
        """Test built dataset includes schema facet with columns."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        dataset = builder.build_from_dbt_node(dbt_model_node)

        assert "schema" in dataset.facets
        schema_facet = dataset.facets["schema"]
        assert "fields" in schema_facet

        field_names = [f["name"] for f in schema_facet["fields"]]
        assert "customer_id" in field_names
        assert "email" in field_names
        assert "name" in field_names

    def test_build_from_dbt_node_includes_datasource_facet(
        self, dbt_model_node: dict[str, Any]
    ) -> None:
        """Test built dataset includes dataSource facet."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        dataset = builder.build_from_dbt_node(dbt_model_node)

        assert "dataSource" in dataset.facets
        datasource = dataset.facets["dataSource"]
        assert datasource["name"] == "analytics_db"
        assert "snowflake" in datasource["uri"]

    def test_build_from_dbt_source_node(
        self, dbt_source_node: dict[str, Any]
    ) -> None:
        """Test building LineageDataset from dbt source node."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        dataset = builder.build_from_dbt_node(dbt_source_node)

        assert dataset.name == "raw_db.public.customers"

    def test_build_classification_facet_extracts_pii(
        self, dbt_model_node: dict[str, Any]
    ) -> None:
        """Test building classification facet from columns with floe meta."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        classification_facet = builder.build_classification_facet(dbt_model_node)

        assert classification_facet is not None
        assert "columnClassifications" in classification_facet

        classifications = classification_facet["columnClassifications"]

        # Should have email and name classified (both have floe.classification)
        classified_columns = {c["columnName"]: c for c in classifications}
        assert "email" in classified_columns
        assert "name" in classified_columns

        # Check email classification
        assert classified_columns["email"]["classification"] == "pii"
        assert classified_columns["email"]["piiType"] == "email"
        assert classified_columns["email"]["sensitivity"] == "high"

        # Check name classification
        assert classified_columns["name"]["classification"] == "pii"
        assert classified_columns["name"]["piiType"] == "name"
        assert classified_columns["name"]["sensitivity"] == "medium"

    def test_build_classification_facet_returns_none_when_no_classifications(
        self,
    ) -> None:
        """Test returns None when no columns have classifications."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        node_without_classifications = {
            "unique_id": "model.analytics.dim_dates",
            "name": "dim_dates",
            "database": "analytics_db",
            "schema": "public",
            "columns": {
                "date_id": {
                    "name": "date_id",
                    "data_type": "INTEGER",
                    "meta": {},  # No floe classification
                },
            },
        }

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        classification_facet = builder.build_classification_facet(
            node_without_classifications
        )

        assert classification_facet is None

    def test_build_dataset_with_classification_facet(
        self, dbt_model_node: dict[str, Any]
    ) -> None:
        """Test built dataset includes classification facet when columns have classifications."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        builder = LineageDatasetBuilder(
            namespace_prefix="snowflake://account",
            include_classifications=True,
        )

        dataset = builder.build_from_dbt_node(dbt_model_node)

        assert "columnClassification" in dataset.facets
        assert len(dataset.facets["columnClassification"]["columnClassifications"]) == 2

    def test_custom_namespace_prefix(self, dbt_model_node: dict[str, Any]) -> None:
        """Test builder respects custom namespace prefix."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        builder = LineageDatasetBuilder(namespace_prefix="bigquery://my-project")

        dataset = builder.build_from_dbt_node(dbt_model_node)

        assert dataset.namespace == "bigquery://my-project"

    def test_build_multiple_datasets(self, dbt_model_node: dict[str, Any]) -> None:
        """Test building multiple datasets in sequence."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        node1 = dbt_model_node.copy()
        node1["name"] = "model_a"
        node1["alias"] = "model_a"

        node2 = dbt_model_node.copy()
        node2["name"] = "model_b"
        node2["alias"] = "model_b"

        dataset1 = builder.build_from_dbt_node(node1)
        dataset2 = builder.build_from_dbt_node(node2)

        assert "model_a" in dataset1.name
        assert "model_b" in dataset2.name

    def test_build_from_dbt_node_handles_missing_columns(self) -> None:
        """Test building dataset when columns dict is missing."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        node_without_columns = {
            "unique_id": "model.analytics.stg_test",
            "name": "stg_test",
            "alias": "stg_test",
            "database": "analytics_db",
            "schema": "staging",
            # No columns key
        }

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        dataset = builder.build_from_dbt_node(node_without_columns)

        # Should still create dataset, schema facet may be empty
        assert dataset.name == "analytics_db.staging.stg_test"

    def test_build_from_dbt_node_uses_alias_over_name(self) -> None:
        """Test builder uses alias when different from name."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        node_with_alias = {
            "unique_id": "model.analytics.my_model",
            "name": "my_model",
            "alias": "custom_table_name",
            "database": "analytics_db",
            "schema": "staging",
        }

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        dataset = builder.build_from_dbt_node(node_with_alias)

        # Should use alias for table name
        assert dataset.name == "analytics_db.staging.custom_table_name"

    def test_build_inputs_from_depends_on(
        self,
        dbt_model_node: dict[str, Any],
    ) -> None:
        """Test building input datasets from depends_on."""
        from floe_dagster.lineage.builder import LineageDatasetBuilder

        # Mock manifest with upstream models
        manifest = {
            "nodes": {
                "model.analytics.stg_orders": {
                    "unique_id": "model.analytics.stg_orders",
                    "name": "stg_orders",
                    "alias": "stg_orders",
                    "database": "analytics_db",
                    "schema": "staging",
                },
            },
            "sources": {
                "source.analytics.raw.customers": {
                    "unique_id": "source.analytics.raw.customers",
                    "name": "customers",
                    "database": "raw_db",
                    "schema": "public",
                },
            },
        }

        builder = LineageDatasetBuilder(namespace_prefix="snowflake://account")

        inputs = builder.build_inputs_from_manifest(dbt_model_node, manifest)

        assert len(inputs) == 2
        input_names = [d.name for d in inputs]
        assert "analytics_db.staging.stg_orders" in input_names
        assert "raw_db.public.customers" in input_names
