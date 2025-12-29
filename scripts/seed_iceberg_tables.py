#!/usr/bin/env python
"""Seed Iceberg tables with demo e-commerce data.

This script creates demo.raw_* tables that represent pre-staged data from
an ELT pipeline. Bronze layer assets then load from these tables, demonstrating
a real-world data flow pattern.

Tables created:
    - demo.raw_customers
    - demo.raw_products
    - demo.raw_orders
    - demo.raw_order_items

Usage:
    # Using environment variables (recommended for K8s/Docker)
    export POLARIS_URI=http://localhost:8181/api/catalog
    export POLARIS_WAREHOUSE=demo_catalog
    export POLARIS_CLIENT_ID=demo_client
    export POLARIS_CLIENT_SECRET=demo_secret
    export AWS_ENDPOINT_URL=http://localhost:4566
    export AWS_ACCESS_KEY_ID=test
    export AWS_SECRET_ACCESS_KEY=test
    python scripts/seed_iceberg_tables.py

    # Using command-line arguments
    python scripts/seed_iceberg_tables.py \\
        --polaris-uri http://localhost:8181/api/catalog \\
        --warehouse demo_catalog \\
        --customers 1000 \\
        --seed 42

Environment Variables:
    POLARIS_URI: Polaris REST API endpoint
    POLARIS_WAREHOUSE: Warehouse/catalog name
    POLARIS_CLIENT_ID: OAuth2 client ID
    POLARIS_CLIENT_SECRET: OAuth2 client secret
    AWS_ENDPOINT_URL: S3-compatible endpoint (for LocalStack/MinIO)
    AWS_ACCESS_KEY_ID: S3 access key
    AWS_SECRET_ACCESS_KEY: S3 secret key
    AWS_REGION: S3 region (default: us-east-1)
    DEMO_SEED: Random seed for reproducible data (default: 42)
    DEMO_CUSTOMERS_COUNT: Number of customers (default: 1000)
    DEMO_PRODUCTS_COUNT: Number of products (default: 100)
    DEMO_ORDERS_COUNT: Number of orders (default: 5000)
    DEMO_ORDER_ITEMS_COUNT: Number of order items (default: 10000)

Covers: 009-FR-001 (Two-Tier Configuration Architecture)
Covers: 007-FR-031 (Medallion architecture demo)
"""

from __future__ import annotations

import argparse
import os
import sys

from pydantic import SecretStr


def _detect_s3_endpoint() -> str:
    """Detect S3 endpoint based on execution context.

    Returns:
        S3 endpoint URL appropriate for execution context

    Notes:
        - Explicit AWS_ENDPOINT_URL environment variable takes precedence
        - Detects K8s execution by checking for service account token
        - Falls back to NodePort for local machine execution
    """
    # Explicit override takes precedence
    if endpoint := os.environ.get("AWS_ENDPOINT_URL"):
        return endpoint

    # Detect K8s execution context
    if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"):
        # Running in K8s pod - use internal service DNS
        return "http://floe-infra-localstack:4566"

    # Local execution - use NodePort (survives pod restarts)
    return "http://localhost:30566"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Seed Iceberg tables with demo e-commerce data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Polaris connection
    parser.add_argument(
        "--polaris-uri",
        default=os.environ.get("POLARIS_URI", "http://localhost:8181/api/catalog"),
        help="Polaris REST API endpoint",
    )
    parser.add_argument(
        "--warehouse",
        default=os.environ.get("POLARIS_WAREHOUSE", "demo_catalog"),
        help="Warehouse/catalog name",
    )
    parser.add_argument(
        "--client-id",
        default=os.environ.get("POLARIS_CLIENT_ID", "demo_client"),
        help="OAuth2 client ID",
    )
    parser.add_argument(
        "--client-secret",
        default=os.environ.get("POLARIS_CLIENT_SECRET", "demo_secret"),
        help="OAuth2 client secret",
    )

    # S3 configuration
    parser.add_argument(
        "--s3-endpoint",
        default=_detect_s3_endpoint(),
        help="S3-compatible endpoint (auto-detected based on context)",
    )
    parser.add_argument(
        "--s3-region",
        default=os.environ.get("AWS_REGION", "us-east-1"),
        help="S3 region",
    )

    # Data volume
    parser.add_argument(
        "--seed",
        type=int,
        default=int(os.environ.get("DEMO_SEED", "42")),
        help="Random seed for reproducible data",
    )
    parser.add_argument(
        "--customers",
        type=int,
        default=int(os.environ.get("DEMO_CUSTOMERS_COUNT", "1000")),
        help="Number of customers to generate",
    )
    parser.add_argument(
        "--products",
        type=int,
        default=int(os.environ.get("DEMO_PRODUCTS_COUNT", "100")),
        help="Number of products to generate",
    )
    parser.add_argument(
        "--orders",
        type=int,
        default=int(os.environ.get("DEMO_ORDERS_COUNT", "5000")),
        help="Number of orders to generate",
    )
    parser.add_argument(
        "--order-items",
        type=int,
        default=int(os.environ.get("DEMO_ORDER_ITEMS_COUNT", "10000")),
        help="Number of order items to generate",
    )

    # Flags
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate data without writing to tables",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for seeding Iceberg tables."""
    args = parse_args()

    print("=" * 60)
    print("FLOE DEMO - Seeding Iceberg Tables")
    print("=" * 60)
    print(f"Polaris URI: {args.polaris_uri}")
    print(f"Warehouse: {args.warehouse}")
    print(f"S3 Endpoint: {args.s3_endpoint}")
    print(f"Seed: {args.seed}")
    print()

    # Import floe packages
    try:
        from floe_iceberg.tables import IcebergTableManager
        from floe_polaris.client import PolarisCatalog
        from floe_polaris.config import PolarisCatalogConfig
        from floe_synthetic.generators.ecommerce import EcommerceGenerator
    except ImportError as e:
        print(f"ERROR: Failed to import floe packages: {e}")
        print("Install with: uv sync --all-packages")
        return 1

    # Resolve S3 credentials from environment
    s3_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "test")
    s3_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")

    # Configure Polaris catalog
    config = PolarisCatalogConfig(
        uri=args.polaris_uri,
        warehouse=args.warehouse,
        client_id=args.client_id,
        client_secret=SecretStr(args.client_secret),
        scope="PRINCIPAL_ROLE:ALL",
        s3_endpoint=args.s3_endpoint,
        s3_region=args.s3_region,
        s3_path_style_access=True,
        s3_access_key_id=s3_access_key,
        s3_secret_access_key=SecretStr(s3_secret_key),
    )

    if args.dry_run:
        print("DRY RUN - not connecting to catalog")
    else:
        print("Creating Polaris catalog connection...")
        try:
            catalog = PolarisCatalog(config)
            manager = IcebergTableManager(catalog.inner_catalog)
            print("✅ Connected to Polaris catalog")
        except Exception as e:
            print(f"ERROR: Failed to connect to Polaris: {e}")
            return 1

    # Generate synthetic data
    print()
    print("Generating synthetic e-commerce data...")
    generator = EcommerceGenerator(seed=args.seed)

    # Generate data with proper FK relationships
    customers = generator.generate_customers(count=args.customers)
    products = generator.generate_products(count=args.products)
    orders = generator.generate_orders(count=args.orders)
    order_items = generator.generate_order_items(count=args.order_items)

    print(f"  ✅ Customers: {customers.num_rows} rows")
    print(f"  ✅ Products: {products.num_rows} rows")
    print(f"  ✅ Orders: {orders.num_rows} rows")
    print(f"  ✅ Order Items: {order_items.num_rows} rows")

    if args.verbose:
        print()
        print("Customer schema:")
        print(customers.schema)
        print()
        print("Order schema:")
        print(orders.schema)

    if args.dry_run:
        print()
        print("DRY RUN - skipping table writes")
        return 0

    # Define tables to seed
    tables = [
        ("demo.raw_customers", customers),
        ("demo.raw_products", products),
        ("demo.raw_orders", orders),
        ("demo.raw_order_items", order_items),
    ]

    # Seed tables
    print()
    print("Seeding Iceberg tables...")
    success = True
    for table_id, data in tables:
        print(f"  Seeding {table_id}...")
        try:
            # Create table if not exists
            manager.create_table_if_not_exists(table_id, data.schema)
            # Overwrite with fresh data
            snapshot = manager.overwrite(table_id, data)
            print(f"    ✅ {table_id}: {data.num_rows} rows (snapshot: {snapshot.snapshot_id})")
        except Exception as e:
            print(f"    ❌ Failed to seed {table_id}: {e}")
            success = False

    print()
    print("=" * 60)
    if success:
        print("✅ Demo seed data complete!")
    else:
        print("⚠️  Some tables failed to seed")
    print("=" * 60)
    print()
    print("Raw layer tables are ready for bronze layer assets to process.")
    print("Run the Dagster demo_bronze job to transform raw → bronze.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
