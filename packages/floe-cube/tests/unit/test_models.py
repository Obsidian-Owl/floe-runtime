"""Unit tests for floe_cube.models foundational Pydantic models.

T012: [Phase 2] Unit tests for foundational models (>80% coverage)

Tests all models defined in models.py:
- CubeConfig
- CubeDimension
- CubeMeasure
- CubeJoin
- CubePreAggregation
- CubeSchema
- SecurityContext
"""

from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from floe_cube.models import (
    CubeConfig,
    CubeDimension,
    CubeJoin,
    CubeMeasure,
    CubePreAggregation,
    CubeSchema,
    DatabaseType,
    DimensionType,
    JoinRelationship,
    MeasureType,
    SecurityContext,
    TimeGranularity,
)


class TestDatabaseType:
    """Tests for DatabaseType enum."""

    def test_all_database_types_exist(self) -> None:
        """All expected database types should be defined."""
        assert DatabaseType.POSTGRES.value == "postgres"
        assert DatabaseType.SNOWFLAKE.value == "snowflake"
        assert DatabaseType.BIGQUERY.value == "bigquery"
        assert DatabaseType.DATABRICKS.value == "databricks"
        assert DatabaseType.TRINO.value == "trino"
        assert DatabaseType.DUCKDB.value == "duckdb"

    def test_database_type_count(self) -> None:
        """Should have exactly 6 database types."""
        assert len(DatabaseType) == 6


class TestDimensionType:
    """Tests for DimensionType enum."""

    def test_all_dimension_types_exist(self) -> None:
        """All expected dimension types should be defined."""
        assert DimensionType.STRING.value == "string"
        assert DimensionType.NUMBER.value == "number"
        assert DimensionType.TIME.value == "time"
        assert DimensionType.BOOLEAN.value == "boolean"
        assert DimensionType.GEO.value == "geo"

    def test_dimension_type_count(self) -> None:
        """Should have exactly 5 dimension types."""
        assert len(DimensionType) == 5


class TestMeasureType:
    """Tests for MeasureType enum."""

    def test_all_measure_types_exist(self) -> None:
        """All expected measure types should be defined."""
        assert MeasureType.COUNT.value == "count"
        assert MeasureType.COUNT_DISTINCT.value == "count_distinct"
        assert MeasureType.COUNT_DISTINCT_APPROX.value == "count_distinct_approx"
        assert MeasureType.SUM.value == "sum"
        assert MeasureType.AVG.value == "avg"
        assert MeasureType.MIN.value == "min"
        assert MeasureType.MAX.value == "max"
        assert MeasureType.NUMBER.value == "number"
        assert MeasureType.STRING.value == "string"
        assert MeasureType.TIME.value == "time"
        assert MeasureType.BOOLEAN.value == "boolean"
        assert MeasureType.RUNNING_TOTAL.value == "running_total"

    def test_measure_type_count(self) -> None:
        """Should have exactly 12 measure types."""
        assert len(MeasureType) == 12


class TestJoinRelationship:
    """Tests for JoinRelationship enum."""

    def test_all_join_relationships_exist(self) -> None:
        """All expected join relationships should be defined."""
        assert JoinRelationship.ONE_TO_ONE.value == "one_to_one"
        assert JoinRelationship.ONE_TO_MANY.value == "one_to_many"
        assert JoinRelationship.MANY_TO_ONE.value == "many_to_one"

    def test_join_relationship_count(self) -> None:
        """Should have exactly 3 join relationship types."""
        assert len(JoinRelationship) == 3


class TestTimeGranularity:
    """Tests for TimeGranularity enum."""

    def test_all_time_granularities_exist(self) -> None:
        """All expected time granularities should be defined."""
        assert TimeGranularity.SECOND.value == "second"
        assert TimeGranularity.MINUTE.value == "minute"
        assert TimeGranularity.HOUR.value == "hour"
        assert TimeGranularity.DAY.value == "day"
        assert TimeGranularity.WEEK.value == "week"
        assert TimeGranularity.MONTH.value == "month"
        assert TimeGranularity.QUARTER.value == "quarter"
        assert TimeGranularity.YEAR.value == "year"

    def test_time_granularity_count(self) -> None:
        """Should have exactly 8 time granularity levels."""
        assert len(TimeGranularity) == 8


class TestCubeConfig:
    """Tests for CubeConfig model."""

    def test_minimal_config(self) -> None:
        """CubeConfig should work with just database_type."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        assert config.database_type == DatabaseType.POSTGRES
        assert config.api_port == 4000  # default
        assert config.sql_port == 15432  # default
        assert config.api_secret_ref is None
        assert config.dev_mode is False
        assert config.jwt_audience is None
        assert config.jwt_issuer is None

    def test_full_config(self) -> None:
        """CubeConfig should accept all optional fields."""
        config = CubeConfig(
            database_type=DatabaseType.SNOWFLAKE,
            api_port=8080,
            sql_port=5432,
            api_secret_ref="my-secret",
            dev_mode=True,
            jwt_audience="my-audience",
            jwt_issuer="my-issuer",
        )
        assert config.database_type == DatabaseType.SNOWFLAKE
        assert config.api_port == 8080
        assert config.sql_port == 5432
        assert config.api_secret_ref == "my-secret"
        assert config.dev_mode is True
        assert config.jwt_audience == "my-audience"
        assert config.jwt_issuer == "my-issuer"

    def test_port_validation_min(self) -> None:
        """CubeConfig should reject ports below 1."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(database_type=DatabaseType.POSTGRES, api_port=0)
        assert "api_port" in str(exc_info.value)

    def test_port_validation_max(self) -> None:
        """CubeConfig should reject ports above 65535."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(database_type=DatabaseType.POSTGRES, api_port=65536)
        assert "api_port" in str(exc_info.value)

    def test_api_secret_ref_pattern(self) -> None:
        """CubeConfig should validate api_secret_ref pattern."""
        # Valid secret names
        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            api_secret_ref="my-secret",
        )
        assert config.api_secret_ref == "my-secret"

        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            api_secret_ref="cube-k8s-secret",
        )
        assert config.api_secret_ref == "cube-k8s-secret"

    def test_api_secret_ref_invalid_start(self) -> None:
        """CubeConfig should reject secrets starting with dash."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(
                database_type=DatabaseType.POSTGRES,
                api_secret_ref="-invalid",
            )
        assert "api_secret_ref" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """CubeConfig should be immutable."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        with pytest.raises(ValidationError):
            config.api_port = 9999  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        """CubeConfig should reject unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(
                database_type=DatabaseType.POSTGRES,
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()


class TestCubeDimension:
    """Tests for CubeDimension model."""

    def test_minimal_dimension(self) -> None:
        """CubeDimension should work with just name and sql."""
        dim = CubeDimension(name="customer_id", sql="${CUBE}.customer_id")
        assert dim.name == "customer_id"
        assert dim.sql == "${CUBE}.customer_id"
        assert dim.type == DimensionType.STRING  # default
        assert dim.primary_key is False  # default
        assert dim.description is None
        assert dim.meta is None

    def test_full_dimension(self) -> None:
        """CubeDimension should accept all optional fields."""
        dim = CubeDimension(
            name="order_date",
            sql="${CUBE}.order_date",
            type=DimensionType.TIME,
            primary_key=False,
            description="Date the order was placed",
            meta={"label": "Order Date"},
        )
        assert dim.name == "order_date"
        assert dim.type == DimensionType.TIME
        assert dim.description == "Date the order was placed"
        assert dim.meta == {"label": "Order Date"}

    def test_primary_key_dimension(self) -> None:
        """CubeDimension should support primary_key flag."""
        dim = CubeDimension(
            name="id",
            sql="${CUBE}.id",
            type=DimensionType.NUMBER,
            primary_key=True,
        )
        assert dim.primary_key is True

    def test_name_pattern_validation(self) -> None:
        """CubeDimension name must start with letter."""
        with pytest.raises(ValidationError) as exc_info:
            CubeDimension(name="123invalid", sql="${CUBE}.field")
        assert "name" in str(exc_info.value)

    def test_name_pattern_special_chars(self) -> None:
        """CubeDimension name must only contain alphanumeric and underscore."""
        with pytest.raises(ValidationError) as exc_info:
            CubeDimension(name="invalid-name", sql="${CUBE}.field")
        assert "name" in str(exc_info.value)

    def test_name_empty(self) -> None:
        """CubeDimension name cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            CubeDimension(name="", sql="${CUBE}.field")
        assert "name" in str(exc_info.value)

    def test_sql_empty(self) -> None:
        """CubeDimension sql cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            CubeDimension(name="field", sql="")
        assert "sql" in str(exc_info.value)

    def test_description_max_length(self) -> None:
        """CubeDimension description should have max length."""
        long_description = "a" * 1001
        with pytest.raises(ValidationError) as exc_info:
            CubeDimension(
                name="field",
                sql="${CUBE}.field",
                description=long_description,
            )
        assert "description" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """CubeDimension should be immutable."""
        dim = CubeDimension(name="field", sql="${CUBE}.field")
        with pytest.raises(ValidationError):
            dim.name = "new_name"  # type: ignore[misc]


class TestCubeMeasure:
    """Tests for CubeMeasure model."""

    def test_count_measure_no_sql(self) -> None:
        """CubeMeasure COUNT should work without sql."""
        measure = CubeMeasure(name="count", type=MeasureType.COUNT)
        assert measure.name == "count"
        assert measure.type == MeasureType.COUNT
        assert measure.sql is None

    def test_sum_measure_with_sql(self) -> None:
        """CubeMeasure SUM requires sql expression."""
        measure = CubeMeasure(
            name="total_amount",
            sql="${CUBE}.amount",
            type=MeasureType.SUM,
        )
        assert measure.name == "total_amount"
        assert measure.sql == "${CUBE}.amount"
        assert measure.type == MeasureType.SUM

    def test_measure_with_filters(self) -> None:
        """CubeMeasure should accept filters."""
        measure = CubeMeasure(
            name="active_count",
            type=MeasureType.COUNT,
            filters=[{"sql": "${CUBE}.status = 'active'"}],
        )
        assert measure.filters == [{"sql": "${CUBE}.status = 'active'"}]

    def test_measure_with_description(self) -> None:
        """CubeMeasure should accept description."""
        measure = CubeMeasure(
            name="revenue",
            sql="${CUBE}.amount",
            type=MeasureType.SUM,
            description="Total revenue from sales",
        )
        assert measure.description == "Total revenue from sales"

    def test_name_pattern_validation(self) -> None:
        """CubeMeasure name must follow pattern."""
        with pytest.raises(ValidationError) as exc_info:
            CubeMeasure(name="123invalid", type=MeasureType.COUNT)
        assert "name" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """CubeMeasure should be immutable."""
        measure = CubeMeasure(name="count", type=MeasureType.COUNT)
        with pytest.raises(ValidationError):
            measure.type = MeasureType.SUM  # type: ignore[misc]


class TestCubeJoin:
    """Tests for CubeJoin model."""

    def test_join_one_to_many(self) -> None:
        """CubeJoin should accept ONE_TO_MANY relationship."""
        join = CubeJoin(
            name="orders",
            relationship=JoinRelationship.ONE_TO_MANY,
            sql="${CUBE}.id = ${orders}.customer_id",
        )
        assert join.name == "orders"
        assert join.relationship == JoinRelationship.ONE_TO_MANY
        assert "${orders}.customer_id" in join.sql

    def test_join_many_to_one(self) -> None:
        """CubeJoin should accept MANY_TO_ONE relationship."""
        join = CubeJoin(
            name="customer",
            relationship=JoinRelationship.MANY_TO_ONE,
            sql="${CUBE}.customer_id = ${customer}.id",
        )
        assert join.relationship == JoinRelationship.MANY_TO_ONE

    def test_join_one_to_one(self) -> None:
        """CubeJoin should accept ONE_TO_ONE relationship."""
        join = CubeJoin(
            name="profile",
            relationship=JoinRelationship.ONE_TO_ONE,
            sql="${CUBE}.user_id = ${profile}.user_id",
        )
        assert join.relationship == JoinRelationship.ONE_TO_ONE

    def test_name_pattern_validation(self) -> None:
        """CubeJoin name must follow pattern."""
        with pytest.raises(ValidationError) as exc_info:
            CubeJoin(
                name="invalid-name",
                relationship=JoinRelationship.ONE_TO_ONE,
                sql="${CUBE}.id = ${other}.id",
            )
        assert "name" in str(exc_info.value)

    def test_sql_required(self) -> None:
        """CubeJoin sql is required."""
        with pytest.raises(ValidationError) as exc_info:
            CubeJoin(
                name="orders",
                relationship=JoinRelationship.ONE_TO_MANY,
                sql="",
            )
        assert "sql" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """CubeJoin should be immutable."""
        join = CubeJoin(
            name="orders",
            relationship=JoinRelationship.ONE_TO_MANY,
            sql="${CUBE}.id = ${orders}.customer_id",
        )
        with pytest.raises(ValidationError):
            join.name = "new_name"  # type: ignore[misc]


class TestCubePreAggregation:
    """Tests for CubePreAggregation model."""

    def test_minimal_pre_aggregation(self) -> None:
        """CubePreAggregation should work with just name."""
        pre_agg = CubePreAggregation(name="main")
        assert pre_agg.name == "main"
        assert pre_agg.measures == []
        assert pre_agg.dimensions == []
        assert pre_agg.time_dimension is None
        assert pre_agg.granularity is None
        assert pre_agg.refresh_every == "*/30 * * * *"  # default
        assert pre_agg.external is True  # default

    def test_rollup_pre_aggregation(self) -> None:
        """CubePreAggregation should support rollups."""
        pre_agg = CubePreAggregation(
            name="daily_orders",
            measures=["count", "total_amount"],
            dimensions=["status", "region"],
            time_dimension="created_at",
            granularity=TimeGranularity.DAY,
        )
        assert pre_agg.measures == ["count", "total_amount"]
        assert pre_agg.dimensions == ["status", "region"]
        assert pre_agg.time_dimension == "created_at"
        assert pre_agg.granularity == TimeGranularity.DAY

    def test_custom_refresh_schedule(self) -> None:
        """CubePreAggregation should accept custom refresh schedule."""
        pre_agg = CubePreAggregation(
            name="hourly",
            refresh_every="0 * * * *",
        )
        assert pre_agg.refresh_every == "0 * * * *"

    def test_external_false(self) -> None:
        """CubePreAggregation should accept external=False."""
        pre_agg = CubePreAggregation(name="local", external=False)
        assert pre_agg.external is False

    def test_cron_validation_valid_5_fields(self) -> None:
        """CubePreAggregation should accept valid 5-field cron."""
        pre_agg = CubePreAggregation(
            name="nightly",
            refresh_every="0 0 * * *",  # midnight daily
        )
        assert pre_agg.refresh_every == "0 0 * * *"

    def test_cron_validation_invalid_fields(self) -> None:
        """CubePreAggregation should reject invalid cron with wrong field count."""
        with pytest.raises(ValidationError) as exc_info:
            CubePreAggregation(
                name="invalid",
                refresh_every="0 0 * *",  # only 4 fields
            )
        assert "5 fields" in str(exc_info.value)

    def test_interval_validation(self) -> None:
        """CubePreAggregation should accept simple intervals."""
        pre_agg = CubePreAggregation(
            name="frequent",
            refresh_every="1h",  # simple interval
        )
        assert pre_agg.refresh_every == "1h"

    def test_name_pattern_validation(self) -> None:
        """CubePreAggregation name must follow pattern."""
        with pytest.raises(ValidationError) as exc_info:
            CubePreAggregation(name="invalid-name")
        assert "name" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """CubePreAggregation should be immutable."""
        pre_agg = CubePreAggregation(name="main")
        with pytest.raises(ValidationError):
            pre_agg.external = False  # type: ignore[misc]


class TestCubeSchema:
    """Tests for CubeSchema model."""

    def test_minimal_schema(self) -> None:
        """CubeSchema should work with just name and sql_table."""
        schema = CubeSchema(
            name="orders",
            sql_table="{{ dbt.ref('orders') }}",
        )
        assert schema.name == "orders"
        assert schema.sql_table == "{{ dbt.ref('orders') }}"
        assert schema.description is None
        assert schema.dimensions == []
        assert schema.measures == []
        assert schema.joins == []
        assert schema.pre_aggregations == []
        assert schema.filter_column is None

    def test_full_schema(self) -> None:
        """CubeSchema should accept all fields."""
        dim = CubeDimension(
            name="id", sql="${CUBE}.id", type=DimensionType.NUMBER, primary_key=True
        )
        measure = CubeMeasure(name="count", type=MeasureType.COUNT)
        join = CubeJoin(
            name="customer",
            relationship=JoinRelationship.MANY_TO_ONE,
            sql="${CUBE}.customer_id = ${customer}.id",
        )
        pre_agg = CubePreAggregation(name="main")

        schema = CubeSchema(
            name="orders",
            sql_table="public.orders",
            description="Order data",
            dimensions=[dim],
            measures=[measure],
            joins=[join],
            pre_aggregations=[pre_agg],
            filter_column="organization_id",
        )

        assert schema.description == "Order data"
        assert len(schema.dimensions) == 1
        assert len(schema.measures) == 1
        assert len(schema.joins) == 1
        assert len(schema.pre_aggregations) == 1
        assert schema.filter_column == "organization_id"

    def test_name_pattern_validation(self) -> None:
        """CubeSchema name must follow pattern."""
        with pytest.raises(ValidationError) as exc_info:
            CubeSchema(name="invalid-name", sql_table="table")
        assert "name" in str(exc_info.value)

    def test_sql_table_required(self) -> None:
        """CubeSchema sql_table is required."""
        with pytest.raises(ValidationError) as exc_info:
            CubeSchema(name="orders", sql_table="")
        assert "sql_table" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """CubeSchema should be immutable."""
        schema = CubeSchema(name="orders", sql_table="public.orders")
        with pytest.raises(ValidationError):
            schema.name = "new_name"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        """CubeSchema should reject unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            CubeSchema(
                name="orders",
                sql_table="public.orders",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()


class TestSecurityContext:
    """Tests for SecurityContext model."""

    def test_minimal_security_context(self) -> None:
        """SecurityContext should work with required fields only."""
        future_exp = int(time.time()) + 3600  # 1 hour from now
        ctx = SecurityContext(user_id="user_123", exp=future_exp)
        assert ctx.user_id == "user_123"
        assert ctx.roles == []
        assert ctx.filter_claims == {}
        assert ctx.exp == future_exp

    def test_full_security_context(self) -> None:
        """SecurityContext should accept all fields."""
        future_exp = int(time.time()) + 3600
        ctx = SecurityContext(
            user_id="user_123",
            roles=["admin", "analyst"],
            filter_claims={"organization_id": "org_abc", "department": "sales"},
            exp=future_exp,
        )
        assert ctx.user_id == "user_123"
        assert ctx.roles == ["admin", "analyst"]
        assert ctx.filter_claims["organization_id"] == "org_abc"
        assert ctx.filter_claims["department"] == "sales"

    def test_is_expired_future(self) -> None:
        """SecurityContext.is_expired() should return False for future exp."""
        future_exp = int(time.time()) + 3600
        ctx = SecurityContext(user_id="user_123", exp=future_exp)
        assert ctx.is_expired() is False

    def test_is_expired_past(self) -> None:
        """SecurityContext.is_expired() should return True for past exp."""
        # Use a timestamp from 2021 (safely after 2020, but in the past)
        past_exp = 1609459200  # 2021-01-01
        ctx = SecurityContext(user_id="user_123", exp=past_exp)
        assert ctx.is_expired() is True

    def test_exp_validation_too_old(self) -> None:
        """SecurityContext should reject exp before 2020."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityContext(
                user_id="user_123",
                exp=1000000000,  # Before 2020
            )
        assert "2020" in str(exc_info.value)

    def test_user_id_required(self) -> None:
        """SecurityContext user_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityContext(user_id="", exp=int(time.time()) + 3600)
        assert "user_id" in str(exc_info.value)

    def test_is_frozen(self) -> None:
        """SecurityContext should be immutable."""
        ctx = SecurityContext(user_id="user_123", exp=int(time.time()) + 3600)
        with pytest.raises(ValidationError):
            ctx.user_id = "new_user"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        """SecurityContext should reject unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityContext(
                user_id="user_123",
                exp=int(time.time()) + 3600,
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()


class TestModelSerialization:
    """Tests for model JSON serialization."""

    def test_cube_config_round_trip(self) -> None:
        """CubeConfig should serialize and deserialize correctly."""
        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            api_port=4000,
            dev_mode=True,
        )
        json_str = config.model_dump_json()
        loaded = CubeConfig.model_validate_json(json_str)
        assert loaded == config

    def test_cube_schema_round_trip(self) -> None:
        """CubeSchema should serialize and deserialize correctly."""
        schema = CubeSchema(
            name="orders",
            sql_table="public.orders",
            dimensions=[
                CubeDimension(name="id", sql="${CUBE}.id", primary_key=True),
            ],
            measures=[
                CubeMeasure(name="count", type=MeasureType.COUNT),
            ],
        )
        json_str = schema.model_dump_json()
        loaded = CubeSchema.model_validate_json(json_str)
        assert loaded == schema
        assert len(loaded.dimensions) == 1
        assert len(loaded.measures) == 1

    def test_security_context_round_trip(self) -> None:
        """SecurityContext should serialize and deserialize correctly."""
        ctx = SecurityContext(
            user_id="user_123",
            roles=["admin"],
            filter_claims={"org": "test"},
            exp=int(time.time()) + 3600,
        )
        json_str = ctx.model_dump_json()
        loaded = SecurityContext.model_validate_json(json_str)
        assert loaded.user_id == ctx.user_id
        assert loaded.roles == ctx.roles
        assert loaded.filter_claims == ctx.filter_claims


class TestModelDefaults:
    """Tests for model default values and isolation."""

    def test_cube_schema_default_lists_isolated(self) -> None:
        """CubeSchema default lists should be isolated between instances."""
        schema1 = CubeSchema(name="s1", sql_table="t1")
        schema2 = CubeSchema(name="s2", sql_table="t2")
        assert schema1.dimensions is not schema2.dimensions
        assert schema1.measures is not schema2.measures

    def test_security_context_default_dicts_isolated(self) -> None:
        """SecurityContext default dicts should be isolated."""
        ctx1 = SecurityContext(user_id="u1", exp=int(time.time()) + 3600)
        ctx2 = SecurityContext(user_id="u2", exp=int(time.time()) + 3600)
        assert ctx1.filter_claims is not ctx2.filter_claims
        assert ctx1.roles is not ctx2.roles
