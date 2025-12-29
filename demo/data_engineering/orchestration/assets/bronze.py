"""Bronze layer assets - Synthetic data generation using floe-synthetic.

The bronze layer in the medallion architecture represents raw, unprocessed data.
These assets use the floe-synthetic library to generate realistic e-commerce data
and load it into Iceberg tables via the Polaris catalog.

Per medallion architecture best practices:
- Bronze layer = Raw data (single source of truth)
- Naming: raw_* tables in demo namespace
- One-time generation: These assets create the foundation data

Architecture:
- Uses EcommerceGeneratorResource (from floe-synthetic package)
- Uses IcebergLoaderResource (from floe-synthetic package)
- Writes to Polaris catalog → Iceberg tables → S3 storage
- Observability via ObservabilityOrchestrator (traces + lineage)
"""

from __future__ import annotations

from typing import Any

from dagster import asset

from floe_dagster.observability import ObservabilityOrchestrator
from floe_synthetic.dagster.resources import (
    EcommerceGeneratorResource,
    IcebergLoaderResource,
)


@asset(
    key_prefix=["bronze"],
    name="raw_customers",
    group_name="bronze",
    description="Raw customer data (bronze layer) - 1000 synthetic customers",
    compute_kind="synthetic",
)
def raw_customers(
    context,
    ecommerce_generator: EcommerceGeneratorResource,
    iceberg_loader: IcebergLoaderResource,
) -> dict[str, Any]:
    """Generate and load raw customer data.

    Args:
        context: Dagster execution context
        ecommerce_generator: Synthetic data generator
        iceberg_loader: Iceberg table loader

    Returns:
        Dictionary with row count and snapshot ID
    """
    orchestrator: ObservabilityOrchestrator = context.resources._floe_observability_orchestrator

    with orchestrator.asset_run(
        context=context,
        asset_key="bronze/raw_customers",
        compute_kind="synthetic",
        group_name="bronze",
    ):
        generator = ecommerce_generator.get_generator()
        loader = iceberg_loader.get_loader()

        # Generate 1000 customers
        customers = generator.generate_customers(count=1000)
        context.log.info(f"Generated {len(customers)} customers")

        # Load to Iceberg table
        result = loader.overwrite("demo.raw_customers", customers)
        context.log.info(
            f"Loaded {result.rows_loaded} rows to demo.raw_customers, "
            f"snapshot: {result.snapshot_id}"
        )

        return {"rows": result.rows_loaded, "snapshot_id": result.snapshot_id}


@asset(
    key_prefix=["bronze"],
    name="raw_products",
    group_name="bronze",
    description="Raw product data (bronze layer) - 100 synthetic products",
    compute_kind="synthetic",
)
def raw_products(
    context,
    ecommerce_generator: EcommerceGeneratorResource,
    iceberg_loader: IcebergLoaderResource,
) -> dict[str, Any]:
    """Generate and load raw product data.

    Args:
        context: Dagster execution context
        ecommerce_generator: Synthetic data generator
        iceberg_loader: Iceberg table loader

    Returns:
        Dictionary with row count and snapshot ID
    """
    orchestrator: ObservabilityOrchestrator = context.resources._floe_observability_orchestrator

    with orchestrator.asset_run(
        context=context,
        asset_key="bronze/raw_products",
        compute_kind="synthetic",
        group_name="bronze",
    ):
        generator = ecommerce_generator.get_generator()
        loader = iceberg_loader.get_loader()

        # Generate 100 products
        products = generator.generate_products(count=100)
        context.log.info(f"Generated {len(products)} products")

        # Load to Iceberg table
        result = loader.overwrite("demo.raw_products", products)
        context.log.info(
            f"Loaded {result.rows_loaded} rows to demo.raw_products, snapshot: {result.snapshot_id}"
        )

        return {"rows": result.rows_loaded, "snapshot_id": result.snapshot_id}


@asset(
    key_prefix=["bronze"],
    name="raw_orders",
    group_name="bronze",
    description="Raw order data (bronze layer) - 5000 synthetic orders",
    compute_kind="synthetic",
    deps=[raw_customers, raw_products],
)
def raw_orders(
    context,
    ecommerce_generator: EcommerceGeneratorResource,
    iceberg_loader: IcebergLoaderResource,
) -> dict[str, Any]:
    """Generate and load raw order data.

    Args:
        context: Dagster execution context
        ecommerce_generator: Synthetic data generator
        iceberg_loader: Iceberg table loader

    Returns:
        Dictionary with row count and snapshot ID
    """
    orchestrator: ObservabilityOrchestrator = context.resources._floe_observability_orchestrator

    with orchestrator.asset_run(
        context=context,
        asset_key="bronze/raw_orders",
        compute_kind="synthetic",
        group_name="bronze",
    ):
        generator = ecommerce_generator.get_generator()
        loader = iceberg_loader.get_loader()

        # Generate 5000 orders (depends on customers existing)
        orders = generator.generate_orders(count=5000)
        context.log.info(f"Generated {len(orders)} orders")

        # Load to Iceberg table
        result = loader.overwrite("demo.raw_orders", orders)
        context.log.info(
            f"Loaded {result.rows_loaded} rows to demo.raw_orders, snapshot: {result.snapshot_id}"
        )

        return {"rows": result.rows_loaded, "snapshot_id": result.snapshot_id}


@asset(
    key_prefix=["bronze"],
    name="raw_order_items",
    group_name="bronze",
    description="Raw order item data (bronze layer) - ~15000 synthetic line items",
    compute_kind="synthetic",
    deps=[raw_orders],
)
def raw_order_items(
    context,
    ecommerce_generator: EcommerceGeneratorResource,
    iceberg_loader: IcebergLoaderResource,
) -> dict[str, Any]:
    """Generate and load raw order item data.

    Args:
        context: Dagster execution context
        ecommerce_generator: Synthetic data generator
        iceberg_loader: Iceberg table loader

    Returns:
        Dictionary with row count and snapshot ID
    """
    orchestrator: ObservabilityOrchestrator = context.resources._floe_observability_orchestrator

    with orchestrator.asset_run(
        context=context,
        asset_key="bronze/raw_order_items",
        compute_kind="synthetic",
        group_name="bronze",
    ):
        generator = ecommerce_generator.get_generator()
        loader = iceberg_loader.get_loader()

        # Generate order items (depends on orders existing)
        order_items = generator.generate_order_items()
        context.log.info(f"Generated {len(order_items)} order items")

        # Load to Iceberg table
        result = loader.overwrite("demo.raw_order_items", order_items)
        context.log.info(
            f"Loaded {result.rows_loaded} rows to demo.raw_order_items, "
            f"snapshot: {result.snapshot_id}"
        )

        return {"rows": result.rows_loaded, "snapshot_id": result.snapshot_id}
