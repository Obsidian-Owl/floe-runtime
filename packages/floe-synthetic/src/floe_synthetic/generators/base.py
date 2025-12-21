"""Base generator protocol and utilities.

This module defines the DataGenerator protocol that all generators must implement,
plus common utilities for data generation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import Iterator
from typing import Any

import pyarrow as pa
import structlog

logger = structlog.get_logger(__name__)


class DataGenerator(ABC):
    """Abstract base class for synthetic data generators.

    All generators must implement:
    - generate_batch: Generate a single batch of records
    - generate_stream: Stream multiple batches for large datasets

    Generators should:
    - Support deterministic seeding for reproducibility
    - Use weighted distributions for realistic data
    - Output PyArrow tables for Iceberg compatibility

    Example:
        >>> class MyGenerator(DataGenerator):
        ...     def generate_batch(self, count: int, **kwargs) -> pa.Table:
        ...         return pa.table({"id": list(range(count))})
        ...
        ...     def generate_stream(
        ...         self, total: int, batch_size: int = 10000, **kwargs
        ...     ) -> Iterator[pa.Table]:
        ...         for i in range(0, total, batch_size):
        ...             yield self.generate_batch(min(batch_size, total - i), **kwargs)
    """

    @abstractmethod
    def generate_batch(  # pragma: no cover - abstract method
        self, count: int, **kwargs: Any
    ) -> pa.Table:
        """Generate a batch of records as Arrow table.

        Args:
            count: Number of records to generate
            **kwargs: Generator-specific options

        Returns:
            PyArrow Table with generated records
        """
        ...

    @abstractmethod
    def generate_stream(  # pragma: no cover - abstract method
        self,
        total: int,
        batch_size: int = 10000,
        **kwargs: Any,
    ) -> Iterator[pa.Table]:
        """Stream batches for memory-efficient large datasets.

        Args:
            total: Total number of records to generate
            batch_size: Number of records per batch (default: 10000)
            **kwargs: Generator-specific options

        Yields:
            PyArrow Tables, each containing up to batch_size records
        """
        ...

    def _log_generation(self, entity: str, count: int) -> None:
        """Log generation activity.

        Args:
            entity: Name of the entity being generated
            count: Number of records generated
        """
        logger.info("data_generated", entity=entity, count=count)


class WeightedChoice:
    """Helper for weighted random selection.

    Provides a simple interface for selecting values based on weights,
    useful for generating realistic distributions.

    Example:
        >>> from faker import Faker
        >>> fake = Faker()
        >>> statuses = WeightedChoice({
        ...     "completed": 60,
        ...     "processing": 20,
        ...     "pending": 15,
        ...     "cancelled": 5,
        ... })
        >>> # Generate 100 statuses with this distribution
        >>> values = statuses.generate(fake, 100)
    """

    def __init__(self, weights: dict[str, int]) -> None:
        """Initialize with weight mapping.

        Args:
            weights: Mapping of values to their relative weights.
                     Weights are relative, not percentages.

        Example:
            >>> wc = WeightedChoice({"a": 3, "b": 1})  # 75% a, 25% b
        """
        self.values = list(weights.keys())
        self.weights = list(weights.values())
        total = sum(self.weights)
        self.probabilities = [w / total for w in self.weights]

    def generate(self, fake: Any, count: int) -> list[str]:
        """Generate weighted random values using Faker.

        Args:
            fake: Faker instance
            count: Number of values to generate

        Returns:
            List of randomly selected values following the weight distribution
        """
        return [fake.random_element(elements=self._build_weighted_elements()) for _ in range(count)]

    def _build_weighted_elements(self) -> OrderedDict[str, float]:
        """Build elements OrderedDict for Faker's random_element."""
        return OrderedDict(zip(self.values, self.probabilities, strict=True))


# Common weight distributions for reuse
STATUS_WEIGHTS: dict[str, int] = {
    "completed": 60,
    "processing": 20,
    "pending": 15,
    "cancelled": 5,
}

REGION_WEIGHTS: dict[str, int] = {
    "north": 25,
    "south": 25,
    "east": 25,
    "west": 25,
}

PLAN_WEIGHTS: dict[str, int] = {
    "free": 50,
    "starter": 25,
    "pro": 20,
    "enterprise": 5,
}

SUBSCRIPTION_STATUS_WEIGHTS: dict[str, int] = {
    "active": 70,
    "trial": 15,
    "churned": 10,
    "cancelled": 3,
    "past_due": 2,
}
