"""E-commerce data generator using Faker.

This module provides the EcommerceGenerator for generating realistic
e-commerce test data including customers, orders, and products.

Features:
- Deterministic seeding for reproducible tests
- Weighted distributions for realistic patterns
- Foreign key relationships maintained
- PyArrow output for Iceberg compatibility
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pyarrow as pa
from faker import Faker

from floe_synthetic.generators.base import (
    DataGenerator,
    REGION_WEIGHTS,
    STATUS_WEIGHTS,
)


class EcommerceGenerator(DataGenerator):
    """Generator for e-commerce data with realistic distributions.

    Generates customers, orders, and products with proper relationships.
    Uses Faker for realistic data and supports weighted distributions.

    Attributes:
        seed: Random seed for reproducibility
        fake: Faker instance for data generation

    Example:
        >>> generator = EcommerceGenerator(seed=42)
        >>> customers = generator.generate_customers(1000)
        >>> orders = generator.generate_orders(5000)
        >>> products = generator.generate_products(100)
    """

    def __init__(self, seed: int = 42) -> None:
        """Initialize the generator with a seed.

        Args:
            seed: Random seed for reproducibility. Same seed produces
                  identical data across runs.
        """
        self.seed = seed
        # Use instance-level seeding for true reproducibility
        self.fake = Faker()
        self.fake.seed_instance(seed)
        # Track generated entities for foreign key relationships
        self._customer_ids: list[int] = []
        self._customer_regions: dict[int, str] = {}
        self._product_ids: list[int] = []

    def generate_batch(self, count: int, **kwargs: Any) -> pa.Table:
        """Generate a batch of orders (default entity).

        Args:
            count: Number of orders to generate
            **kwargs: Additional options (status_weights, region_weights)

        Returns:
            PyArrow Table with order data
        """
        return self.generate_orders(count, **kwargs)

    def generate_stream(
        self,
        total: int,
        batch_size: int = 10000,
        **kwargs: Any,
    ) -> Iterator[pa.Table]:
        """Stream order batches for large datasets.

        Args:
            total: Total number of orders to generate
            batch_size: Orders per batch
            **kwargs: Options passed to generate_orders

        Yields:
            PyArrow Tables with order data
        """
        for i in range(0, total, batch_size):
            current_batch = min(batch_size, total - i)
            yield self.generate_orders(
                count=current_batch,
                start_id=i + 1,
                **kwargs,
            )

    def generate_customers(
        self,
        count: int,
        *,
        start_id: int = 1,
        region_weights: dict[str, int] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pa.Table:
        """Generate customer records with varied regions.

        Args:
            count: Number of customers to generate
            start_id: Starting customer_id (default: 1)
            region_weights: Custom region distribution (default: 25% each)
            start_date: Earliest signup date (default: 2 years ago)
            end_date: Latest signup date (default: now)

        Returns:
            PyArrow Table with customer data
        """
        weights = region_weights or REGION_WEIGHTS
        regions = list(weights.keys())
        region_probs = [w / sum(weights.values()) for w in weights.values()]

        start_date = start_date or datetime.now() - timedelta(days=730)
        end_date = end_date or datetime.now()

        # Track for foreign key relationships
        self._customer_ids = list(range(start_id, start_id + count))

        customer_ids: list[int] = []
        names: list[str] = []
        emails: list[str] = []
        customer_regions: list[str] = []
        created_ats: list[datetime] = []

        for i in range(count):
            customer_id = start_id + i
            customer_ids.append(customer_id)
            names.append(self.fake.name())
            emails.append(self.fake.email())

            # Weighted region selection (OrderedDict required by Faker)
            region = self.fake.random_element(
                elements=OrderedDict(zip(regions, region_probs, strict=True))
            )
            customer_regions.append(region)
            self._customer_regions[customer_id] = region

            created_ats.append(
                self.fake.date_time_between(start_date=start_date, end_date=end_date)
            )

        self._log_generation("customers", count)

        return pa.table(
            {
                "customer_id": pa.array(customer_ids, type=pa.int64()),
                "name": pa.array(names, type=pa.string()),
                "email": pa.array(emails, type=pa.string()),
                "region": pa.array(customer_regions, type=pa.string()),
                "created_at": pa.array(created_ats, type=pa.timestamp("us")),
            }
        )

    def generate_orders(
        self,
        count: int,
        *,
        start_id: int = 1,
        status_weights: dict[str, int] | None = None,
        region_weights: dict[str, int] | None = None,
        min_amount: Decimal = Decimal("10.00"),
        max_amount: Decimal = Decimal("1000.00"),
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        inherit_customer_region: bool = False,
    ) -> pa.Table:
        """Generate order records with realistic distributions.

        Args:
            count: Number of orders to generate
            start_id: Starting order_id (default: 1)
            status_weights: Custom status distribution
            region_weights: Custom region distribution
            min_amount: Minimum order amount
            max_amount: Maximum order amount
            start_date: Earliest order date (default: 1 year ago)
            end_date: Latest order date (default: now)
            inherit_customer_region: If True, inherit region from customer

        Returns:
            PyArrow Table with order data
        """
        # Generate customers if none exist
        if not self._customer_ids:
            self.generate_customers(1000)

        s_weights = status_weights or STATUS_WEIGHTS
        r_weights = region_weights or REGION_WEIGHTS

        statuses = list(s_weights.keys())
        status_probs = [w / sum(s_weights.values()) for w in s_weights.values()]

        regions = list(r_weights.keys())
        region_probs = [w / sum(r_weights.values()) for w in r_weights.values()]

        start_date = start_date or datetime.now() - timedelta(days=365)
        end_date = end_date or datetime.now()

        order_ids: list[int] = []
        customer_ids: list[int] = []
        order_statuses: list[str] = []
        order_regions: list[str] = []
        amounts: list[float] = []
        created_ats: list[datetime] = []

        for i in range(count):
            order_ids.append(start_id + i)

            # Select customer (with some customers having more orders - Pareto-like)
            customer_id = self.fake.random_element(self._customer_ids)
            customer_ids.append(customer_id)

            # Weighted status selection (OrderedDict required by Faker)
            status = self.fake.random_element(
                elements=OrderedDict(zip(statuses, status_probs, strict=True))
            )
            order_statuses.append(status)

            # Region: either inherit from customer or generate with weights
            if inherit_customer_region and customer_id in self._customer_regions:
                region = self._customer_regions[customer_id]
            else:
                region = self.fake.random_element(
                    elements=OrderedDict(zip(regions, region_probs, strict=True))
                )
            order_regions.append(region)

            # Amount with realistic decimal
            amount = float(
                self.fake.pydecimal(
                    min_value=min_amount,
                    max_value=max_amount,
                    right_digits=2,
                )
            )
            amounts.append(amount)

            created_ats.append(
                self.fake.date_time_between(start_date=start_date, end_date=end_date)
            )

        self._log_generation("orders", count)

        return pa.table(
            {
                "id": pa.array(order_ids, type=pa.int64()),
                "customer_id": pa.array(customer_ids, type=pa.int64()),
                "status": pa.array(order_statuses, type=pa.string()),
                "region": pa.array(order_regions, type=pa.string()),
                "amount": pa.array(amounts, type=pa.float64()),
                "created_at": pa.array(created_ats, type=pa.timestamp("us")),
            }
        )

    def generate_products(
        self,
        count: int,
        *,
        start_id: int = 1,
        min_price: Decimal = Decimal("5.00"),
        max_price: Decimal = Decimal("500.00"),
    ) -> pa.Table:
        """Generate product catalog records.

        Args:
            count: Number of products to generate
            start_id: Starting product_id (default: 1)
            min_price: Minimum product price
            max_price: Maximum product price

        Returns:
            PyArrow Table with product data
        """
        categories = ["electronics", "clothing", "home", "sports", "books"]

        self._product_ids = list(range(start_id, start_id + count))

        product_ids: list[int] = []
        names: list[str] = []
        product_categories: list[str] = []
        prices: list[float] = []
        skus: list[str] = []

        for i in range(count):
            product_id = start_id + i
            product_ids.append(product_id)

            # Generate realistic product names
            category = self.fake.random_element(elements=categories)
            product_categories.append(category)

            if category == "electronics":
                name = f"{self.fake.word().title()} {self.fake.random_element(['Pro', 'Ultra', 'Max', 'Plus'])} {self.fake.random_element(['Phone', 'Tablet', 'Laptop', 'Headphones', 'Speaker'])}"
            elif category == "clothing":
                name = f"{self.fake.color_name()} {self.fake.random_element(['T-Shirt', 'Jacket', 'Pants', 'Dress', 'Shoes'])}"
            elif category == "home":
                name = f"{self.fake.word().title()} {self.fake.random_element(['Lamp', 'Chair', 'Table', 'Rug', 'Pillow'])}"
            elif category == "sports":
                name = f"{self.fake.word().title()} {self.fake.random_element(['Ball', 'Racket', 'Weights', 'Mat', 'Gear'])}"
            else:  # books
                name = f"The {self.fake.word().title()} {self.fake.random_element(['Guide', 'Story', 'Manual', 'Handbook', 'Journey'])}"

            names.append(name)

            price = float(
                self.fake.pydecimal(
                    min_value=min_price,
                    max_value=max_price,
                    right_digits=2,
                )
            )
            prices.append(price)

            # Generate SKU
            sku = f"{category[:3].upper()}-{self.fake.random_int(100, 999)}"
            skus.append(sku)

        self._log_generation("products", count)

        return pa.table(
            {
                "product_id": pa.array(product_ids, type=pa.int64()),
                "name": pa.array(names, type=pa.string()),
                "category": pa.array(product_categories, type=pa.string()),
                "price": pa.array(prices, type=pa.float64()),
                "sku": pa.array(skus, type=pa.string()),
            }
        )

    def reset(self) -> None:
        """Reset the generator state.

        Clears tracked customer and product IDs. Useful between test runs
        when you want fresh data without changing the seed.
        """
        self._customer_ids = []
        self._customer_regions = {}
        self._product_ids = []
        self.fake.seed_instance(self.seed)
