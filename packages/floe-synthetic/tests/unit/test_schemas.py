"""Unit tests for synthetic data schemas.

Tests for Pydantic schema validation:
- Valid construction
- Immutability (frozen models)
- Field validation (constraints, patterns)
- Type validation
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from floe_synthetic.schemas.ecommerce import Customer, Order, OrderItem, Product
from floe_synthetic.schemas.saas_metrics import Event, Subscription, User


class TestCustomerSchema:
    """Tests for Customer Pydantic model."""

    def test_valid_customer(self) -> None:
        """Create valid customer with all required fields."""
        customer = Customer(
            customer_id=1,
            name="John Doe",
            email="john@example.com",
            region="north",
            created_at=datetime(2025, 1, 1),
        )
        assert customer.customer_id == 1
        assert customer.name == "John Doe"
        assert customer.email == "john@example.com"
        assert customer.region == "north"

    def test_customer_frozen(self) -> None:
        """Customer model is immutable."""
        customer = Customer(
            customer_id=1,
            name="Jane Doe",
            email="jane@example.com",
            region="south",
            created_at=datetime(2025, 1, 1),
        )
        with pytest.raises(ValidationError):
            customer.name = "New Name"  # type: ignore[misc]

    def test_customer_invalid_region(self) -> None:
        """Invalid region raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                customer_id=1,
                name="Test",
                email="test@example.com",
                region="invalid",  # type: ignore[arg-type]
                created_at=datetime(2025, 1, 1),
            )
        assert "region" in str(exc_info.value)

    def test_customer_invalid_email(self) -> None:
        """Invalid email pattern raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                customer_id=1,
                name="Test",
                email="not-an-email",
                region="north",
                created_at=datetime(2025, 1, 1),
            )
        assert "email" in str(exc_info.value)

    def test_customer_invalid_id(self) -> None:
        """Non-positive customer_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                customer_id=0,
                name="Test",
                email="test@example.com",
                region="north",
                created_at=datetime(2025, 1, 1),
            )
        assert "customer_id" in str(exc_info.value)

    def test_customer_extra_field_forbidden(self) -> None:
        """Extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                customer_id=1,
                name="Test",
                email="test@example.com",
                region="north",
                created_at=datetime(2025, 1, 1),
                extra_field="value",  # type: ignore[call-arg]
            )
        assert "extra_field" in str(exc_info.value)


class TestOrderSchema:
    """Tests for Order Pydantic model."""

    def test_valid_order(self) -> None:
        """Create valid order with all required fields."""
        order = Order(
            order_id=1,
            customer_id=100,
            status="completed",
            region="east",
            amount=Decimal("99.99"),
            created_at=datetime(2025, 1, 1),
        )
        assert order.order_id == 1
        assert order.customer_id == 100
        assert order.status == "completed"
        assert order.amount == Decimal("99.99")

    def test_order_frozen(self) -> None:
        """Order model is immutable."""
        order = Order(
            order_id=1,
            customer_id=100,
            status="pending",
            region="west",
            amount=Decimal("50.00"),
            created_at=datetime(2025, 1, 1),
        )
        with pytest.raises(ValidationError):
            order.status = "completed"  # type: ignore[misc]

    def test_order_invalid_status(self) -> None:
        """Invalid status raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Order(
                order_id=1,
                customer_id=100,
                status="invalid",  # type: ignore[arg-type]
                region="north",
                amount=Decimal("50.00"),
                created_at=datetime(2025, 1, 1),
            )
        assert "status" in str(exc_info.value)

    def test_order_negative_amount(self) -> None:
        """Negative amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Order(
                order_id=1,
                customer_id=100,
                status="completed",
                region="north",
                amount=Decimal("-10.00"),
                created_at=datetime(2025, 1, 1),
            )
        assert "amount" in str(exc_info.value)


class TestOrderItemSchema:
    """Tests for OrderItem Pydantic model.

    Covers: 007-FR-027a (OrderItem schema for E2E demo)
    """

    @pytest.mark.requirement("007-FR-027a")
    def test_valid_order_item(self) -> None:
        """Create valid order item with all required fields."""
        order_item = OrderItem(
            order_item_id=1,
            order_id=100,
            product_id=50,
            quantity=2,
            unit_price=Decimal("49.99"),
            discount=Decimal("5.00"),
        )
        assert order_item.order_item_id == 1
        assert order_item.order_id == 100
        assert order_item.product_id == 50
        assert order_item.quantity == 2
        assert order_item.unit_price == Decimal("49.99")
        assert order_item.discount == Decimal("5.00")
        # subtotal = quantity * unit_price - discount = 2 * 49.99 - 5.00 = 94.98
        assert order_item.subtotal == Decimal("94.98")

    @pytest.mark.requirement("007-FR-027a")
    def test_order_item_default_discount(self) -> None:
        """OrderItem discount defaults to 0."""
        order_item = OrderItem(
            order_item_id=1,
            order_id=100,
            product_id=50,
            quantity=1,
            unit_price=Decimal("29.99"),
        )
        assert order_item.discount == Decimal("0.00")
        assert order_item.subtotal == Decimal("29.99")

    @pytest.mark.requirement("007-FR-027a")
    def test_order_item_frozen(self) -> None:
        """OrderItem model is immutable."""
        order_item = OrderItem(
            order_item_id=1,
            order_id=100,
            product_id=50,
            quantity=1,
            unit_price=Decimal("10.00"),
        )
        with pytest.raises(ValidationError):
            order_item.quantity = 5  # type: ignore[misc]

    @pytest.mark.requirement("007-FR-027a")
    def test_order_item_invalid_quantity(self) -> None:
        """Non-positive quantity raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OrderItem(
                order_item_id=1,
                order_id=100,
                product_id=50,
                quantity=0,
                unit_price=Decimal("10.00"),
            )
        assert "quantity" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-027a")
    def test_order_item_negative_price(self) -> None:
        """Negative unit_price raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OrderItem(
                order_item_id=1,
                order_id=100,
                product_id=50,
                quantity=1,
                unit_price=Decimal("-10.00"),
            )
        assert "unit_price" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-027a")
    def test_order_item_negative_discount(self) -> None:
        """Negative discount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OrderItem(
                order_item_id=1,
                order_id=100,
                product_id=50,
                quantity=1,
                unit_price=Decimal("10.00"),
                discount=Decimal("-5.00"),
            )
        assert "discount" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-027a")
    def test_order_item_extra_field_forbidden(self) -> None:
        """Extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OrderItem(
                order_item_id=1,
                order_id=100,
                product_id=50,
                quantity=1,
                unit_price=Decimal("10.00"),
                extra_field="value",  # type: ignore[call-arg]
            )
        assert "extra_field" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-027a")
    def test_order_item_subtotal_calculation(self) -> None:
        """Subtotal is correctly calculated from quantity, unit_price, discount."""
        # Test various combinations
        test_cases = [
            (1, Decimal("100.00"), Decimal("0.00"), Decimal("100.00")),
            (2, Decimal("50.00"), Decimal("0.00"), Decimal("100.00")),
            (3, Decimal("33.33"), Decimal("0.00"), Decimal("99.99")),
            (1, Decimal("100.00"), Decimal("10.00"), Decimal("90.00")),
            (5, Decimal("20.00"), Decimal("25.00"), Decimal("75.00")),
        ]
        for qty, price, discount, expected in test_cases:
            order_item = OrderItem(
                order_item_id=1,
                order_id=1,
                product_id=1,
                quantity=qty,
                unit_price=price,
                discount=discount,
            )
            assert order_item.subtotal == expected, (
                f"Expected {expected} for qty={qty}, price={price}, discount={discount}"
            )


class TestProductSchema:
    """Tests for Product Pydantic model."""

    def test_valid_product(self) -> None:
        """Create valid product with all required fields."""
        product = Product(
            product_id=1,
            name="Wireless Headphones",
            category="electronics",
            price=Decimal("149.99"),
            sku="WH-001",
        )
        assert product.product_id == 1
        assert product.name == "Wireless Headphones"
        assert product.category == "electronics"
        assert product.price == Decimal("149.99")
        assert product.sku == "WH-001"

    def test_product_frozen(self) -> None:
        """Product model is immutable."""
        product = Product(
            product_id=1,
            name="Test Product",
            category="clothing",
            price=Decimal("29.99"),
            sku="TP-001",
        )
        with pytest.raises(ValidationError):
            product.price = Decimal("39.99")  # type: ignore[misc]

    def test_product_invalid_category(self) -> None:
        """Invalid category raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Product(
                product_id=1,
                name="Test",
                category="invalid",  # type: ignore[arg-type]
                price=Decimal("10.00"),
                sku="TEST-001",
            )
        assert "category" in str(exc_info.value)

    def test_product_invalid_sku_pattern(self) -> None:
        """SKU with lowercase letters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Product(
                product_id=1,
                name="Test",
                category="electronics",
                price=Decimal("10.00"),
                sku="invalid-sku",  # lowercase not allowed
            )
        assert "sku" in str(exc_info.value)


class TestUserSchema:
    """Tests for User Pydantic model."""

    def test_valid_user(self) -> None:
        """Create valid user with all required fields."""
        user = User(
            user_id=1,
            email="user@company.com",
            name="Alice Smith",
            plan="pro",
            organization_id=100,
            signup_date=datetime(2025, 1, 1),
            last_active_at=datetime(2025, 1, 15),
        )
        assert user.user_id == 1
        assert user.email == "user@company.com"
        assert user.plan == "pro"
        assert user.organization_id == 100

    def test_user_optional_organization(self) -> None:
        """User can be created without organization_id."""
        user = User(
            user_id=1,
            email="solo@user.com",
            name="Solo User",
            plan="free",
            signup_date=datetime(2025, 1, 1),
            last_active_at=datetime(2025, 1, 1),
        )
        assert user.organization_id is None

    def test_user_frozen(self) -> None:
        """User model is immutable."""
        user = User(
            user_id=1,
            email="test@test.com",
            name="Test User",
            plan="starter",
            signup_date=datetime(2025, 1, 1),
            last_active_at=datetime(2025, 1, 1),
        )
        with pytest.raises(ValidationError):
            user.plan = "enterprise"  # type: ignore[misc]

    def test_user_invalid_plan(self) -> None:
        """Invalid plan raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            User(
                user_id=1,
                email="test@test.com",
                name="Test",
                plan="invalid",  # type: ignore[arg-type]
                signup_date=datetime(2025, 1, 1),
                last_active_at=datetime(2025, 1, 1),
            )
        assert "plan" in str(exc_info.value)


class TestEventSchema:
    """Tests for Event Pydantic model."""

    def test_valid_event(self) -> None:
        """Create valid event with all fields."""
        event = Event(
            event_id=1,
            user_id=100,
            event_type="feature_use",
            properties={"feature": "dashboard", "duration_ms": 5000},
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            session_id="sess_abc123",
        )
        assert event.event_id == 1
        assert event.user_id == 100
        assert event.event_type == "feature_use"
        assert event.properties["feature"] == "dashboard"
        assert event.session_id == "sess_abc123"

    def test_event_default_properties(self) -> None:
        """Event properties default to empty dict."""
        event = Event(
            event_id=1,
            user_id=100,
            event_type="login",
            timestamp=datetime(2025, 1, 1),
        )
        assert event.properties == {}
        assert event.session_id is None

    def test_event_frozen(self) -> None:
        """Event model is immutable."""
        event = Event(
            event_id=1,
            user_id=100,
            event_type="page_view",
            timestamp=datetime(2025, 1, 1),
        )
        with pytest.raises(ValidationError):
            event.event_type = "logout"  # type: ignore[misc]

    def test_event_invalid_type(self) -> None:
        """Invalid event_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Event(
                event_id=1,
                user_id=100,
                event_type="invalid",  # type: ignore[arg-type]
                timestamp=datetime(2025, 1, 1),
            )
        assert "event_type" in str(exc_info.value)

    def test_event_all_event_types(self) -> None:
        """All valid event types work."""
        valid_types = [
            "page_view",
            "feature_use",
            "api_call",
            "login",
            "logout",
            "signup",
            "upgrade",
            "downgrade",
        ]
        for event_type in valid_types:
            event = Event(
                event_id=1,
                user_id=1,
                event_type=event_type,  # type: ignore[arg-type]
                timestamp=datetime(2025, 1, 1),
            )
            assert event.event_type == event_type


class TestSubscriptionSchema:
    """Tests for Subscription Pydantic model."""

    def test_valid_subscription(self) -> None:
        """Create valid subscription with all fields."""
        subscription = Subscription(
            subscription_id=1,
            user_id=100,
            plan="pro",
            mrr=Decimal("49.00"),
            status="active",
            started_at=datetime(2025, 1, 1),
            ended_at=None,
            trial_ends_at=datetime(2025, 1, 15),
        )
        assert subscription.subscription_id == 1
        assert subscription.plan == "pro"
        assert subscription.mrr == Decimal("49.00")
        assert subscription.status == "active"

    def test_subscription_optional_dates(self) -> None:
        """Subscription can be created without optional dates."""
        subscription = Subscription(
            subscription_id=1,
            user_id=100,
            plan="free",
            mrr=Decimal("0.00"),
            status="active",
            started_at=datetime(2025, 1, 1),
        )
        assert subscription.ended_at is None
        assert subscription.trial_ends_at is None

    def test_subscription_frozen(self) -> None:
        """Subscription model is immutable."""
        subscription = Subscription(
            subscription_id=1,
            user_id=100,
            plan="starter",
            mrr=Decimal("19.00"),
            status="active",
            started_at=datetime(2025, 1, 1),
        )
        with pytest.raises(ValidationError):
            subscription.status = "churned"  # type: ignore[misc]

    def test_subscription_invalid_status(self) -> None:
        """Invalid status raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Subscription(
                subscription_id=1,
                user_id=100,
                plan="pro",
                mrr=Decimal("49.00"),
                status="invalid",  # type: ignore[arg-type]
                started_at=datetime(2025, 1, 1),
            )
        assert "status" in str(exc_info.value)

    def test_subscription_all_statuses(self) -> None:
        """All valid subscription statuses work."""
        valid_statuses = ["active", "churned", "trial", "cancelled", "past_due"]
        for status in valid_statuses:
            subscription = Subscription(
                subscription_id=1,
                user_id=1,
                plan="free",
                mrr=Decimal("0.00"),
                status=status,  # type: ignore[arg-type]
                started_at=datetime(2025, 1, 1),
            )
            assert subscription.status == status

    def test_subscription_negative_mrr(self) -> None:
        """Negative MRR raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Subscription(
                subscription_id=1,
                user_id=100,
                plan="pro",
                mrr=Decimal("-10.00"),
                status="active",
                started_at=datetime(2025, 1, 1),
            )
        assert "mrr" in str(exc_info.value)
