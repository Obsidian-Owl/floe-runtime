"""Synthetic data generation for floe-runtime.

This package provides infrastructure for generating high-quality synthetic data
to support E2E testing, demo environments, and live transformation showcases.

Key Components:
- generators: Faker-based data generators for various schemas
- schemas: Pydantic models defining data structures
- loaders: Data loaders for Iceberg tables
- distributions: Helpers for weighted and temporal distributions
- dagster: Dagster assets for scheduled data generation
- quality: Data quality defect injection for dbt validation demos

Example:
    >>> from floe_synthetic.generators.ecommerce import EcommerceGenerator
    >>> from floe_synthetic.loaders.iceberg import IcebergLoader
    >>>
    >>> generator = EcommerceGenerator(seed=42)
    >>> orders = generator.generate_orders(count=1000)
    >>> loader = IcebergLoader(catalog_uri="http://polaris:8181/api/catalog")
    >>> loader.append("default.orders", orders)

Example with quality defects:
    >>> from floe_synthetic.quality import DefectConfig, QualityDefectInjector
    >>>
    >>> config = DefectConfig(null_rate=0.05, duplicate_rate=0.02)
    >>> injector = QualityDefectInjector(seed=42, config=config)
    >>> dirty_orders = injector.apply(orders)
"""

from __future__ import annotations

__version__ = "0.1.0"
