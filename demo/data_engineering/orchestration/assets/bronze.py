"""Bronze layer assets - Load from raw tables to Iceberg.

These assets demonstrate the simplicity of floe-runtime:
- Simple @floe_asset decorator (batteries-included observability)
- CatalogResource for Iceberg operations
- No infrastructure configuration (loaded from platform.yaml)
- Auto-discovered via orchestration.asset_modules in floe.yaml
"""

from typing import Any

from dagster import AssetExecutionContext

from demo.data_engineering.orchestration.constants import (
    TABLE_BRONZE_CUSTOMERS,
    TABLE_BRONZE_ORDER_ITEMS,
    TABLE_BRONZE_ORDERS,
    TABLE_BRONZE_PRODUCTS,
    TABLE_RAW_CUSTOMERS,
    TABLE_RAW_ORDER_ITEMS,
    TABLE_RAW_ORDERS,
    TABLE_RAW_PRODUCTS,
)
from floe_dagster import floe_asset
from floe_dagster.resources import CatalogResource


@floe_asset(
    group_name="bronze",
    description="Load customer data from raw layer to bronze",
    inputs=[TABLE_RAW_CUSTOMERS],
    outputs=[TABLE_BRONZE_CUSTOMERS],
    compute_kind="python",
)
def bronze_customers(
    context: AssetExecutionContext,
    catalog: CatalogResource,
) -> dict[str, Any]:
    """Load customer data from raw to bronze layer."""
    context.log.info("Loading customers from %s", TABLE_RAW_CUSTOMERS)
    raw_data = catalog.read_table(TABLE_RAW_CUSTOMERS)
    snapshot = catalog.write_table(TABLE_BRONZE_CUSTOMERS, raw_data)
    return {"rows": raw_data.num_rows, "snapshot_id": snapshot.snapshot_id}


@floe_asset(
    group_name="bronze",
    description="Load product data from raw layer to bronze",
    inputs=[TABLE_RAW_PRODUCTS],
    outputs=[TABLE_BRONZE_PRODUCTS],
    compute_kind="python",
)
def bronze_products(
    context: AssetExecutionContext,
    catalog: CatalogResource,
) -> dict[str, Any]:
    """Load product data from raw to bronze layer."""
    context.log.info("Loading products from %s", TABLE_RAW_PRODUCTS)
    raw_data = catalog.read_table(TABLE_RAW_PRODUCTS)
    snapshot = catalog.write_table(TABLE_BRONZE_PRODUCTS, raw_data)
    return {"rows": raw_data.num_rows, "snapshot_id": snapshot.snapshot_id}


@floe_asset(
    group_name="bronze",
    description="Load order data from raw layer to bronze",
    inputs=[TABLE_RAW_ORDERS],
    outputs=[TABLE_BRONZE_ORDERS],
    compute_kind="python",
    deps=["bronze_customers"],
)
def bronze_orders(
    context: AssetExecutionContext,
    catalog: CatalogResource,
) -> dict[str, Any]:
    """Load order data from raw to bronze layer."""
    context.log.info("Loading orders from %s", TABLE_RAW_ORDERS)
    raw_data = catalog.read_table(TABLE_RAW_ORDERS)
    snapshot = catalog.write_table(TABLE_BRONZE_ORDERS, raw_data)
    return {"rows": raw_data.num_rows, "snapshot_id": snapshot.snapshot_id}


@floe_asset(
    group_name="bronze",
    description="Load order item data from raw layer to bronze",
    inputs=[TABLE_RAW_ORDER_ITEMS],
    outputs=[TABLE_BRONZE_ORDER_ITEMS],
    compute_kind="python",
    deps=["bronze_orders", "bronze_products"],
)
def bronze_order_items(
    context: AssetExecutionContext,
    catalog: CatalogResource,
) -> dict[str, Any]:
    """Load order item data from raw to bronze layer."""
    context.log.info("Loading order items from %s", TABLE_RAW_ORDER_ITEMS)
    raw_data = catalog.read_table(TABLE_RAW_ORDER_ITEMS)
    snapshot = catalog.write_table(TABLE_BRONZE_ORDER_ITEMS, raw_data)
    return {"rows": raw_data.num_rows, "snapshot_id": snapshot.snapshot_id}
