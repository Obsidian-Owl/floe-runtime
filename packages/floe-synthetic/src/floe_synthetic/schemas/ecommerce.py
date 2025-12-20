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

from pydantic import BaseModel, ConfigDict, Field

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
