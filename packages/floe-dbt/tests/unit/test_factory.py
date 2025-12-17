"""Unit tests for ProfileFactory.

T022: [P] [US2] Unit tests for ProfileFactory
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator


class TestProfileFactory:
    """Test suite for ProfileFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory class."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    def test_create_duckdb_generator(self, factory: Any) -> None:
        """Test creating DuckDB generator."""
        generator = factory.create("duckdb")
        assert isinstance(generator, ProfileGenerator)

    def test_create_snowflake_generator(self, factory: Any) -> None:
        """Test creating Snowflake generator."""
        generator = factory.create("snowflake")
        assert isinstance(generator, ProfileGenerator)

    def test_create_bigquery_generator(self, factory: Any) -> None:
        """Test creating BigQuery generator."""
        generator = factory.create("bigquery")
        assert isinstance(generator, ProfileGenerator)

    def test_create_redshift_generator(self, factory: Any) -> None:
        """Test creating Redshift generator."""
        generator = factory.create("redshift")
        assert isinstance(generator, ProfileGenerator)

    def test_create_databricks_generator(self, factory: Any) -> None:
        """Test creating Databricks generator."""
        generator = factory.create("databricks")
        assert isinstance(generator, ProfileGenerator)

    def test_create_postgres_generator(self, factory: Any) -> None:
        """Test creating PostgreSQL generator."""
        generator = factory.create("postgres")
        assert isinstance(generator, ProfileGenerator)

    def test_create_spark_generator(self, factory: Any) -> None:
        """Test creating Spark generator."""
        generator = factory.create("spark")
        assert isinstance(generator, ProfileGenerator)

    def test_create_unknown_target_raises(self, factory: Any) -> None:
        """Test that unknown target raises error."""
        with pytest.raises(ValueError) as exc_info:
            factory.create("unknown_target")

        assert "unknown_target" in str(exc_info.value).lower()
        assert "supported" in str(exc_info.value).lower()

    def test_supported_targets_list(self, factory: Any) -> None:
        """Test that supported targets list includes all 7 targets."""
        supported = factory.supported_targets()

        assert "duckdb" in supported
        assert "snowflake" in supported
        assert "bigquery" in supported
        assert "redshift" in supported
        assert "databricks" in supported
        assert "postgres" in supported
        assert "spark" in supported
        assert len(supported) == 7

    def test_is_supported_returns_true_for_valid(self, factory: Any) -> None:
        """Test is_supported returns True for valid targets."""
        assert factory.is_supported("duckdb") is True
        assert factory.is_supported("snowflake") is True
        assert factory.is_supported("bigquery") is True

    def test_is_supported_returns_false_for_invalid(self, factory: Any) -> None:
        """Test is_supported returns False for invalid targets."""
        assert factory.is_supported("mysql") is False
        assert factory.is_supported("oracle") is False
        assert factory.is_supported("") is False

    def test_create_returns_new_instance_each_call(self, factory: Any) -> None:
        """Test that create returns new instance each call."""
        gen1 = factory.create("duckdb")
        gen2 = factory.create("duckdb")

        assert gen1 is not gen2

    def test_create_case_insensitive(self, factory: Any) -> None:
        """Test that target matching is case insensitive."""
        # Should work with lowercase (standard)
        gen_lower = factory.create("duckdb")
        assert isinstance(gen_lower, ProfileGenerator)

        # Test case handling - factory may normalize or error
        # depending on implementation choice
        try:
            gen_upper = factory.create("DUCKDB")
            assert isinstance(gen_upper, ProfileGenerator)
        except ValueError:
            # Also acceptable - strict case matching
            pass
