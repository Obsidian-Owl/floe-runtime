#!/usr/bin/env python3
"""Generate Cube test data and load directly to Iceberg via PyIceberg.

This script generates test data using floe-synthetic and loads it directly
to Iceberg tables via the Polaris REST catalog. This avoids Trino's RANDOM()
bug which returns the same value for all rows in a query.

Usage:
    python generate_cube_data.py

Environment variables:
    POLARIS_CATALOG_URI: Polaris REST catalog URI (default: http://polaris:8181/api/catalog)
    POLARIS_CLIENT_ID: OAuth client ID for Polaris
    POLARIS_CLIENT_SECRET: OAuth client secret for Polaris
    DATA_COUNT: Number of orders to generate (default: 15500)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# Add the packages to path for local development
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "floe-synthetic" / "src"))

import pyarrow as pa
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NoSuchTableError, NamespaceAlreadyExistsError
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DoubleType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

from floe_synthetic.generators.ecommerce import EcommerceGenerator


def get_catalog() -> "Catalog":  # noqa: F821
    """Load Polaris catalog with OAuth credentials."""
    catalog_uri = os.environ.get("POLARIS_CATALOG_URI", "http://polaris:8181/api/catalog")
    client_id = os.environ.get("POLARIS_CLIENT_ID", "")
    client_secret = os.environ.get("POLARIS_CLIENT_SECRET", "")

    print(f"Connecting to Polaris at {catalog_uri}")

    return load_catalog(
        "polaris",
        type="rest",
        uri=catalog_uri,
        credential=f"{client_id}:{client_secret}",
        warehouse="test_warehouse",
        scope="PRINCIPAL_ROLE:ALL",
    )


def create_orders_table(catalog: "Catalog") -> "Table":  # noqa: F821
    """Create or get the orders table."""
    namespace = "default"
    table_name = "orders"
    full_name = f"{namespace}.{table_name}"

    # Ensure namespace exists
    try:
        catalog.create_namespace(namespace)
        print(f"Created namespace: {namespace}")
    except NamespaceAlreadyExistsError:
        print(f"Namespace already exists: {namespace}")

    # Define schema matching Trino table
    schema = Schema(
        NestedField(1, "id", LongType(), required=True),
        NestedField(2, "customer_id", LongType(), required=True),
        NestedField(3, "status", StringType(), required=True),
        NestedField(4, "region", StringType(), required=True),
        NestedField(5, "amount", DoubleType(), required=True),
        NestedField(6, "created_at", TimestampType(), required=True),
    )

    try:
        table = catalog.load_table(full_name)
        print(f"Table already exists: {full_name}")

        # Check if data needs regeneration
        scan = table.scan()
        row_count = sum(1 for _ in scan.to_arrow().to_batches())  # noqa: SIM118

        # Actually count properly
        arrow_table = table.scan().to_arrow()
        row_count = len(arrow_table)
        print(f"  Current row count: {row_count}")

        # Check region distribution
        if row_count > 0:
            regions = set(arrow_table.column("region").to_pylist())
            print(f"  Distinct regions: {len(regions)} ({regions})")

            if row_count >= 15000 and len(regions) >= 4:
                print("  Data quality is good, skipping regeneration")
                return table

        print("  Data needs regeneration, dropping table...")
        catalog.drop_table(full_name)

    except NoSuchTableError:
        print(f"Table does not exist, will create: {full_name}")

    # Create fresh table
    table = catalog.create_table(
        full_name,
        schema=schema,
    )
    print(f"Created table: {full_name}")

    return table


def generate_and_load_data(table: "Table", count: int = 15500) -> None:  # noqa: F821
    """Generate synthetic data and load to Iceberg table."""
    print(f"\nGenerating {count} orders using floe-synthetic...")

    # Generate data with proper weighted distributions
    generator = EcommerceGenerator(seed=42)

    # Generate customers first (required for orders)
    customers = generator.generate_customers(
        count=1000,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2024, 1, 1),
    )
    print(f"  Generated {len(customers)} customers")

    # Generate orders with realistic distributions
    orders = generator.generate_orders(
        count=count,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
    )
    print(f"  Generated {len(orders)} orders")

    # Verify distributions before loading
    print("\n=== Pre-load Distribution Check ===")

    status_col = orders.column("status").to_pylist()
    status_counts: dict[str, int] = {}
    for s in status_col:
        status_counts[s] = status_counts.get(s, 0) + 1
    print("Status distribution:")
    for status, cnt in sorted(status_counts.items()):
        pct = cnt / len(status_col) * 100
        print(f"  {status}: {cnt} ({pct:.1f}%)")

    region_col = orders.column("region").to_pylist()
    region_counts: dict[str, int] = {}
    for r in region_col:
        region_counts[r] = region_counts.get(r, 0) + 1
    print("Region distribution:")
    for region, cnt in sorted(region_counts.items()):
        pct = cnt / len(region_col) * 100
        print(f"  {region}: {cnt} ({pct:.1f}%)")

    # Load to Iceberg
    print(f"\nLoading {len(orders)} orders to Iceberg...")
    table.append(orders)
    print("  Data loaded successfully!")

    # Verify final state
    final_table = table.scan().to_arrow()
    print(f"\n=== Final Table State ===")
    print(f"Total rows: {len(final_table)}")


def main() -> int:
    """Main entry point."""
    try:
        data_count = int(os.environ.get("DATA_COUNT", "15500"))

        catalog = get_catalog()
        table = create_orders_table(catalog)
        generate_and_load_data(table, count=data_count)

        print("\n✓ Cube test data initialization complete!")
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
