"""Bronze layer assets - Raw synthetic data created via external tooling.

The bronze layer in the medallion architecture represents raw, unprocessed data.
In this demo, synthetic raw data is generated via the seed_iceberg_tables.py script
and stored as demo.raw_* tables in the Polaris catalog.

Per medallion architecture best practices:
- Bronze layer = Raw data (single source of truth)
- No transformation, stored "as-is" from source
- Naming: raw_* tables ARE the bronze layer

These assets serve as external table declarations for Dagster's lineage tracking.
The actual data is materialized via scripts/seed_iceberg_tables.py.
"""

from dagster import AssetExecutionContext, asset

from floe_dagster.resources import CatalogResource

TABLE_RAW_CUSTOMERS = "demo.raw_customers"
TABLE_RAW_PRODUCTS = "demo.raw_products"
TABLE_RAW_ORDERS = "demo.raw_orders"
TABLE_RAW_ORDER_ITEMS = "demo.raw_order_items"


@asset(
    key_prefix=["bronze"],
    name="raw_customers",
    group_name="bronze",
    description="Raw customer data (bronze layer) - 1000 synthetic customers",
    compute_kind="synthetic",
)
def raw_customers(context: AssetExecutionContext, catalog: CatalogResource) -> dict:
    """Bronze layer: Raw customer data from synthetic generation.

    Created externally via seed_iceberg_tables.py script.
    This asset declaration enables Dagster lineage tracking.
    """
    table = catalog.read_table(TABLE_RAW_CUSTOMERS)
    context.log.info(f"Bronze layer table validated: {TABLE_RAW_CUSTOMERS}")
    return {"rows": table.num_rows, "table": TABLE_RAW_CUSTOMERS}


@asset(
    key_prefix=["bronze"],
    name="raw_products",
    group_name="bronze",
    description="Raw product data (bronze layer) - 100 synthetic products",
    compute_kind="synthetic",
)
def raw_products(context: AssetExecutionContext, catalog: CatalogResource) -> dict:
    """Bronze layer: Raw product data from synthetic generation.

    Created externally via seed_iceberg_tables.py script.
    This asset declaration enables Dagster lineage tracking.
    """
    table = catalog.read_table(TABLE_RAW_PRODUCTS)
    context.log.info(f"Bronze layer table validated: {TABLE_RAW_PRODUCTS}")
    return {"rows": table.num_rows, "table": TABLE_RAW_PRODUCTS}


@asset(
    key_prefix=["bronze"],
    name="raw_orders",
    group_name="bronze",
    description="Raw order data (bronze layer) - 5000 synthetic orders",
    compute_kind="synthetic",
    deps=[raw_customers],
)
def raw_orders(context: AssetExecutionContext, catalog: CatalogResource) -> dict:
    """Bronze layer: Raw order data from synthetic generation.

    Created externally via seed_iceberg_tables.py script.
    This asset declaration enables Dagster lineage tracking.
    """
    table = catalog.read_table(TABLE_RAW_ORDERS)
    context.log.info(f"Bronze layer table validated: {TABLE_RAW_ORDERS}")
    return {"rows": table.num_rows, "table": TABLE_RAW_ORDERS}


@asset(
    key_prefix=["bronze"],
    name="raw_order_items",
    group_name="bronze",
    description="Raw order item data (bronze layer) - 10000 synthetic line items",
    compute_kind="synthetic",
    deps=[raw_orders, raw_products],
)
def raw_order_items(context: AssetExecutionContext, catalog: CatalogResource) -> dict:
    """Bronze layer: Raw order item data from synthetic generation.

    Created externally via seed_iceberg_tables.py script.
    This asset declaration enables Dagster lineage tracking.
    """
    table = catalog.read_table(TABLE_RAW_ORDER_ITEMS)
    context.log.info(f"Bronze layer table validated: {TABLE_RAW_ORDER_ITEMS}")
    return {"rows": table.num_rows, "table": TABLE_RAW_ORDER_ITEMS}
