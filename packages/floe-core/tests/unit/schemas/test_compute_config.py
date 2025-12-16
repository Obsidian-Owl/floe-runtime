"""Unit tests for ComputeConfig model.

T011: [US1] Unit tests for ComputeConfig validation
Tests ComputeConfig with target validation and secret ref patterns.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestComputeConfig:
    """Tests for ComputeConfig model."""

    def test_compute_config_requires_target(self) -> None:
        """ComputeConfig should require target field."""
        from floe_core.schemas import ComputeConfig

        with pytest.raises(ValidationError) as exc_info:
            ComputeConfig()  # type: ignore[call-arg]

        assert "target" in str(exc_info.value)

    def test_compute_config_with_valid_target(self) -> None:
        """ComputeConfig should accept valid target."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target=ComputeTarget.duckdb)
        assert config.target == ComputeTarget.duckdb

    def test_compute_config_with_string_target(self) -> None:
        """ComputeConfig should accept target as string."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target="snowflake")  # type: ignore[arg-type]
        assert config.target == ComputeTarget.snowflake

    def test_compute_config_connection_secret_ref_optional(self) -> None:
        """ComputeConfig.connection_secret_ref should be optional."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target=ComputeTarget.duckdb)
        assert config.connection_secret_ref is None

    def test_compute_config_valid_secret_ref(self) -> None:
        """ComputeConfig should accept valid K8s secret ref."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            connection_secret_ref="my-snowflake-secret",
        )
        assert config.connection_secret_ref == "my-snowflake-secret"

    def test_compute_config_secret_ref_with_underscores(self) -> None:
        """ComputeConfig should accept secret ref with underscores."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            connection_secret_ref="my_snowflake_secret",
        )
        assert config.connection_secret_ref == "my_snowflake_secret"

    def test_compute_config_secret_ref_invalid_start_char(self) -> None:
        """ComputeConfig should reject secret ref starting with invalid char."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        with pytest.raises(ValidationError) as exc_info:
            ComputeConfig(
                target=ComputeTarget.snowflake,
                connection_secret_ref="-invalid-start",
            )

        assert "connection_secret_ref" in str(exc_info.value)

    def test_compute_config_secret_ref_too_long(self) -> None:
        """ComputeConfig should reject secret ref exceeding 253 chars."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        long_name = "a" * 254
        with pytest.raises(ValidationError) as exc_info:
            ComputeConfig(
                target=ComputeTarget.snowflake,
                connection_secret_ref=long_name,
            )

        assert "connection_secret_ref" in str(exc_info.value)

    def test_compute_config_properties_default_empty_dict(self) -> None:
        """ComputeConfig.properties should default to empty dict."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target=ComputeTarget.duckdb)
        assert config.properties == {}

    def test_compute_config_properties_with_values(self) -> None:
        """ComputeConfig should accept properties dict."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            properties={
                "account": "xy12345.us-east-1",
                "warehouse": "COMPUTE_WH",
            },
        )
        assert config.properties["account"] == "xy12345.us-east-1"
        assert config.properties["warehouse"] == "COMPUTE_WH"

    def test_compute_config_is_frozen(self) -> None:
        """ComputeConfig should be immutable (frozen)."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target=ComputeTarget.duckdb)

        with pytest.raises(ValidationError):
            config.target = ComputeTarget.snowflake  # type: ignore[misc]

    def test_compute_config_rejects_extra_fields(self) -> None:
        """ComputeConfig should reject unknown fields."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        with pytest.raises(ValidationError) as exc_info:
            ComputeConfig(
                target=ComputeTarget.duckdb,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()


class TestDuckDBTargetProperties:
    """T055: [US5] Unit tests for DuckDB target properties."""

    def test_duckdb_with_path_property(self) -> None:
        """DuckDB target should accept path property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.duckdb,
            properties={"path": "./data/local.duckdb"},
        )
        assert config.properties["path"] == "./data/local.duckdb"

    def test_duckdb_with_memory_mode(self) -> None:
        """DuckDB target should accept memory mode."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.duckdb,
            properties={"path": ":memory:"},
        )
        assert config.properties["path"] == ":memory:"

    def test_duckdb_with_threads_property(self) -> None:
        """DuckDB target should accept threads property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.duckdb,
            properties={"path": ":memory:", "threads": 4},
        )
        assert config.properties["threads"] == 4


class TestSnowflakeTargetProperties:
    """T056: [US5] Unit tests for Snowflake target properties."""

    def test_snowflake_with_account_property(self) -> None:
        """Snowflake target should accept account property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            properties={"account": "xy12345.us-east-1"},
        )
        assert config.properties["account"] == "xy12345.us-east-1"

    def test_snowflake_with_warehouse_property(self) -> None:
        """Snowflake target should accept warehouse property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            properties={"warehouse": "COMPUTE_WH"},
        )
        assert config.properties["warehouse"] == "COMPUTE_WH"

    def test_snowflake_with_database_schema(self) -> None:
        """Snowflake target should accept database and schema properties."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            properties={
                "account": "xy12345",
                "database": "ANALYTICS",
                "schema": "PUBLIC",
            },
        )
        assert config.properties["database"] == "ANALYTICS"
        assert config.properties["schema"] == "PUBLIC"

    def test_snowflake_with_role_property(self) -> None:
        """Snowflake target should accept role property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            properties={"account": "xy12345", "role": "DATA_ENGINEER"},
        )
        assert config.properties["role"] == "DATA_ENGINEER"


class TestBigQueryTargetProperties:
    """T057: [US5] Unit tests for BigQuery target properties."""

    def test_bigquery_with_project_property(self) -> None:
        """BigQuery target should accept project property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.bigquery,
            properties={"project": "my-gcp-project"},
        )
        assert config.properties["project"] == "my-gcp-project"

    def test_bigquery_with_dataset_property(self) -> None:
        """BigQuery target should accept dataset property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.bigquery,
            properties={"project": "my-project", "dataset": "analytics"},
        )
        assert config.properties["dataset"] == "analytics"

    def test_bigquery_with_location_property(self) -> None:
        """BigQuery target should accept location property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.bigquery,
            properties={"project": "my-project", "location": "US"},
        )
        assert config.properties["location"] == "US"

    def test_bigquery_with_method_property(self) -> None:
        """BigQuery target should accept method property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.bigquery,
            properties={"project": "my-project", "method": "service-account"},
        )
        assert config.properties["method"] == "service-account"


class TestRedshiftTargetProperties:
    """T058: [US5] Unit tests for Redshift target properties."""

    def test_redshift_with_host_property(self) -> None:
        """Redshift target should accept host property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.redshift,
            properties={"host": "my-cluster.us-east-1.redshift.amazonaws.com"},
        )
        assert "my-cluster" in config.properties["host"]

    def test_redshift_with_port_property(self) -> None:
        """Redshift target should accept port property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.redshift,
            properties={"host": "my-cluster", "port": 5439},
        )
        assert config.properties["port"] == 5439

    def test_redshift_with_database_property(self) -> None:
        """Redshift target should accept database property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.redshift,
            properties={"host": "my-cluster", "database": "analytics"},
        )
        assert config.properties["database"] == "analytics"


class TestDatabricksTargetProperties:
    """T059: [US5] Unit tests for Databricks target properties."""

    def test_databricks_with_host_property(self) -> None:
        """Databricks target should accept host property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.databricks,
            properties={"host": "my-workspace.cloud.databricks.com"},
        )
        assert "databricks.com" in config.properties["host"]

    def test_databricks_with_http_path_property(self) -> None:
        """Databricks target should accept http_path property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.databricks,
            properties={
                "host": "my-workspace.databricks.com",
                "http_path": "/sql/1.0/warehouses/abc123",
            },
        )
        assert "/sql/" in config.properties["http_path"]

    def test_databricks_with_catalog_schema(self) -> None:
        """Databricks target should accept catalog and schema properties."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.databricks,
            properties={
                "host": "my-workspace.databricks.com",
                "catalog": "unity_catalog",
                "schema": "default",
            },
        )
        assert config.properties["catalog"] == "unity_catalog"
        assert config.properties["schema"] == "default"


class TestPostgresTargetProperties:
    """T060: [US5] Unit tests for PostgreSQL target properties."""

    def test_postgres_with_host_property(self) -> None:
        """PostgreSQL target should accept host property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.postgres,
            properties={"host": "localhost"},
        )
        assert config.properties["host"] == "localhost"

    def test_postgres_with_port_property(self) -> None:
        """PostgreSQL target should accept port property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.postgres,
            properties={"host": "localhost", "port": 5432},
        )
        assert config.properties["port"] == 5432

    def test_postgres_with_database_schema(self) -> None:
        """PostgreSQL target should accept database and schema properties."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.postgres,
            properties={
                "host": "localhost",
                "database": "analytics",
                "schema": "public",
            },
        )
        assert config.properties["database"] == "analytics"
        assert config.properties["schema"] == "public"


class TestSparkTargetProperties:
    """T061: [US5] Unit tests for Spark target properties."""

    def test_spark_with_host_property(self) -> None:
        """Spark target should accept host property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.spark,
            properties={"host": "spark://master:7077"},
        )
        assert "spark://" in config.properties["host"]

    def test_spark_with_method_property(self) -> None:
        """Spark target should accept method property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.spark,
            properties={"method": "thrift"},
        )
        assert config.properties["method"] == "thrift"

    def test_spark_with_cluster_property(self) -> None:
        """Spark target should accept cluster property."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.spark,
            properties={"method": "thrift", "cluster": "my-spark-cluster"},
        )
        assert config.properties["cluster"] == "my-spark-cluster"
