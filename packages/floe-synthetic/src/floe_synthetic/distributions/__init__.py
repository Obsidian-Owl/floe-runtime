"""Distribution helpers for synthetic data generation.

This module provides utilities for creating realistic data distributions:
- Weighted choices for categorical data
- Temporal patterns for time-series data
"""

from __future__ import annotations

from floe_synthetic.distributions.temporal import TemporalDistribution
from floe_synthetic.distributions.weighted import WeightedDistribution

__all__ = ["WeightedDistribution", "TemporalDistribution"]
