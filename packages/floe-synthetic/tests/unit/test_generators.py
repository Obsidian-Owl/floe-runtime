"""Unit tests for synthetic data generators.

Tests cover:
- Deterministic seeding and reproducibility
- Weighted distributions
- Schema compliance
- Foreign key relationships
- Batch generation
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pyarrow as pa
import pytest

from floe_synthetic.generators.ecommerce import EcommerceGenerator
from floe_synthetic.generators.saas import SaaSGenerator

# Mark all tests as unit tests
pytestmark = pytest.mark.unit


class TestEcommerceGenerator:
    """Tests for EcommerceGenerator."""

    def test_deterministic_seeding(self) -> None:
        """Same seed produces identical data (with fixed date range for determinism)."""
        # Use fixed date range to ensure deterministic timestamps
        end_date = datetime(2025, 1, 1)
        start_date = end_date - timedelta(days=365)

        gen1 = EcommerceGenerator(seed=42)
        gen2 = EcommerceGenerator(seed=42)

        # Generate with explicit date range for determinism
        gen1.generate_customers(1000, start_date=start_date, end_date=end_date)
        gen2.generate_customers(1000, start_date=start_date, end_date=end_date)

        orders1 = gen1.generate_orders(100, start_date=start_date, end_date=end_date)
        orders2 = gen2.generate_orders(100, start_date=start_date, end_date=end_date)

        # All columns should be identical with fixed date range
        assert orders1.equals(orders2)

    def test_different_seeds_produce_different_data(self) -> None:
        """Different seeds produce different data."""
        gen1 = EcommerceGenerator(seed=42)
        gen2 = EcommerceGenerator(seed=123)

        orders1 = gen1.generate_orders(100)
        orders2 = gen2.generate_orders(100)

        # Data should differ
        assert not orders1.equals(orders2)

    def test_generate_customers_schema(self) -> None:
        """Generated customers have correct schema."""
        gen = EcommerceGenerator(seed=42)
        customers = gen.generate_customers(100)

        assert isinstance(customers, pa.Table)
        assert len(customers) == 100

        # Check expected columns
        expected_columns = {"customer_id", "name", "email", "region", "created_at"}
        assert set(customers.column_names) == expected_columns

        # Check types
        assert customers.schema.field("customer_id").type == pa.int64()
        assert customers.schema.field("name").type == pa.string()
        assert customers.schema.field("region").type == pa.string()

    def test_generate_orders_schema(self) -> None:
        """Generated orders have correct schema."""
        gen = EcommerceGenerator(seed=42)
        orders = gen.generate_orders(100)

        assert isinstance(orders, pa.Table)
        assert len(orders) == 100

        # Check expected columns
        expected_columns = {"id", "customer_id", "status", "region", "amount", "created_at"}
        assert set(orders.column_names) == expected_columns

    def test_orders_have_valid_status_values(self) -> None:
        """All order statuses are valid values."""
        gen = EcommerceGenerator(seed=42)
        orders = gen.generate_orders(1000)

        valid_statuses = {"pending", "processing", "completed", "cancelled"}
        statuses = set(orders.column("status").to_pylist())

        assert statuses.issubset(valid_statuses)

    def test_orders_have_valid_region_values(self) -> None:
        """All order regions are valid values."""
        gen = EcommerceGenerator(seed=42)
        orders = gen.generate_orders(1000)

        valid_regions = {"north", "south", "east", "west"}
        regions = set(orders.column("region").to_pylist())

        assert regions.issubset(valid_regions)

    def test_weighted_status_distribution(self) -> None:
        """Custom status weights are respected (approximately)."""
        gen = EcommerceGenerator(seed=42)

        # Generate many orders to test distribution
        orders = gen.generate_orders(
            10000,
            status_weights={"completed": 80, "pending": 20},
        )

        statuses = orders.column("status").to_pylist()
        completed_count = statuses.count("completed")

        # Should be approximately 80/20 (±5%)
        completed_ratio = completed_count / len(statuses)
        assert 0.75 <= completed_ratio <= 0.85

    def test_weighted_region_distribution(self) -> None:
        """Custom region weights are respected."""
        gen = EcommerceGenerator(seed=42)

        # Generate many orders with equal region weights
        orders = gen.generate_orders(
            10000,
            region_weights={"north": 25, "south": 25, "east": 25, "west": 25},
        )

        regions = orders.column("region").to_pylist()

        # Each region should have approximately 25% (±5%)
        for region in ["north", "south", "east", "west"]:
            ratio = regions.count(region) / len(regions)
            assert 0.20 <= ratio <= 0.30, f"Region {region} has {ratio:.1%}"

    def test_orders_reference_existing_customers(self) -> None:
        """Orders reference generated customer IDs."""
        gen = EcommerceGenerator(seed=42)

        # Generate customers first
        customers = gen.generate_customers(100)
        customer_ids = set(customers.column("customer_id").to_pylist())

        # Generate orders
        orders = gen.generate_orders(500)
        order_customer_ids = set(orders.column("customer_id").to_pylist())

        # All order customer_ids should exist in customers
        assert order_customer_ids.issubset(customer_ids)

    def test_generate_products_schema(self) -> None:
        """Generated products have correct schema."""
        gen = EcommerceGenerator(seed=42)
        products = gen.generate_products(50)

        assert isinstance(products, pa.Table)
        assert len(products) == 50

        expected_columns = {"product_id", "name", "category", "price", "sku"}
        assert set(products.column_names) == expected_columns

    def test_order_amounts_in_range(self) -> None:
        """Order amounts are within specified range."""
        gen = EcommerceGenerator(seed=42)
        orders = gen.generate_orders(
            100,
            min_amount=Decimal("50.00"),
            max_amount=Decimal("200.00"),
        )

        amounts = orders.column("amount").to_pylist()
        assert all(50.0 <= amt <= 200.0 for amt in amounts)

    def test_date_range_respected(self) -> None:
        """Generated dates fall within specified range."""
        gen = EcommerceGenerator(seed=42)
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)

        orders = gen.generate_orders(100, start_date=start, end_date=end)

        dates = orders.column("created_at").to_pylist()
        for dt in dates:
            assert start <= dt <= end

    def test_reset_clears_state(self) -> None:
        """Reset clears tracked customer and product IDs."""
        gen = EcommerceGenerator(seed=42)

        gen.generate_customers(100)
        assert len(gen._customer_ids) == 100

        gen.reset()
        assert len(gen._customer_ids) == 0

    def test_generate_stream_batches(self) -> None:
        """Stream generator produces correct number of batches."""
        gen = EcommerceGenerator(seed=42)
        gen.generate_customers(100)  # Pre-generate customers

        batches = list(gen.generate_stream(total=250, batch_size=100))

        assert len(batches) == 3
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        assert len(batches[2]) == 50


class TestSaaSGenerator:
    """Tests for SaaSGenerator."""

    def test_deterministic_seeding(self) -> None:
        """Same seed produces identical data."""
        gen1 = SaaSGenerator(seed=42)
        gen2 = SaaSGenerator(seed=42)

        users1 = gen1.generate_users(100)
        users2 = gen2.generate_users(100)

        assert users1.equals(users2)

    def test_generate_users_schema(self) -> None:
        """Generated users have correct schema."""
        gen = SaaSGenerator(seed=42)
        users = gen.generate_users(100)

        assert isinstance(users, pa.Table)
        assert len(users) == 100

        expected_columns = {
            "user_id",
            "email",
            "name",
            "plan",
            "organization_id",
            "signup_date",
            "last_active_at",
        }
        assert set(users.column_names) == expected_columns

    def test_users_have_valid_plan_values(self) -> None:
        """All user plans are valid values."""
        gen = SaaSGenerator(seed=42)
        users = gen.generate_users(1000)

        valid_plans = {"free", "starter", "pro", "enterprise"}
        plans = set(users.column("plan").to_pylist())

        assert plans.issubset(valid_plans)

    def test_generate_events_schema(self) -> None:
        """Generated events have correct schema."""
        gen = SaaSGenerator(seed=42)
        events = gen.generate_events(100)

        assert isinstance(events, pa.Table)
        assert len(events) == 100

        expected_columns = {
            "event_id",
            "user_id",
            "event_type",
            "properties",
            "timestamp",
            "session_id",
        }
        assert set(events.column_names) == expected_columns

    def test_events_reference_existing_users(self) -> None:
        """Events reference generated user IDs."""
        gen = SaaSGenerator(seed=42)

        users = gen.generate_users(100)
        user_ids = set(users.column("user_id").to_pylist())

        events = gen.generate_events(500)
        event_user_ids = set(events.column("user_id").to_pylist())

        assert event_user_ids.issubset(user_ids)

    def test_generate_subscriptions_for_all_users(self) -> None:
        """Subscriptions are generated for all users."""
        gen = SaaSGenerator(seed=42)

        users = gen.generate_users(50)
        subscriptions = gen.generate_subscriptions()

        assert len(subscriptions) == 50

        user_ids = set(users.column("user_id").to_pylist())
        sub_user_ids = set(subscriptions.column("user_id").to_pylist())

        assert sub_user_ids == user_ids

    def test_subscription_mrr_matches_plan(self) -> None:
        """Subscription MRR corresponds to plan pricing."""
        gen = SaaSGenerator(seed=42)

        gen.generate_users(100)
        subscriptions = gen.generate_subscriptions()

        # Check a sample
        for i in range(min(10, len(subscriptions))):
            plan = subscriptions.column("plan")[i].as_py()
            mrr = subscriptions.column("mrr")[i].as_py()

            expected_mrr = {
                "free": 0.0,
                "starter": 19.0,
                "pro": 49.0,
                "enterprise": 199.0,
            }

            assert mrr == expected_mrr[plan]

    def test_organizations_generated_with_users(self) -> None:
        """Organizations are generated when requested."""
        gen = SaaSGenerator(seed=42)

        users = gen.generate_users(100, with_organizations=True)

        # Some users should have organization_ids
        org_ids = users.column("organization_id").to_pylist()
        non_null_orgs = [oid for oid in org_ids if oid is not None]

        assert len(non_null_orgs) > 0
        assert len(gen._organization_ids) > 0

    def test_weighted_plan_distribution(self) -> None:
        """Custom plan weights are respected."""
        gen = SaaSGenerator(seed=42)

        users = gen.generate_users(
            10000,
            plan_weights={"free": 70, "pro": 30},
        )

        plans = users.column("plan").to_pylist()
        free_ratio = plans.count("free") / len(plans)

        # Should be approximately 70% free (±5%)
        assert 0.65 <= free_ratio <= 0.75


class TestGeneratorIntegration:
    """Integration tests for generator combinations."""

    def test_ecommerce_full_dataset(self) -> None:
        """Generate a complete e-commerce dataset."""
        gen = EcommerceGenerator(seed=42)

        customers = gen.generate_customers(100)
        products = gen.generate_products(50)
        orders = gen.generate_orders(500)

        assert len(customers) == 100
        assert len(products) == 50
        assert len(orders) == 500

        # Verify referential integrity
        customer_ids = set(customers.column("customer_id").to_pylist())
        order_customer_ids = set(orders.column("customer_id").to_pylist())
        assert order_customer_ids.issubset(customer_ids)

    def test_saas_full_dataset(self) -> None:
        """Generate a complete SaaS dataset."""
        gen = SaaSGenerator(seed=42)

        users = gen.generate_users(100, with_organizations=True)
        subscriptions = gen.generate_subscriptions()
        events = gen.generate_events(1000)

        assert len(users) == 100
        assert len(subscriptions) == 100
        assert len(events) == 1000

        # Verify referential integrity
        user_ids = set(users.column("user_id").to_pylist())
        event_user_ids = set(events.column("user_id").to_pylist())
        assert event_user_ids.issubset(user_ids)
