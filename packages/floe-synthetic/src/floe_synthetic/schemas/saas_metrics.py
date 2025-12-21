"""SaaS metrics schema definitions for synthetic data generation.

This module defines Pydantic models for SaaS application data:
- User: User entity with subscription plan
- Event: User activity events for analytics
- Subscription: Subscription lifecycle tracking

All models are immutable (frozen=True) and validate at construction time.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Valid values for categorical fields
PlanType = Literal["free", "starter", "pro", "enterprise"]
SubscriptionStatusType = Literal["active", "churned", "trial", "cancelled", "past_due"]
EventType = Literal[
    "page_view",
    "feature_use",
    "api_call",
    "login",
    "logout",
    "signup",
    "upgrade",
    "downgrade",
]


class User(BaseModel):
    """User entity for SaaS metrics demo.

    Attributes:
        user_id: Unique user identifier
        email: User email address
        name: Display name
        plan: Current subscription plan
        organization_id: Optional organization for multi-tenant demos
        signup_date: Account creation date
        last_active_at: Last activity timestamp

    Example:
        >>> user = User(
        ...     user_id=1,
        ...     email="user@company.com",
        ...     name="Alice Smith",
        ...     plan="pro",
        ...     organization_id=100,
        ...     signup_date=datetime.now(),
        ...     last_active_at=datetime.now(),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: int = Field(..., ge=1, description="Unique user identifier")
    email: str = Field(
        ...,
        min_length=5,
        max_length=254,
        pattern=r"^[\w\.\-\+]+@[\w\.\-]+\.\w+$",
        description="Email address",
    )
    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    plan: PlanType = Field(..., description="Subscription plan")
    organization_id: int | None = Field(
        default=None,
        ge=1,
        description="Organization ID for multi-tenant",
    )
    signup_date: datetime = Field(..., description="Account creation date")
    last_active_at: datetime = Field(..., description="Last activity timestamp")


class Event(BaseModel):
    """User activity event for analytics.

    Attributes:
        event_id: Unique event identifier
        user_id: Foreign key to User
        event_type: Type of event (page_view, feature_use, etc.)
        properties: Event-specific metadata
        timestamp: When the event occurred
        session_id: Optional session identifier

    Example:
        >>> event = Event(
        ...     event_id=1,
        ...     user_id=100,
        ...     event_type="feature_use",
        ...     properties={"feature": "dashboard", "duration_ms": 5000},
        ...     timestamp=datetime.now(),
        ...     session_id="sess_abc123",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: int = Field(..., ge=1, description="Unique event identifier")
    user_id: int = Field(..., ge=1, description="Foreign key to User")
    event_type: EventType = Field(..., description="Type of event")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific metadata",
    )
    timestamp: datetime = Field(..., description="Event timestamp")
    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Session identifier",
    )


class Subscription(BaseModel):
    """Subscription lifecycle tracking.

    Attributes:
        subscription_id: Unique subscription identifier
        user_id: Foreign key to User
        plan: Subscription plan
        mrr: Monthly recurring revenue
        status: Subscription status
        started_at: Subscription start date
        ended_at: Subscription end date (for churned/cancelled)
        trial_ends_at: Trial period end date

    Example:
        >>> subscription = Subscription(
        ...     subscription_id=1,
        ...     user_id=100,
        ...     plan="pro",
        ...     mrr=Decimal("49.00"),
        ...     status="active",
        ...     started_at=datetime.now(),
        ...     ended_at=None,
        ...     trial_ends_at=None,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    subscription_id: int = Field(..., ge=1, description="Unique subscription identifier")
    user_id: int = Field(..., ge=1, description="Foreign key to User")
    plan: PlanType = Field(..., description="Subscription plan")
    mrr: Decimal = Field(
        ...,
        ge=Decimal("0"),
        decimal_places=2,
        description="Monthly recurring revenue",
    )
    status: SubscriptionStatusType = Field(..., description="Subscription status")
    started_at: datetime = Field(..., description="Subscription start date")
    ended_at: datetime | None = Field(
        default=None,
        description="Subscription end date",
    )
    trial_ends_at: datetime | None = Field(
        default=None,
        description="Trial period end date",
    )
