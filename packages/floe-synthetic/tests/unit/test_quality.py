"""Unit tests for data quality defects module.

Tests for configurable data quality scenarios:
- Null injection (FR-027b)
- Duplicate injection (FR-027b)
- Late-arriving data injection (FR-027b)

These quality defects enable dbt data validation demos.

Run with:
    pytest packages/floe-synthetic/tests/unit/test_quality.py -v
"""

from __future__ import annotations

from datetime import datetime

import pyarrow as pa
import pytest

from floe_synthetic.quality import (
    DefectConfig,
    QualityDefectInjector,
)


class TestDefectConfig:
    """Tests for DefectConfig Pydantic model.

    Covers: 007-FR-027b (configurable data quality scenarios)
    """

    @pytest.mark.requirement("007-FR-027b")
    def test_default_config(self) -> None:
        """Default config has zero defect rates."""
        config = DefectConfig()
        assert config.null_rate == 0.0
        assert config.duplicate_rate == 0.0
        assert config.late_arrival_rate == 0.0

    @pytest.mark.requirement("007-FR-027b")
    def test_custom_rates(self) -> None:
        """Config accepts custom defect rates."""
        config = DefectConfig(
            null_rate=0.05,
            duplicate_rate=0.02,
            late_arrival_rate=0.01,
        )
        assert config.null_rate == 0.05
        assert config.duplicate_rate == 0.02
        assert config.late_arrival_rate == 0.01

    @pytest.mark.requirement("007-FR-027b")
    def test_rate_validation_range(self) -> None:
        """Rates must be between 0.0 and 1.0."""
        # Valid boundary values
        config = DefectConfig(null_rate=0.0, duplicate_rate=1.0)
        assert config.null_rate == 0.0
        assert config.duplicate_rate == 1.0

    @pytest.mark.requirement("007-FR-027b")
    def test_rate_validation_negative(self) -> None:
        """Negative rates raise ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            DefectConfig(null_rate=-0.1)
        assert "null_rate" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-027b")
    def test_rate_validation_over_one(self) -> None:
        """Rates over 1.0 raise ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            DefectConfig(duplicate_rate=1.5)
        assert "duplicate_rate" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-027b")
    def test_null_columns_config(self) -> None:
        """Config accepts specific columns for null injection."""
        config = DefectConfig(
            null_rate=0.05,
            null_columns=["email", "region"],
        )
        assert config.null_columns == ["email", "region"]

    @pytest.mark.requirement("007-FR-027b")
    def test_late_arrival_delay_config(self) -> None:
        """Config accepts late arrival delay settings."""
        config = DefectConfig(
            late_arrival_rate=0.01,
            late_arrival_min_hours=24,
            late_arrival_max_hours=168,
        )
        assert config.late_arrival_min_hours == 24
        assert config.late_arrival_max_hours == 168


class TestQualityDefectInjector:
    """Tests for QualityDefectInjector.

    Covers: 007-FR-027b (null, duplicate, late-arriving injection)
    """

    @pytest.fixture
    def sample_table(self) -> pa.Table:
        """Create sample PyArrow table for testing."""
        return pa.table(
            {
                "id": pa.array([1, 2, 3, 4, 5], type=pa.int64()),
                "name": pa.array(
                    ["Alice", "Bob", "Charlie", "Diana", "Eve"],
                    type=pa.string(),
                ),
                "email": pa.array(
                    ["a@test.com", "b@test.com", "c@test.com", "d@test.com", "e@test.com"],
                    type=pa.string(),
                ),
                "amount": pa.array([100.0, 200.0, 300.0, 400.0, 500.0], type=pa.float64()),
                "created_at": pa.array(
                    [
                        datetime(2025, 1, 1, 10, 0),
                        datetime(2025, 1, 2, 10, 0),
                        datetime(2025, 1, 3, 10, 0),
                        datetime(2025, 1, 4, 10, 0),
                        datetime(2025, 1, 5, 10, 0),
                    ],
                    type=pa.timestamp("us"),
                ),
            }
        )

    @pytest.mark.requirement("007-FR-027b")
    def test_injector_creation(self) -> None:
        """Injector can be created with seed and config."""
        config = DefectConfig(null_rate=0.05)
        injector = QualityDefectInjector(seed=42, config=config)
        assert injector.seed == 42
        assert injector.config.null_rate == 0.05

    @pytest.mark.requirement("007-FR-027b")
    def test_injector_default_config(self) -> None:
        """Injector uses default config if none provided."""
        injector = QualityDefectInjector(seed=42)
        assert injector.config.null_rate == 0.0
        assert injector.config.duplicate_rate == 0.0

    @pytest.mark.requirement("007-FR-027b")
    def test_inject_nulls_basic(self, sample_table: pa.Table) -> None:
        """Inject nulls into specified columns."""
        config = DefectConfig(null_rate=0.4, null_columns=["email"])
        injector = QualityDefectInjector(seed=42, config=config)

        result = injector.inject_nulls(sample_table)

        # Result should have same schema
        assert result.schema == sample_table.schema
        # Result should have same number of rows
        assert result.num_rows == sample_table.num_rows
        # Email column should have some nulls (at 40% rate with 5 rows, expect 1-3 nulls)
        email_nulls = result.column("email").null_count
        assert email_nulls > 0  # Some nulls injected
        # Non-target columns should have no nulls
        assert result.column("id").null_count == 0
        assert result.column("name").null_count == 0

    @pytest.mark.requirement("007-FR-027b")
    def test_inject_nulls_multiple_columns(self, sample_table: pa.Table) -> None:
        """Inject nulls into multiple columns."""
        config = DefectConfig(null_rate=0.5, null_columns=["email", "name"])
        injector = QualityDefectInjector(seed=42, config=config)

        result = injector.inject_nulls(sample_table)

        # Both columns should have some nulls
        assert result.column("email").null_count > 0
        assert result.column("name").null_count > 0
        # ID should never have nulls (not in target columns)
        assert result.column("id").null_count == 0

    @pytest.mark.requirement("007-FR-027b")
    def test_inject_nulls_zero_rate(self, sample_table: pa.Table) -> None:
        """Zero null rate means no nulls injected."""
        config = DefectConfig(null_rate=0.0, null_columns=["email"])
        injector = QualityDefectInjector(seed=42, config=config)

        result = injector.inject_nulls(sample_table)

        # No nulls should be injected
        assert result.column("email").null_count == 0

    @pytest.mark.requirement("007-FR-027b")
    def test_inject_duplicates_basic(self, sample_table: pa.Table) -> None:
        """Inject duplicate rows."""
        config = DefectConfig(duplicate_rate=0.4)
        injector = QualityDefectInjector(seed=42, config=config)

        result = injector.inject_duplicates(sample_table)

        # Result should have more rows (duplicates added)
        assert result.num_rows > sample_table.num_rows
        # Schema should be the same
        assert result.schema == sample_table.schema

    @pytest.mark.requirement("007-FR-027b")
    def test_inject_duplicates_zero_rate(self, sample_table: pa.Table) -> None:
        """Zero duplicate rate means no duplicates added."""
        config = DefectConfig(duplicate_rate=0.0)
        injector = QualityDefectInjector(seed=42, config=config)

        result = injector.inject_duplicates(sample_table)

        # Same number of rows
        assert result.num_rows == sample_table.num_rows

    @pytest.mark.requirement("007-FR-027b")
    def test_inject_late_arrivals_basic(self, sample_table: pa.Table) -> None:
        """Inject late-arriving data with timestamp modifications."""
        config = DefectConfig(
            late_arrival_rate=0.4,
            late_arrival_min_hours=24,
            late_arrival_max_hours=48,
            timestamp_column="created_at",
        )
        injector = QualityDefectInjector(seed=42, config=config)

        result = injector.inject_late_arrivals(sample_table)

        # Result should have same number of rows
        assert result.num_rows == sample_table.num_rows
        # Some timestamps should be backdated (earlier than original)
        original_times = sample_table.column("created_at").to_pylist()
        result_times = result.column("created_at").to_pylist()

        # At least one row should have an earlier timestamp
        backdated_count = sum(
            1 for orig, res in zip(original_times, result_times, strict=True) if res < orig
        )
        assert backdated_count > 0

    @pytest.mark.requirement("007-FR-027b")
    def test_inject_late_arrivals_zero_rate(self, sample_table: pa.Table) -> None:
        """Zero late arrival rate means no timestamp changes."""
        config = DefectConfig(
            late_arrival_rate=0.0,
            timestamp_column="created_at",
        )
        injector = QualityDefectInjector(seed=42, config=config)

        result = injector.inject_late_arrivals(sample_table)

        # Timestamps should be unchanged
        original_times = sample_table.column("created_at").to_pylist()
        result_times = result.column("created_at").to_pylist()
        assert original_times == result_times

    @pytest.mark.requirement("007-FR-027b")
    def test_apply_all_defects(self, sample_table: pa.Table) -> None:
        """Apply all defects in one call."""
        config = DefectConfig(
            null_rate=0.2,
            null_columns=["email"],
            duplicate_rate=0.2,
            late_arrival_rate=0.2,
            timestamp_column="created_at",
        )
        injector = QualityDefectInjector(seed=42, config=config)

        result = injector.apply(sample_table)

        # Result should have:
        # - More rows (from duplicates)
        assert result.num_rows >= sample_table.num_rows
        # - Some nulls in email column
        assert result.column("email").null_count > 0

    @pytest.mark.requirement("007-FR-027b")
    def test_reproducibility_with_seed(self, sample_table: pa.Table) -> None:
        """Same seed produces same results."""
        config = DefectConfig(
            null_rate=0.3,
            null_columns=["email"],
            duplicate_rate=0.3,
        )

        injector1 = QualityDefectInjector(seed=42, config=config)
        injector2 = QualityDefectInjector(seed=42, config=config)

        result1 = injector1.apply(sample_table)
        result2 = injector2.apply(sample_table)

        # Results should be identical
        assert result1.equals(result2)

    @pytest.mark.requirement("007-FR-027b")
    def test_different_seeds_different_results(self, sample_table: pa.Table) -> None:
        """Different seeds produce different results."""
        config = DefectConfig(
            null_rate=0.5,
            null_columns=["email"],
        )

        injector1 = QualityDefectInjector(seed=42, config=config)
        injector2 = QualityDefectInjector(seed=99, config=config)

        result1 = injector1.apply(sample_table)
        result2 = injector2.apply(sample_table)

        # Results should differ (different null patterns)
        # Note: With small samples, there's a tiny chance of collision
        # but with 50% rate on 5 rows, very unlikely to be identical
        email1 = result1.column("email").to_pylist()
        email2 = result2.column("email").to_pylist()
        assert email1 != email2
