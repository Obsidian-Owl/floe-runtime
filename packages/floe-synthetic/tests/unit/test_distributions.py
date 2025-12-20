"""Unit tests for distribution helpers.

Tests cover:
- Weighted distributions
- Temporal patterns
"""

from __future__ import annotations

from datetime import datetime

import pytest

from floe_synthetic.distributions.weighted import (
    ORDER_STATUS_DISTRIBUTION,
    REGION_DISTRIBUTION,
    WeightedDistribution,
)
from floe_synthetic.distributions.temporal import (
    BUSINESS_HOURS_DISTRIBUTION,
    TemporalDistribution,
)

pytestmark = pytest.mark.unit


class TestWeightedDistribution:
    """Tests for WeightedDistribution."""

    def test_sample_returns_correct_count(self) -> None:
        """Sample returns the requested number of values."""
        dist = WeightedDistribution({"a": 50, "b": 50}, seed=42)
        values = dist.sample(100)

        assert len(values) == 100

    def test_sample_only_returns_valid_values(self) -> None:
        """Sample only returns values from the distribution."""
        dist = WeightedDistribution({"x": 1, "y": 2, "z": 3}, seed=42)
        values = dist.sample(1000)

        valid_values = {"x", "y", "z"}
        assert set(values).issubset(valid_values)

    def test_sample_one_returns_string(self) -> None:
        """Sample one returns a single string."""
        dist = WeightedDistribution({"a": 1, "b": 1}, seed=42)
        value = dist.sample_one()

        assert isinstance(value, str)
        assert value in {"a", "b"}

    def test_deterministic_with_seed(self) -> None:
        """Same seed produces identical samples."""
        dist1 = WeightedDistribution({"a": 1, "b": 1}, seed=42)
        dist2 = WeightedDistribution({"a": 1, "b": 1}, seed=42)

        values1 = dist1.sample(100)
        values2 = dist2.sample(100)

        assert values1 == values2

    def test_different_seeds_differ(self) -> None:
        """Different seeds produce different samples."""
        dist1 = WeightedDistribution({"a": 1, "b": 1}, seed=42)
        dist2 = WeightedDistribution({"a": 1, "b": 1}, seed=123)

        values1 = dist1.sample(100)
        values2 = dist2.sample(100)

        assert values1 != values2

    def test_weighted_distribution_approximates_weights(self) -> None:
        """Weights are approximately respected in large samples."""
        dist = WeightedDistribution({"a": 75, "b": 25}, seed=42)
        values = dist.sample(10000)

        a_ratio = values.count("a") / len(values)

        # Should be approximately 75% (±5%)
        assert 0.70 <= a_ratio <= 0.80

    def test_probabilities_sum_to_one(self) -> None:
        """Probabilities dictionary sums to 1.0."""
        dist = WeightedDistribution({"a": 30, "b": 20, "c": 50})
        probs = dist.probabilities

        assert abs(sum(probs.values()) - 1.0) < 0.001

    def test_probabilities_match_weights(self) -> None:
        """Probabilities correctly reflect weights."""
        dist = WeightedDistribution({"x": 1, "y": 2, "z": 7})
        probs = dist.probabilities

        assert abs(probs["x"] - 0.1) < 0.001
        assert abs(probs["y"] - 0.2) < 0.001
        assert abs(probs["z"] - 0.7) < 0.001


class TestPrebuiltDistributions:
    """Tests for pre-built distribution constants."""

    def test_order_status_distribution(self) -> None:
        """ORDER_STATUS_DISTRIBUTION has expected values."""
        values = ORDER_STATUS_DISTRIBUTION.sample(100)
        valid = {"completed", "processing", "pending", "cancelled"}
        assert set(values).issubset(valid)

    def test_region_distribution(self) -> None:
        """REGION_DISTRIBUTION has expected values."""
        values = REGION_DISTRIBUTION.sample(100)
        valid = {"north", "south", "east", "west"}
        assert set(values).issubset(valid)


class TestTemporalDistribution:
    """Tests for TemporalDistribution."""

    def test_daily_factor_night_is_low(self) -> None:
        """Night hours have low activity factor."""
        dist = TemporalDistribution()

        for hour in [0, 1, 2, 3, 4, 5]:
            factor = dist.daily_factor(hour)
            assert factor < 0.3, f"Hour {hour} should have low factor"

    def test_daily_factor_peak_hours_are_high(self) -> None:
        """Peak hours have high activity factor."""
        dist = TemporalDistribution(daily_peak_hours=(10, 14, 18, 21))

        for hour in [10, 14, 18, 21]:
            factor = dist.daily_factor(hour)
            assert factor == 1.0, f"Peak hour {hour} should have factor 1.0"

    def test_weekly_factor_weekend_is_lower(self) -> None:
        """Weekend has lower activity factor."""
        dist = TemporalDistribution(weekend_factor=0.3)

        # Weekdays
        for day in [0, 1, 2, 3, 4]:
            factor = dist.weekly_factor(day)
            assert factor >= 0.8, f"Weekday {day} should have high factor"

        # Weekend
        for day in [5, 6]:
            factor = dist.weekly_factor(day)
            assert factor == 0.3, f"Weekend day {day} should have low factor"

    def test_trend_factor_increases_over_time(self) -> None:
        """Positive trend increases factor over time."""
        dist = TemporalDistribution(trend_percent=0.05)  # 5% monthly growth
        base = datetime(2024, 1, 1)

        factor_jan = dist.trend_factor(datetime(2024, 1, 15), base)
        factor_jul = dist.trend_factor(datetime(2024, 7, 15), base)

        assert factor_jul > factor_jan

    def test_zero_trend_returns_one(self) -> None:
        """Zero trend always returns 1.0."""
        dist = TemporalDistribution(trend_percent=0.0)
        base = datetime(2024, 1, 1)

        factor = dist.trend_factor(datetime(2025, 12, 31), base)
        assert factor == 1.0

    def test_adjusted_count_is_positive(self) -> None:
        """Adjusted count is always at least 1."""
        dist = TemporalDistribution(
            weekend_factor=0.01,
            noise_percent=0.0,
        )

        # Saturday night - very low factor
        dt = datetime(2024, 1, 6, 3, 0)  # Saturday 3am
        count = dist.adjusted_count(base_count=1, date=dt)

        assert count >= 1

    def test_combined_factor_varies(self) -> None:
        """Combined factor varies across different times."""
        dist = TemporalDistribution(seed=42)

        # Business hours Tuesday
        business = datetime(2024, 1, 9, 10, 0)
        # Saturday night
        weekend = datetime(2024, 1, 6, 2, 0)

        factor_business = dist.combined_factor(business)
        factor_weekend = dist.combined_factor(weekend)

        assert factor_business > factor_weekend

    def test_generate_timestamps_returns_correct_count(self) -> None:
        """Generate timestamps returns requested count."""
        dist = TemporalDistribution(seed=42)

        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        timestamps = dist.generate_timestamps(100, start, end)

        assert len(timestamps) == 100

    def test_generate_timestamps_within_range(self) -> None:
        """Generated timestamps fall within specified range."""
        dist = TemporalDistribution(seed=42)

        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        timestamps = dist.generate_timestamps(100, start, end)

        for ts in timestamps:
            assert start <= ts <= end

    def test_generate_timestamps_sorted(self) -> None:
        """Generated timestamps are sorted."""
        dist = TemporalDistribution(seed=42)

        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        timestamps = dist.generate_timestamps(100, start, end)

        assert timestamps == sorted(timestamps)


class TestPrebuiltTemporalDistributions:
    """Tests for pre-built temporal distributions."""

    def test_business_hours_distribution(self) -> None:
        """BUSINESS_HOURS_DISTRIBUTION has low weekend factor."""
        assert BUSINESS_HOURS_DISTRIBUTION.weekend_factor == 0.1
