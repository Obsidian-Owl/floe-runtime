"""E-commerce schema definitions for synthetic data generation.

This module defines Pydantic models for e-commerce data:
- Customer: Customer entity with region for RLS testing
- Order: Order entity with foreign key to Customer
- Product: Product catalog entity

All models are immutable (frozen=True) and validate at construction time.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

# Valid values for categorical fields
RegionType = Literal["north", "south", "east", "west"]
OrderStatusType = Literal["pending", "processing", "completed", "cancelled"]
ProductCategoryType = Literal["electronics", "clothing", "home", "sports", "books"]


class Customer(BaseModel):
    """Customer entity for e-commerce demo.

    Attributes:
        customer_id: Unique customer identifier (positive integer)
        name: Full name of the customer
        email: Email address (validated format)
        region: Geographic region (north, south, east, west)
        created_at: Account creation timestamp

    Example:
        >>> customer = Customer(
        ...     customer_id=1,
        ...     name="John Doe",
        ...     email="john@example.com",
        ...     region="north",
        ...     created_at=datetime.now(),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    customer_id: int = Field(..., ge=1, description="Unique customer identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Full name")
    email: str = Field(
        ...,
        min_length=5,
        max_length=254,
        pattern=r"^[\w\.\-\+]+@[\w\.\-]+\.\w+$",
        description="Email address",
    )
    region: RegionType = Field(..., description="Geographic region for RLS")
    created_at: datetime = Field(..., description="Account creation timestamp")


class Order(BaseModel):
    """Order entity with foreign key to Customer.

    Attributes:
        order_id: Unique order identifier (positive integer)
        customer_id: Reference to Customer.customer_id
        status: Order status (pending, processing, completed, cancelled)
        region: Denormalized from Customer for RLS testing
        amount: Order total amount (positive decimal)
        created_at: Order creation timestamp

    Example:
        >>> order = Order(
        ...     order_id=1,
        ...     customer_id=100,
        ...     status="completed",
        ...     region="north",
        ...     amount=Decimal("99.99"),
        ...     created_at=datetime.now(),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: int = Field(..., ge=1, description="Unique order identifier")
    customer_id: int = Field(..., ge=1, description="Foreign key to Customer")
    status: OrderStatusType = Field(..., description="Order status")
    region: RegionType = Field(..., description="Denormalized region for RLS")
    amount: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=2,
        description="Order total amount",
    )
    created_at: datetime = Field(..., description="Order creation timestamp")


class OrderItem(BaseModel):
    """Order line item entity linking orders to products.

    Represents a single line item within an order, including quantity,
    pricing, and calculated subtotal. Added for 007-FR-027a (E2E demo).

    Attributes:
        order_item_id: Unique line item identifier
        order_id: Reference to parent Order.order_id
        product_id: Reference to Product.product_id
        quantity: Quantity ordered (positive integer)
        unit_price: Price per unit at time of order
        discount: Discount applied to this line item (default: 0)
        subtotal: Computed as quantity * unit_price - discount

    Example:
        >>> item = OrderItem(
        ...     order_item_id=1,
        ...     order_id=100,
        ...     product_id=50,
        ...     quantity=2,
        ...     unit_price=Decimal("49.99"),
        ...     discount=Decimal("5.00"),
        ... )
        >>> item.subtotal
        Decimal('94.98')
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    order_item_id: int = Field(..., ge=1, description="Unique line item identifier")
    order_id: int = Field(..., ge=1, description="Foreign key to Order")
    product_id: int = Field(..., ge=1, description="Foreign key to Product")
    quantity: int = Field(..., ge=1, description="Quantity ordered")
    unit_price: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=2,
        description="Price per unit at time of order",
    )
    discount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        decimal_places=2,
        description="Discount applied to line item",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal as quantity * unit_price - discount."""
        return (self.quantity * self.unit_price) - self.discount


class Product(BaseModel):
    """Product catalog entity.

    Attributes:
        product_id: Unique product identifier
        name: Product name
        category: Product category
        price: Product price (positive decimal)
        sku: Stock keeping unit (unique identifier)

    Example:
        >>> product = Product(
        ...     product_id=1,
        ...     name="Wireless Headphones",
        ...     category="electronics",
        ...     price=Decimal("149.99"),
        ...     sku="WH-001",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    product_id: int = Field(..., ge=1, description="Unique product identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    category: ProductCategoryType = Field(..., description="Product category")
    price: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=2,
        description="Product price",
    )
    sku: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[A-Z0-9\-]+$",
        description="Stock keeping unit",
    )
