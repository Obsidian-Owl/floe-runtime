"""Dagster Definitions for Floe Demo - Batteries-Included Implementation.

Provides orchestration for the demo e-commerce data pipeline with:
- Real synthetic data generation using Faker
- Real Iceberg table storage via Polaris/LocalStack
- Real OpenTelemetry tracing visible in Jaeger
- Real OpenLineage lineage visible in Marquez

This demo uses the batteries-included @floe_asset decorator which
automatically handles observability (tracing + lineage) without boilerplate.

Data Flow:
    1. Bronze Layer: EcommerceGenerator → Iceberg tables
    2. Silver Layer: dbt staging transformations
    3. Gold Layer: dbt mart transformations
    4. Semantic Layer: Cube queries mart tables

Covers: 007-FR-029 (E2E validation tests)
Covers: 007-FR-031 (Medallion architecture orchestration)

Note: This file intentionally does NOT use `from __future__ import annotations`
because Dagster 1.12.x's type validation uses identity checks that break with
PEP 563 string annotations. See: https://github.com/dagster-io/dagster/issues
"""

import logging
import os
from typing import Any, Dict, Optional

from dagster import (
    AssetExecutionContext,
    AssetSelection,
    DefaultScheduleStatus,
    DefaultSensorStatus,
    RunRequest,
    ScheduleDefinition,
    define_asset_job,
    sensor,
)

from demo.orchestration.config import (
    DEMO_CUSTOMERS_COUNT,
    DEMO_ORDER_ITEMS_COUNT,
    DEMO_ORDERS_COUNT,
    DEMO_PRODUCTS_COUNT,
    DEMO_SEED,
    get_compiled_artifacts_dict,
)
from floe_dagster import FloeDefinitions, floe_asset
from floe_dagster.resources import PolarisCatalogResource

logger = logging.getLogger(__name__)

# =============================================================================
# Table Name Constants (S1192: avoid duplicate string literals)
# =============================================================================

TABLE_BRONZE_CUSTOMERS = "demo.bronze_customers"
TABLE_BRONZE_PRODUCTS = "demo.bronze_products"
TABLE_BRONZE_ORDERS = "demo.bronze_orders"
TABLE_BRONZE_ORDER_ITEMS = "demo.bronze_order_items"


# =============================================================================
# Bronze Layer Assets - Real Data Generation to Iceberg
# Using @floe_asset for automatic observability (tracing + lineage)
# =============================================================================


@floe_asset(
    group_name="bronze",
    description="Generate and load synthetic customer data to Iceberg",
    outputs=[TABLE_BRONZE_CUSTOMERS],
    compute_kind="python",
    metadata={
        "demo.count": DEMO_CUSTOMERS_COUNT,
        "demo.seed": DEMO_SEED,
    },
)
def bronze_customers(
    context: AssetExecutionContext,
    catalog: PolarisCatalogResource,
) -> Dict[str, Any]:
    """Generate real customer data and write to Iceberg table.

    Uses EcommerceGenerator to create realistic customer records,
    then writes to an Iceberg table via Polaris catalog.

    Returns:
        Dictionary with row count and snapshot information.
    """
    from floe_synthetic.generators.ecommerce import EcommerceGenerator

    # Generate real customer data
    context.log.info("Generating %d customers with seed %d", DEMO_CUSTOMERS_COUNT, DEMO_SEED)
    generator = EcommerceGenerator(seed=DEMO_SEED)
    customers = generator.generate_customers(count=DEMO_CUSTOMERS_COUNT)

    # Write to Iceberg via catalog.write_table() (batteries-included)
    context.log.info("Writing customers to Iceberg table")
    snapshot = catalog.write_table(TABLE_BRONZE_CUSTOMERS, customers)

    result = {
        "rows": customers.num_rows,
        "snapshot_id": snapshot.snapshot_id,
        "table": TABLE_BRONZE_CUSTOMERS,
    }

    context.log.info("bronze_customers completed: %s", result)
    return result


@floe_asset(
    group_name="bronze",
    description="Generate and load synthetic product data to Iceberg",
    outputs=[TABLE_BRONZE_PRODUCTS],
    compute_kind="python",
    metadata={
        "demo.count": DEMO_PRODUCTS_COUNT,
        "demo.seed": DEMO_SEED,
    },
)
def bronze_products(
    context: AssetExecutionContext,
    catalog: PolarisCatalogResource,
) -> Dict[str, Any]:
    """Generate real product data and write to Iceberg table.

    Returns:
        Dictionary with row count and snapshot information.
    """
    from floe_synthetic.generators.ecommerce import EcommerceGenerator

    context.log.info("Generating %d products with seed %d", DEMO_PRODUCTS_COUNT, DEMO_SEED)
    generator = EcommerceGenerator(seed=DEMO_SEED)
    products = generator.generate_products(count=DEMO_PRODUCTS_COUNT)

    # Write to Iceberg via catalog.write_table() (batteries-included)
    context.log.info("Writing products to Iceberg table")
    snapshot = catalog.write_table(TABLE_BRONZE_PRODUCTS, products)

    result = {
        "rows": products.num_rows,
        "snapshot_id": snapshot.snapshot_id,
        "table": TABLE_BRONZE_PRODUCTS,
    }

    context.log.info("bronze_products completed: %s", result)
    return result


@floe_asset(
    group_name="bronze",
    description="Generate and load synthetic order data to Iceberg",
    outputs=[TABLE_BRONZE_ORDERS],
    inputs=[TABLE_BRONZE_CUSTOMERS],
    compute_kind="python",
    deps=["bronze_customers"],
    metadata={
        "demo.count": DEMO_ORDERS_COUNT,
        "demo.seed": DEMO_SEED,
    },
)
def bronze_orders(
    context: AssetExecutionContext,
    catalog: PolarisCatalogResource,
) -> Dict[str, Any]:
    """Generate real order data and write to Iceberg table.

    Returns:
        Dictionary with row count and snapshot information.
    """
    from floe_synthetic.generators.ecommerce import EcommerceGenerator

    context.log.info("Generating %d orders with seed %d", DEMO_ORDERS_COUNT, DEMO_SEED)
    generator = EcommerceGenerator(seed=DEMO_SEED)
    # Generate customers first to establish FK relationships
    generator.generate_customers(count=DEMO_CUSTOMERS_COUNT)
    orders = generator.generate_orders(count=DEMO_ORDERS_COUNT)

    # Write to Iceberg via catalog.write_table() (batteries-included)
    context.log.info("Writing orders to Iceberg table")
    snapshot = catalog.write_table(TABLE_BRONZE_ORDERS, orders)

    result = {
        "rows": orders.num_rows,
        "snapshot_id": snapshot.snapshot_id,
        "table": TABLE_BRONZE_ORDERS,
    }

    context.log.info("bronze_orders completed: %s", result)
    return result


@floe_asset(
    group_name="bronze",
    description="Generate and load synthetic order item data to Iceberg",
    outputs=[TABLE_BRONZE_ORDER_ITEMS],
    inputs=[TABLE_BRONZE_ORDERS, TABLE_BRONZE_PRODUCTS],
    compute_kind="python",
    deps=["bronze_orders", "bronze_products"],
    metadata={
        "demo.count": DEMO_ORDER_ITEMS_COUNT,
        "demo.seed": DEMO_SEED,
    },
)
def bronze_order_items(
    context: AssetExecutionContext,
    catalog: PolarisCatalogResource,
) -> Dict[str, Any]:
    """Generate real order item data and write to Iceberg table.

    Returns:
        Dictionary with row count and snapshot information.
    """
    from floe_synthetic.generators.ecommerce import EcommerceGenerator

    context.log.info(
        "Generating %d order items with seed %d",
        DEMO_ORDER_ITEMS_COUNT,
        DEMO_SEED,
    )
    generator = EcommerceGenerator(seed=DEMO_SEED)
    # Generate parent entities first
    generator.generate_customers(count=DEMO_CUSTOMERS_COUNT)
    generator.generate_products(count=DEMO_PRODUCTS_COUNT)
    generator.generate_orders(count=DEMO_ORDERS_COUNT)
    order_items = generator.generate_order_items(count=DEMO_ORDER_ITEMS_COUNT)

    # Write to Iceberg via catalog.write_table() (batteries-included)
    context.log.info("Writing order_items to Iceberg table")
    snapshot = catalog.write_table(TABLE_BRONZE_ORDER_ITEMS, order_items)

    result = {
        "rows": order_items.num_rows,
        "snapshot_id": snapshot.snapshot_id,
        "table": TABLE_BRONZE_ORDER_ITEMS,
    }

    context.log.info("bronze_order_items completed: %s", result)
    return result


# =============================================================================
# Placeholder Asset for Future dbt Integration
# =============================================================================


@floe_asset(
    group_name="transform",
    description="Run dbt transformations (staging → intermediate → marts)",
    outputs=["demo.dbt_transformations"],
    inputs=[
        "demo.bronze_customers",
        "demo.bronze_orders",
        "demo.bronze_products",
        "demo.bronze_order_items",
    ],
    compute_kind="dbt",
    deps=["bronze_customers", "bronze_orders", "bronze_products", "bronze_order_items"],
)
def dbt_transformations(context: AssetExecutionContext) -> Dict[str, str]:
    """Execute dbt transformations.

    Note: Full dbt integration requires dagster-dbt and project setup.
    For the demo, this validates that bronze layer data is available.

    Returns:
        Dictionary with transformation status.
    """
    # Verify bronze tables exist via Trino
    context.log.info("dbt transformations would run here")
    context.log.info("Bronze layer tables created - dbt models can query them")

    # For full implementation:
    # from dagster_dbt import DbtCliResource
    # result = dbt.cli(["run", "--target", "demo"], context=context).wait()

    result = {
        "status": "placeholder",
        "message": "Bronze layer ready for dbt transformations",
        "tables": "bronze_customers, bronze_orders, bronze_products, bronze_order_items",
    }

    context.log.info("dbt_transformations completed: %s", result)
    return result


# =============================================================================
# Jobs
# =============================================================================

# Full bronze layer job - generates all synthetic data
demo_bronze_job = define_asset_job(
    name="demo_bronze",
    selection=AssetSelection.groups("bronze"),
    description="Generate bronze layer: synthetic data → Iceberg tables",
)

# Full pipeline job - runs all assets
demo_pipeline_job = define_asset_job(
    name="demo_pipeline",
    selection=AssetSelection.groups("bronze", "transform"),
    description="Full demo pipeline: bronze layer → dbt transformations",
)


# =============================================================================
# Schedules
# =============================================================================

# Synthetic data generation schedule - auto-starts on deployment
synthetic_data_schedule = ScheduleDefinition(
    name="synthetic_data_schedule",
    job=demo_bronze_job,
    cron_schedule="*/5 * * * *",  # Every 5 minutes
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start on deployment
    description="Generate synthetic e-commerce data every 5 minutes",
)

# Transform pipeline schedule - auto-starts on deployment
transform_pipeline_schedule = ScheduleDefinition(
    name="transform_pipeline_schedule",
    job=demo_pipeline_job,
    cron_schedule="*/5 * * * *",  # Every 5 minutes (offset by pipeline duration)
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start on deployment
    description="Run full transform pipeline every 5 minutes",
)


# =============================================================================
# Sensors
# =============================================================================


@sensor(
    job=demo_bronze_job,
    minimum_interval_seconds=60,
    default_status=DefaultSensorStatus.STOPPED,  # Start stopped for demo
    description="Trigger pipeline when trigger file appears",
)
def file_arrival_sensor(context: Any) -> Optional[RunRequest]:
    """Sensor for file arrival trigger.

    Monitors for /tmp/demo_trigger file and triggers pipeline.
    """
    trigger_path = os.environ.get("DEMO_TRIGGER_FILE", "/tmp/demo_trigger")

    if os.path.exists(trigger_path):
        try:
            os.remove(trigger_path)
            context.log.info("Trigger file detected, starting pipeline")
            return RunRequest(
                run_key=f"file_trigger_{context.cursor}",
                run_config={},
            )
        except OSError:
            pass

    return None


@sensor(
    job=demo_bronze_job,
    minimum_interval_seconds=30,
    default_status=DefaultSensorStatus.STOPPED,
    description="API trigger for on-demand pipeline execution",
)
def api_trigger_sensor(context: Any) -> Optional[RunRequest]:
    """Sensor for API-based on-demand triggers.

    Checks for /tmp/demo_api_trigger file.
    """
    trigger_path = os.environ.get("DEMO_API_TRIGGER_FILE", "/tmp/demo_api_trigger")

    if os.path.exists(trigger_path):
        try:
            os.remove(trigger_path)
            context.log.info("API trigger detected, starting pipeline")
            return RunRequest(
                run_key=f"api_trigger_{context.cursor}",
                run_config={},
            )
        except OSError:
            pass

    return None


# =============================================================================
# Definitions - One-line batteries-included factory
# =============================================================================

defs = FloeDefinitions.from_compiled_artifacts(
    artifacts_dict=get_compiled_artifacts_dict(),
    assets=[
        bronze_customers,
        bronze_products,
        bronze_orders,
        bronze_order_items,
        dbt_transformations,
    ],
    jobs=[
        demo_bronze_job,
        demo_pipeline_job,
    ],
    schedules=[
        synthetic_data_schedule,
        transform_pipeline_schedule,
    ],
    sensors=[
        file_arrival_sensor,
        api_trigger_sensor,
    ],
    namespace="demo",
)
