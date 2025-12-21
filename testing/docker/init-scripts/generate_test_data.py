#!/usr/bin/env python3
"""Generate test data for Cube integration tests using floe-synthetic.

This script replaces SQL-based data generation which suffered from Trino's
RANDOM() bug (returns same value for all rows).

Usage:
    python generate_test_data.py --output /tmp/orders.parquet --count 15500

The generated Parquet file can then be loaded via Trino's INSERT.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

# Add the packages to path for local development
_package_path = Path(__file__).parent.parent.parent.parent / "packages" / "floe-synthetic" / "src"
sys.path.insert(0, str(_package_path))

from floe_synthetic.generators.ecommerce import EcommerceGenerator  # noqa: E402


def main() -> int:
    """Generate test data and save to Parquet file."""
    parser = argparse.ArgumentParser(description="Generate synthetic test data")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/orders.parquet"),
        help="Output Parquet file path",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=15500,
        help="Number of orders to generate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Print distribution verification",
    )
    args = parser.parse_args()

    print(f"Generating {args.count} orders with seed {args.seed}...")

    # Generate data with proper weighted distributions
    generator = EcommerceGenerator(seed=args.seed)

    # Generate customers first (required for orders)
    customers = generator.generate_customers(
        count=1000,
        start_date=datetime(2022, 1, 1),
        end_date=datetime(2024, 1, 1),
    )
    print(f"  Generated {len(customers)} customers")

    # Generate orders with realistic distributions
    # Default weights: status (completed:60, processing:20, pending:15, cancelled:5)
    # Default weights: region (north:25, south:25, east:25, west:25)
    orders = generator.generate_orders(
        count=args.count,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
    )
    print(f"  Generated {len(orders)} orders")

    # Save to Parquet
    import pyarrow.parquet as pq

    pq.write_table(orders, args.output)
    print(f"  Saved to {args.output}")

    if args.verify:
        print("\n=== Distribution Verification ===")

        # Status distribution
        status_col = orders.column("status").to_pylist()
        status_counts = {}
        for s in status_col:
            status_counts[s] = status_counts.get(s, 0) + 1
        print("\nStatus distribution:")
        for status, count in sorted(status_counts.items()):
            pct = count / len(status_col) * 100
            print(f"  {status}: {count} ({pct:.1f}%)")

        # Region distribution
        region_col = orders.column("region").to_pylist()
        region_counts = {}
        for r in region_col:
            region_counts[r] = region_counts.get(r, 0) + 1
        print("\nRegion distribution:")
        for region, count in sorted(region_counts.items()):
            pct = count / len(region_col) * 100
            print(f"  {region}: {count} ({pct:.1f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
