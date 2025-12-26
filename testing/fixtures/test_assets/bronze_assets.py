"""Bronze layer test assets.

These assets simulate a bronze layer ingesting raw data.
Used for integration testing of asset module auto-discovery.
"""

from __future__ import annotations

from dagster import asset


@asset
def bronze_customers() -> dict[str, int]:
    """Bronze layer customers asset."""
    return {"rows": 100, "columns": 5}


@asset
def bronze_orders() -> dict[str, int]:
    """Bronze layer orders asset."""
    return {"rows": 500, "columns": 8}


@asset
def bronze_products() -> dict[str, int]:
    """Bronze layer products asset."""
    return {"rows": 50, "columns": 3}
