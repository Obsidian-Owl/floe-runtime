"""Unit tests for base generator utilities.

Tests for WeightedChoice and other utilities in the base module.
"""

from __future__ import annotations

from collections import OrderedDict

from faker import Faker

from floe_synthetic.generators.base import (
    PLAN_WEIGHTS,
    REGION_WEIGHTS,
    STATUS_WEIGHTS,
    SUBSCRIPTION_STATUS_WEIGHTS,
    WeightedChoice,
)


class TestWeightedChoice:
    """Tests for WeightedChoice utility class."""

    def test_initialization(self) -> None:
        """Test WeightedChoice initializes with weights."""
        wc = WeightedChoice({"a": 3, "b": 1})

        assert wc.values == ["a", "b"]
        assert wc.weights == [3, 1]
        assert len(wc.probabilities) == 2
        # 3/(3+1) = 0.75, 1/(3+1) = 0.25
        assert abs(wc.probabilities[0] - 0.75) < 0.01
        assert abs(wc.probabilities[1] - 0.25) < 0.01

    def test_probabilities_sum_to_one(self) -> None:
        """Test probabilities sum to 1.0."""
        wc = WeightedChoice(STATUS_WEIGHTS)

        total = sum(wc.probabilities)
        assert abs(total - 1.0) < 0.0001

    def test_generate_returns_correct_count(self) -> None:
        """Test generate returns the requested number of values."""
        wc = WeightedChoice({"x": 1, "y": 1})
        fake = Faker()
        fake.seed_instance(42)

        values = wc.generate(fake, 100)

        assert len(values) == 100

    def test_generate_only_returns_valid_values(self) -> None:
        """Test generate only returns values from the weights dict."""
        wc = WeightedChoice({"red": 5, "blue": 3, "green": 2})
        fake = Faker()
        fake.seed_instance(42)

        values = wc.generate(fake, 1000)

        valid_values = {"red", "blue", "green"}
        for v in values:
            assert v in valid_values

    def test_generate_approximates_distribution(self) -> None:
        """Test generate approximates the expected distribution."""
        wc = WeightedChoice({"high": 80, "low": 20})
        fake = Faker()
        fake.seed_instance(42)

        values = wc.generate(fake, 10000)

        high_count = sum(1 for v in values if v == "high")
        high_ratio = high_count / len(values)

        # Should be approximately 0.8 (within 5% tolerance)
        assert 0.75 < high_ratio < 0.85

    def test_build_weighted_elements(self) -> None:
        """Test _build_weighted_elements returns correct format."""
        wc = WeightedChoice({"a": 1, "b": 2, "c": 3})

        elements = wc._build_weighted_elements()

        # Must be OrderedDict for Faker compatibility
        assert isinstance(elements, OrderedDict)
        assert len(elements) == 3
        assert "a" in elements
        assert "b" in elements
        assert "c" in elements
        # Values should be probabilities (floats)
        for v in elements.values():
            assert isinstance(v, float)


class TestPrebuiltWeights:
    """Tests for pre-built weight constants."""

    def test_status_weights_is_valid(self) -> None:
        """Test STATUS_WEIGHTS is a valid weights dict."""
        assert isinstance(STATUS_WEIGHTS, dict)
        assert len(STATUS_WEIGHTS) > 0
        assert all(isinstance(v, int) for v in STATUS_WEIGHTS.values())
        assert "completed" in STATUS_WEIGHTS

    def test_region_weights_is_valid(self) -> None:
        """Test REGION_WEIGHTS is a valid weights dict."""
        assert isinstance(REGION_WEIGHTS, dict)
        assert len(REGION_WEIGHTS) == 4  # north, south, east, west
        assert all(isinstance(v, int) for v in REGION_WEIGHTS.values())

    def test_plan_weights_is_valid(self) -> None:
        """Test PLAN_WEIGHTS is a valid weights dict."""
        assert isinstance(PLAN_WEIGHTS, dict)
        assert len(PLAN_WEIGHTS) > 0
        assert "free" in PLAN_WEIGHTS
        assert "enterprise" in PLAN_WEIGHTS

    def test_subscription_status_weights_is_valid(self) -> None:
        """Test SUBSCRIPTION_STATUS_WEIGHTS is a valid weights dict."""
        assert isinstance(SUBSCRIPTION_STATUS_WEIGHTS, dict)
        assert "active" in SUBSCRIPTION_STATUS_WEIGHTS
        assert "churned" in SUBSCRIPTION_STATUS_WEIGHTS
