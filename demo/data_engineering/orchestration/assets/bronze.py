"""Bronze layer assets - Synthetic data generation using floe-synthetic.

The bronze layer in the medallion architecture represents raw, unprocessed data.
These assets use the floe-synthetic library to generate realistic e-commerce data
and load it into Iceberg tables via the Polaris catalog.

Per medallion architecture best practices:
- Bronze layer = Raw data (single source of truth)
- Layer-aware writes using catalog.write_to_layer() (v1.2.0)
- No hardcoded namespaces - layer config in platform.yaml
- One-time generation: These assets create the foundation data

Architecture:
- Uses EcommerceGeneratorResource (from floe-synthetic package)
- Uses CatalogResource with layer-aware writes (declarative API)
- Writes to Polaris catalog → Iceberg tables → S3 storage
- Observability via ObservabilityOrchestrator (traces + lineage)
"""

from __future__ import annotations

from typing import Any

from dagster import asset
from floe_dagster.observability import ObservabilityOrchestrator


@asset(
    key_prefix=["bronze"],
    name="raw_customers",
    group_name="bronze",
    description="Raw customer data (bronze layer) - 1000 synthetic customers",
    compute_kind="synthetic",
    required_resource_keys={"ecommerce_generator", "catalog", "floe_observability_orchestrator"},
)
def raw_customers(
    context,
) -> dict[str, Any]:
    """Generate and load raw customer data using layer-aware writes.

    Uses catalog.write_to_layer() for declarative writes - no hardcoded namespaces.
    The target namespace (e.g., demo_catalog.bronze) is resolved from platform.yaml.

    Args:
        context: Dagster execution context

    Returns:
        Dictionary with row count and snapshot ID
    """
    ecommerce_generator = context.resources.ecommerce_generator
    catalog = context.resources.catalog
    orchestrator: ObservabilityOrchestrator = context.resources.floe_observability_orchestrator

    with orchestrator.asset_run(
        "bronze/raw_customers",
        outputs=["demo_catalog.bronze.raw_customers"],
        attributes={"compute_kind": "synthetic", "group_name": "bronze"},
    ):
        generator = ecommerce_generator.get_generator()

        # Generate 1000 customers
        customers = generator.generate_customers(count=1000)
        context.log.info(f"Generated {customers.num_rows} customers")

        # Layer-aware write - namespace resolved from platform.yaml
        snapshot = catalog.write_to_layer("bronze", "raw_customers", customers)
        context.log.info(
            f"Loaded {customers.num_rows} rows to bronze layer, snapshot: {snapshot.snapshot_id}"
        )

        return {"rows": customers.num_rows, "snapshot_id": snapshot.snapshot_id}


@asset(
    key_prefix=["bronze"],
    name="raw_products",
    group_name="bronze",
    description="Raw product data (bronze layer) - 100 synthetic products",
    compute_kind="synthetic",
    required_resource_keys={"ecommerce_generator", "catalog", "floe_observability_orchestrator"},
)
def raw_products(
    context,
) -> dict[str, Any]:
    """Generate and load raw product data using layer-aware writes.

    Args:
        context: Dagster execution context

    Returns:
        Dictionary with row count and snapshot ID
    """
    ecommerce_generator = context.resources.ecommerce_generator
    catalog = context.resources.catalog
    orchestrator: ObservabilityOrchestrator = context.resources.floe_observability_orchestrator

    with orchestrator.asset_run(
        "bronze/raw_products",
        outputs=["demo_catalog.bronze.raw_products"],
        attributes={"compute_kind": "synthetic", "group_name": "bronze"},
    ):
        generator = ecommerce_generator.get_generator()

        # Generate 100 products
        products = generator.generate_products(count=100)
        context.log.info(f"Generated {products.num_rows} products")

        # Layer-aware write - namespace resolved from platform.yaml
        snapshot = catalog.write_to_layer("bronze", "raw_products", products)
        context.log.info(
            f"Loaded {products.num_rows} rows to bronze layer, snapshot: {snapshot.snapshot_id}"
        )

        return {"rows": products.num_rows, "snapshot_id": snapshot.snapshot_id}


@asset(
    key_prefix=["bronze"],
    name="raw_orders",
    group_name="bronze",
    description="Raw order data (bronze layer) - 5000 synthetic orders",
    compute_kind="synthetic",
    deps=[raw_customers, raw_products],
    required_resource_keys={"ecommerce_generator", "catalog", "floe_observability_orchestrator"},
)
def raw_orders(
    context,
) -> dict[str, Any]:
    """Generate and load raw order data using layer-aware writes.

    Args:
        context: Dagster execution context

    Returns:
        Dictionary with row count and snapshot ID
    """
    ecommerce_generator = context.resources.ecommerce_generator
    catalog = context.resources.catalog
    orchestrator: ObservabilityOrchestrator = context.resources.floe_observability_orchestrator

    with orchestrator.asset_run(
        "bronze/raw_orders",
        outputs=["demo_catalog.bronze.raw_orders"],
        attributes={"compute_kind": "synthetic", "group_name": "bronze"},
    ):
        generator = ecommerce_generator.get_generator()

        # Generate 5000 orders (depends on customers existing)
        orders = generator.generate_orders(count=5000)
        context.log.info(f"Generated {orders.num_rows} orders")

        # Layer-aware write - namespace resolved from platform.yaml
        snapshot = catalog.write_to_layer("bronze", "raw_orders", orders)
        context.log.info(
            f"Loaded {orders.num_rows} rows to bronze layer, snapshot: {snapshot.snapshot_id}"
        )

        return {"rows": orders.num_rows, "snapshot_id": snapshot.snapshot_id}


@asset(
    key_prefix=["bronze"],
    name="raw_order_items",
    group_name="bronze",
    description="Raw order item data (bronze layer) - ~15000 synthetic line items",
    compute_kind="synthetic",
    deps=[raw_orders],
    required_resource_keys={"ecommerce_generator", "catalog", "floe_observability_orchestrator"},
)
def raw_order_items(
    context,
) -> dict[str, Any]:
    """Generate and load raw order item data using layer-aware writes.

    Args:
        context: Dagster execution context

    Returns:
        Dictionary with row count and snapshot ID
    """
    ecommerce_generator = context.resources.ecommerce_generator
    catalog = context.resources.catalog
    orchestrator: ObservabilityOrchestrator = context.resources.floe_observability_orchestrator

    with orchestrator.asset_run(
        "bronze/raw_order_items",
        outputs=["demo_catalog.bronze.raw_order_items"],
        attributes={"compute_kind": "synthetic", "group_name": "bronze"},
    ):
        generator = ecommerce_generator.get_generator()

        # Generate order items (depends on orders existing)
        order_items = generator.generate_order_items()
        context.log.info(f"Generated {order_items.num_rows} order items")

        # Layer-aware write - namespace resolved from platform.yaml
        snapshot = catalog.write_to_layer("bronze", "raw_order_items", order_items)
        context.log.info(
            f"Loaded {order_items.num_rows} rows to bronze layer, snapshot: {snapshot.snapshot_id}"
        )

        return {"rows": order_items.num_rows, "snapshot_id": snapshot.snapshot_id}
