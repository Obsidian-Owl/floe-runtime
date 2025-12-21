"""Synthetic data generators.

This module provides generators for creating realistic test data:
- EcommerceGenerator: Orders, Customers, Products
- SaaSGenerator: Users, Events, Subscriptions

All generators support:
- Deterministic seeding for reproducible tests
- Weighted distributions for realistic data patterns
- Batch generation for memory efficiency
- PyArrow output for Iceberg compatibility
"""

from __future__ import annotations

from floe_synthetic.generators.base import DataGenerator
from floe_synthetic.generators.ecommerce import EcommerceGenerator
from floe_synthetic.generators.saas import SaaSGenerator

__all__ = [
    "DataGenerator",
    "EcommerceGenerator",
    "SaaSGenerator",
]
