"""Data quality defects module for synthetic data generation.

This module provides configurable data quality scenarios for dbt validation demos:
- Null injection: Inject NULL values into specified columns
- Duplicate injection: Add duplicate rows to test deduplication
- Late-arriving data: Backdate timestamps to test late arrival handling

Covers: 007-FR-027b (configurable data quality scenarios)

Example:
    >>> from floe_synthetic.quality import DefectConfig, QualityDefectInjector
    >>> from floe_synthetic.generators.ecommerce import EcommerceGenerator
    >>>
    >>> # Generate clean data
    >>> gen = EcommerceGenerator(seed=42)
    >>> orders = gen.generate_orders(1000)
    >>>
    >>> # Configure defects: 5% nulls, 2% duplicates, 1% late arrivals
    >>> config = DefectConfig(
    ...     null_rate=0.05,
    ...     null_columns=["email", "region"],
    ...     duplicate_rate=0.02,
    ...     late_arrival_rate=0.01,
    ...     timestamp_column="created_at",
    ... )
    >>>
    >>> # Inject defects
    >>> injector = QualityDefectInjector(seed=42, config=config)
    >>> dirty_orders = injector.apply(orders)
"""

from __future__ import annotations

from floe_synthetic.quality.defects import DefectConfig, QualityDefectInjector

__all__ = [
    "DefectConfig",
    "QualityDefectInjector",
]
