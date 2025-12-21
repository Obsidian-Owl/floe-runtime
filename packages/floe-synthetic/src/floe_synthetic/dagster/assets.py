"""Dagster assets for scheduled synthetic data generation.

This module provides Dagster assets that generate synthetic data
on a daily schedule, useful for demo environments.

Note: This module intentionally does NOT use `from __future__ import annotations`
because Dagster's @asset decorator validates type hints at runtime and PEP 563
string annotations confuse its context type validation.
"""

# Note: No `from __future__ import annotations` - see module docstring
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # Keep for potential future type-only imports

from dagster import (
    AssetExecutionContext,
    DailyPartitionsDefinition,
    asset,
)

from floe_synthetic.dagster.resources import (
    EcommerceGeneratorResource,
    IcebergLoaderResource,
    SaaSGeneratorResource,
)
from floe_synthetic.distributions.temporal import ECOMMERCE_DISTRIBUTION, SAAS_DISTRIBUTION

# Partition definitions for daily data generation
daily_partitions = DailyPartitionsDefinition(start_date="2024-01-01")


@asset(
    partitions_def=daily_partitions,
    group_name="synthetic_ecommerce",
    description="Generate daily e-commerce orders for demo environment",
)
def daily_ecommerce_orders(  # pragma: no cover - integration tested
    context: AssetExecutionContext,
    generator: EcommerceGeneratorResource,
    loader: IcebergLoaderResource,
) -> None:
    """Generate daily order transactions with realistic patterns.

    Simulates:
    - 500-2000 orders per day (randomized)
    - Intraday distribution (peak at business hours)
    - Realistic status and region distributions
    """
    partition_date = datetime.fromisoformat(context.partition_key)

    # Seed based on partition for reproducibility
    gen = generator.get_generator()
    gen.seed = hash(context.partition_key) % (2**31)

    # Calculate adjusted order count based on temporal patterns
    base_count = 1000
    adjusted_count = ECOMMERCE_DISTRIBUTION.adjusted_count(base_count, partition_date)

    context.log.info(f"Generating {adjusted_count} orders for {partition_date.date()}")

    # Ensure customers exist
    if not gen._customer_ids:
        customers = gen.generate_customers(1000)
        loader.get_loader().overwrite("demo.customers", customers)
        context.log.info("Generated 1000 customers")

    # Generate day's orders
    orders = gen.generate_orders(
        count=adjusted_count,
        start_date=partition_date.replace(hour=0, minute=0, second=0),
        end_date=partition_date.replace(hour=23, minute=59, second=59),
    )

    # Append to orders table
    result = loader.get_loader().append("demo.orders", orders)
    context.log.info(f"Appended {result.rows_loaded} orders, snapshot: {result.snapshot_id}")


@asset(
    partitions_def=daily_partitions,
    group_name="synthetic_saas",
    description="Generate daily SaaS events for demo environment",
)
def daily_saas_events(  # pragma: no cover - integration tested
    context: AssetExecutionContext,
    generator: SaaSGeneratorResource,
    loader: IcebergLoaderResource,
) -> None:
    """Generate daily user activity events with realistic patterns.

    Simulates:
    - 5000-20000 events per day
    - Various event types (page views, feature usage, API calls)
    - Session continuity
    """
    partition_date = datetime.fromisoformat(context.partition_key)

    # Seed based on partition for reproducibility
    gen = generator.get_generator()
    gen.seed = hash(context.partition_key) % (2**31)

    # Calculate adjusted event count
    base_count = 10000
    adjusted_count = SAAS_DISTRIBUTION.adjusted_count(base_count, partition_date)

    context.log.info(f"Generating {adjusted_count} events for {partition_date.date()}")

    # Ensure users exist
    if not gen._user_ids:
        users = gen.generate_users(500, with_organizations=True)
        loader.get_loader().overwrite("demo.users", users)
        context.log.info("Generated 500 users")

        # Also generate subscriptions
        subscriptions = gen.generate_subscriptions()
        loader.get_loader().overwrite("demo.subscriptions", subscriptions)
        context.log.info("Generated subscriptions")

    # Generate day's events
    events = gen.generate_events(
        count=adjusted_count,
        start_date=partition_date.replace(hour=0, minute=0, second=0),
        end_date=partition_date.replace(hour=23, minute=59, second=59),
    )

    # Append to events table
    result = loader.get_loader().append("demo.events", events)
    context.log.info(f"Appended {result.rows_loaded} events, snapshot: {result.snapshot_id}")
