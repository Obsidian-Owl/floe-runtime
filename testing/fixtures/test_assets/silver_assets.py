"""Silver layer test assets.

These assets simulate a silver layer with cleaned/transformed data.
Used for integration testing of asset module auto-discovery.
"""

from __future__ import annotations

from dagster import asset


@asset
def silver_customer_metrics() -> dict[str, int]:
    """Silver layer customer metrics asset."""
    return {"rows": 100, "columns": 10}


@asset
def silver_order_summary() -> dict[str, int]:
    """Silver layer order summary asset."""
    return {"rows": 500, "columns": 12}
