"""Dagster assets for scheduled synthetic data generation.

This module provides Dagster assets and resources for generating
synthetic data on a schedule, useful for demo environments and
showcasing live transformations.

Note: Requires the 'dagster' optional dependency.
"""

from __future__ import annotations

try:
    from floe_synthetic.dagster.assets import (
        daily_ecommerce_orders,
        daily_saas_events,
    )
    from floe_synthetic.dagster.resources import (
        EcommerceGeneratorResource,
        IcebergLoaderResource,
        SaaSGeneratorResource,
    )

    __all__ = [
        "daily_ecommerce_orders",
        "daily_saas_events",
        "EcommerceGeneratorResource",
        "SaaSGeneratorResource",
        "IcebergLoaderResource",
    ]
except ImportError:
    # Dagster not installed
    __all__ = []
