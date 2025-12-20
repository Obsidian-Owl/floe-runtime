"""Weighted distribution utilities.

This module provides helpers for creating realistic weighted distributions
for categorical data generation.
"""

from __future__ import annotations

import random
from typing import TypeVar

T = TypeVar("T")


class WeightedDistribution:
    """Helper for weighted random selection.

    Provides a clean interface for selecting values based on weights,
    with support for seeding and batch generation.

    Example:
        >>> statuses = WeightedDistribution({
        ...     "completed": 60,
        ...     "processing": 20,
        ...     "pending": 15,
        ...     "cancelled": 5,
        ... })
        >>> values = statuses.sample(100)  # 100 values with this distribution
    """

    def __init__(self, weights: dict[str, int | float], seed: int | None = None) -> None:
        """Initialize with weight mapping.

        Args:
            weights: Mapping of values to their relative weights
            seed: Optional random seed for reproducibility
        """
        self.values = list(weights.keys())
        self.weights = list(weights.values())
        self._rng = random.Random(seed)

    def sample(self, count: int) -> list[str]:
        """Generate weighted random values.

        Args:
            count: Number of values to generate

        Returns:
            List of randomly selected values
        """
        return self._rng.choices(self.values, weights=self.weights, k=count)

    def sample_one(self) -> str:
        """Generate a single weighted random value.

        Returns:
            Randomly selected value
        """
        return self._rng.choices(self.values, weights=self.weights, k=1)[0]

    @property
    def probabilities(self) -> dict[str, float]:
        """Get probability distribution.

        Returns:
            Dictionary mapping values to their probabilities
        """
        total = sum(self.weights)
        return {v: w / total for v, w in zip(self.values, self.weights, strict=True)}


# Common weight distributions for reuse
ORDER_STATUS_DISTRIBUTION = WeightedDistribution({
    "completed": 60,
    "processing": 20,
    "pending": 15,
    "cancelled": 5,
})

REGION_DISTRIBUTION = WeightedDistribution({
    "north": 25,
    "south": 25,
    "east": 25,
    "west": 25,
})

PLAN_DISTRIBUTION = WeightedDistribution({
    "free": 50,
    "starter": 25,
    "pro": 20,
    "enterprise": 5,
})
