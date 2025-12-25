"""Dagster Definitions for Floe Demo - Batteries-Included Implementation.

Provides orchestration for the demo e-commerce data pipeline with:
- Real Iceberg table storage via Polaris/LocalStack
- Real OpenTelemetry tracing visible in Jaeger
- Real OpenLineage lineage visible in Marquez

This demo uses the batteries-included @floe_asset decorator which
automatically handles observability (tracing + lineage) without boilerplate.

Data Flow:
    1. Raw Layer: Pre-staged by seed job (demo.raw_*)
    2. Bronze Layer: Load from raw → Iceberg tables (demo.bronze_*)
    3. Silver Layer: dbt staging transformations
    4. Gold Layer: dbt mart transformations
    5. Semantic Layer: Cube queries mart tables

Two-Tier Architecture:
    Data engineers write assets with NO infrastructure configuration.
    FloeDefinitions auto-loads platform.yaml via FLOE_PLATFORM_FILE env var.
    Platform engineers configure infrastructure in platform.yaml.

Note: This file intentionally does NOT use `from __future__ import annotations`
because Dagster 1.12.x's type validation uses identity checks that break with
PEP 563 string annotations.
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
from dagster_dbt import DbtCliResource

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
from floe_dagster import FloeDefinitions, floe_asset
from floe_dagster.resources import CatalogResource

logger = logging.getLogger(__name__)


# =============================================================================
# Bronze Layer Assets - Load from Raw Tables
# =============================================================================


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
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
    """Load order item data from raw to bronze layer."""
    context.log.info("Loading order items from %s", TABLE_RAW_ORDER_ITEMS)
    raw_data = catalog.read_table(TABLE_RAW_ORDER_ITEMS)
    snapshot = catalog.write_table(TABLE_BRONZE_ORDER_ITEMS, raw_data)
    return {"rows": raw_data.num_rows, "snapshot_id": snapshot.snapshot_id}


@floe_asset(
    group_name="silver",
    description="Run dbt staging models (Bronze → Silver)",
    inputs=[
        TABLE_BRONZE_CUSTOMERS,
        TABLE_BRONZE_ORDERS,
        TABLE_BRONZE_PRODUCTS,
        TABLE_BRONZE_ORDER_ITEMS,
    ],
    outputs=[
        "demo.silver_customers",
        "demo.silver_orders",
        "demo.silver_products",
        "demo.silver_order_items",
    ],
    compute_kind="dbt",
    deps=["bronze_customers", "bronze_orders", "bronze_products", "bronze_order_items"],
)
def silver_staging(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
) -> Dict[str, Any]:
    """Run dbt staging models to create Silver layer."""
    context.log.info("Running dbt staging models...")

    # Run dbt models in staging folder
    dbt_run = dbt.cli(["run", "--select", "staging.*"], context=context)

    return {
        "models_run": len(dbt_run.result.results),
        "success": dbt_run.success,
        "run_results": dbt_run.result.to_dict(),
    }


@floe_asset(
    group_name="gold",
    description="Run dbt marts (Silver → Gold)",
    inputs=[
        "demo.silver_customers",
        "demo.silver_orders",
        "demo.silver_products",
        "demo.silver_order_items",
    ],
    outputs=[
        "demo.gold_customer_orders",
        "demo.gold_revenue",
        "demo.gold_product_performance",
    ],
    compute_kind="dbt",
    deps=["silver_staging"],
)
def gold_marts(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
) -> Dict[str, Any]:
    """Run dbt marts to create Gold layer."""
    context.log.info("Running dbt marts...")

    # Run dbt models in marts folder
    dbt_run = dbt.cli(["run", "--select", "marts.*"], context=context)

    return {
        "models_run": len(dbt_run.result.results),
        "success": dbt_run.success,
        "run_results": dbt_run.result.to_dict(),
    }


# =============================================================================
# Jobs
# =============================================================================

demo_bronze_job = define_asset_job(
    name="demo_bronze",
    selection=AssetSelection.groups("bronze"),
    description="Load bronze layer: raw tables → bronze Iceberg tables",
)

demo_pipeline_job = define_asset_job(
    name="demo_pipeline",
    selection=AssetSelection.groups("bronze", "silver", "gold"),
    description="Full demo pipeline: bronze → silver → gold",
)


# =============================================================================
# Schedules
# =============================================================================

bronze_refresh_schedule = ScheduleDefinition(
    name="bronze_refresh_schedule",
    job=demo_bronze_job,
    cron_schedule="*/5 * * * *",
    default_status=DefaultScheduleStatus.STOPPED,
    description="Refresh bronze layer from raw tables every 5 minutes",
)

transform_pipeline_schedule = ScheduleDefinition(
    name="transform_pipeline_schedule",
    job=demo_pipeline_job,
    cron_schedule="*/5 * * * *",
    default_status=DefaultScheduleStatus.RUNNING,
    description="Run full transform pipeline every 5 minutes",
)


# =============================================================================
# Sensors
# =============================================================================


@sensor(
    job=demo_bronze_job,
    minimum_interval_seconds=60,
    default_status=DefaultSensorStatus.STOPPED,
    description="Trigger pipeline when trigger file appears",
)
def file_arrival_sensor(context: Any) -> Optional[RunRequest]:
    """Sensor for file arrival trigger."""
    trigger_path = os.environ.get("DEMO_TRIGGER_FILE", "/tmp/demo_trigger")
    if os.path.exists(trigger_path):
        try:
            os.remove(trigger_path)
            context.log.info("Trigger file detected, starting pipeline")
            return RunRequest(run_key=f"file_trigger_{context.cursor}", run_config={})
        except OSError:
            pass
    return None


# =============================================================================
# Definitions - Auto-loads platform.yaml via FLOE_PLATFORM_FILE
# =============================================================================

defs = FloeDefinitions.from_compiled_artifacts(
    assets=[
        bronze_customers,
        bronze_products,
        bronze_orders,
        bronze_order_items,
        silver_staging,
        gold_marts,
    ],
    jobs=[demo_bronze_job, demo_pipeline_job],
    schedules=[bronze_refresh_schedule, transform_pipeline_schedule],
    sensors=[file_arrival_sensor],
    namespace="demo",
)
