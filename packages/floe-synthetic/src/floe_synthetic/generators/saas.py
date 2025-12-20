"""SaaS metrics data generator using Faker.

This module provides the SaaSGenerator for generating realistic
SaaS application test data including users, events, and subscriptions.

Features:
- Deterministic seeding for reproducible tests
- Weighted distributions for realistic patterns
- Foreign key relationships maintained
- Event properties with realistic metadata
- MRR tracking for subscription analytics
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
    PLAN_WEIGHTS,
    SUBSCRIPTION_STATUS_WEIGHTS,
    DataGenerator,
)

# MRR by plan (monthly recurring revenue in USD)
PLAN_MRR: dict[str, Decimal] = {
    "free": Decimal("0.00"),
    "starter": Decimal("19.00"),
    "pro": Decimal("49.00"),
    "enterprise": Decimal("199.00"),
}

# Event type weights for realistic activity patterns
EVENT_TYPE_WEIGHTS: dict[str, float] = {
    "page_view": 50,
    "feature_use": 25,
    "api_call": 15,
    "login": 5,
    "logout": 3,
    "signup": 1,
    "upgrade": 0.5,
    "downgrade": 0.5,
}


class SaaSGenerator(DataGenerator):
    """Generator for SaaS metrics data with realistic distributions.

    Generates users, events, and subscriptions with proper relationships.
    Supports multi-tenant scenarios with organization_id.

    Attributes:
        seed: Random seed for reproducibility
        fake: Faker instance for data generation

    Example:
        >>> generator = SaaSGenerator(seed=42)
        >>> users = generator.generate_users(1000)
        >>> events = generator.generate_events(50000)
        >>> subscriptions = generator.generate_subscriptions()
    """

    def __init__(self, seed: int = 42) -> None:
        """Initialize the generator with a seed.

        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        # Use instance-level seeding for true reproducibility
        self.fake = Faker()
        self.fake.seed_instance(seed)
        # Track generated entities for foreign key relationships
        self._user_ids: list[int] = []
        self._user_plans: dict[int, str] = {}
        self._organization_ids: list[int] = []

    def generate_batch(self, count: int, **kwargs: Any) -> pa.Table:
        """Generate a batch of events (default entity).

        Args:
            count: Number of events to generate
            **kwargs: Additional options

        Returns:
            PyArrow Table with event data
        """
        return self.generate_events(count, **kwargs)

    def generate_stream(
        self,
        total: int,
        batch_size: int = 10000,
        **kwargs: Any,
    ) -> Iterator[pa.Table]:
        """Stream event batches for large datasets.

        Args:
            total: Total number of events to generate
            batch_size: Events per batch
            **kwargs: Options passed to generate_events

        Yields:
            PyArrow Tables with event data
        """
        for i in range(0, total, batch_size):
            current_batch = min(batch_size, total - i)
            yield self.generate_events(
                count=current_batch,
                start_id=i + 1,
                **kwargs,
            )

    def generate_organizations(
        self,
        count: int,
        *,
        start_id: int = 1,
    ) -> pa.Table:
        """Generate organization records for multi-tenant scenarios.

        Args:
            count: Number of organizations to generate
            start_id: Starting organization_id

        Returns:
            PyArrow Table with organization data
        """
        self._organization_ids = list(range(start_id, start_id + count))

        org_ids: list[int] = []
        names: list[str] = []
        industries: list[str] = []
        sizes: list[str] = []

        industries_list = [
            "technology",
            "finance",
            "healthcare",
            "retail",
            "manufacturing",
            "education",
        ]
        sizes_list = ["startup", "small", "medium", "large", "enterprise"]

        for i in range(count):
            org_ids.append(start_id + i)
            names.append(self.fake.company())
            industries.append(self.fake.random_element(elements=industries_list))
            sizes.append(self.fake.random_element(elements=sizes_list))

        self._log_generation("organizations", count)

        return pa.table(
            {
                "organization_id": pa.array(org_ids, type=pa.int64()),
                "name": pa.array(names, type=pa.string()),
                "industry": pa.array(industries, type=pa.string()),
                "size": pa.array(sizes, type=pa.string()),
            }
        )

    def generate_users(
        self,
        count: int,
        *,
        start_id: int = 1,
        plan_weights: dict[str, int] | None = None,
        with_organizations: bool = False,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pa.Table:
        """Generate user records with subscription plans.

        Args:
            count: Number of users to generate
            start_id: Starting user_id
            plan_weights: Custom plan distribution
            with_organizations: Assign users to organizations
            start_date: Earliest signup date
            end_date: Latest signup date

        Returns:
            PyArrow Table with user data
        """
        weights = plan_weights or PLAN_WEIGHTS
        plans = list(weights.keys())
        plan_probs = [w / sum(weights.values()) for w in weights.values()]

        start_date = start_date or datetime.now() - timedelta(days=730)
        end_date = end_date or datetime.now()

        # Generate organizations if needed
        if with_organizations and not self._organization_ids:
            self.generate_organizations(count // 10 + 1)

        self._user_ids = list(range(start_id, start_id + count))

        user_ids: list[int] = []
        emails: list[str] = []
        names: list[str] = []
        user_plans: list[str] = []
        organization_ids: list[int | None] = []
        signup_dates: list[datetime] = []
        last_active_ats: list[datetime] = []

        for i in range(count):
            user_id = start_id + i
            user_ids.append(user_id)
            emails.append(self.fake.email())
            names.append(self.fake.name())

            # Weighted plan selection (OrderedDict required by Faker)
            plan = self.fake.random_element(
                elements=OrderedDict(zip(plans, plan_probs, strict=True))
            )
            user_plans.append(plan)
            self._user_plans[user_id] = plan

            # Organization assignment
            if with_organizations and self._organization_ids:
                org_id: int | None = self.fake.random_element(self._organization_ids)
            else:
                org_id = None
            organization_ids.append(org_id)

            signup_date = self.fake.date_time_between(start_date=start_date, end_date=end_date)
            signup_dates.append(signup_date)

            # Last active somewhere between signup and now
            last_active = self.fake.date_time_between(
                start_date=signup_date, end_date=datetime.now()
            )
            last_active_ats.append(last_active)

        self._log_generation("users", count)

        return pa.table(
            {
                "user_id": pa.array(user_ids, type=pa.int64()),
                "email": pa.array(emails, type=pa.string()),
                "name": pa.array(names, type=pa.string()),
                "plan": pa.array(user_plans, type=pa.string()),
                "organization_id": pa.array(organization_ids, type=pa.int64()),
                "signup_date": pa.array(signup_dates, type=pa.timestamp("us")),
                "last_active_at": pa.array(last_active_ats, type=pa.timestamp("us")),
            }
        )

    def generate_events(
        self,
        count: int,
        *,
        start_id: int = 1,
        event_type_weights: dict[str, float] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pa.Table:
        """Generate user activity events.

        Args:
            count: Number of events to generate
            start_id: Starting event_id
            event_type_weights: Custom event type distribution
            start_date: Earliest event timestamp
            end_date: Latest event timestamp

        Returns:
            PyArrow Table with event data
        """
        # Generate users if none exist
        if not self._user_ids:
            self.generate_users(1000)

        weights = event_type_weights or EVENT_TYPE_WEIGHTS
        event_types = list(weights.keys())
        type_probs = [w / sum(weights.values()) for w in weights.values()]

        start_date = start_date or datetime.now() - timedelta(days=30)
        end_date = end_date or datetime.now()

        event_ids: list[int] = []
        user_ids: list[int] = []
        event_type_list: list[str] = []
        properties_list: list[str] = []  # JSON strings
        timestamps: list[datetime] = []
        session_ids: list[str | None] = []

        # Track sessions for continuity
        current_sessions: dict[int, str] = {}

        for i in range(count):
            event_ids.append(start_id + i)

            # Select user (active users generate more events)
            user_id = self.fake.random_element(self._user_ids)
            user_ids.append(user_id)

            # Weighted event type selection (OrderedDict required by Faker)
            event_type = self.fake.random_element(
                elements=OrderedDict(zip(event_types, type_probs, strict=True))
            )
            event_type_list.append(event_type)

            # Generate event-specific properties
            properties = self._generate_event_properties(event_type, user_id)
            properties_list.append(str(properties))

            timestamps.append(self.fake.date_time_between(start_date=start_date, end_date=end_date))

            # Session management
            session_id: str | None
            if event_type == "login":
                session_id = f"sess_{self.fake.uuid4()[:8]}"
                current_sessions[user_id] = session_id
            elif event_type == "logout":
                session_id = current_sessions.pop(user_id, "")
                if not session_id:
                    session_id = None
            else:
                session_id = current_sessions.get(user_id)

            session_ids.append(session_id)

        self._log_generation("events", count)

        return pa.table(
            {
                "event_id": pa.array(event_ids, type=pa.int64()),
                "user_id": pa.array(user_ids, type=pa.int64()),
                "event_type": pa.array(event_type_list, type=pa.string()),
                "properties": pa.array(properties_list, type=pa.string()),
                "timestamp": pa.array(timestamps, type=pa.timestamp("us")),
                "session_id": pa.array(session_ids, type=pa.string()),
            }
        )

    def generate_subscriptions(
        self,
        *,
        status_weights: dict[str, int] | None = None,
    ) -> pa.Table:
        """Generate subscription records for all users.

        Creates one subscription per user based on their plan.

        Args:
            status_weights: Custom status distribution

        Returns:
            PyArrow Table with subscription data
        """
        if not self._user_ids:
            self.generate_users(1000)

        weights = status_weights or SUBSCRIPTION_STATUS_WEIGHTS
        statuses = list(weights.keys())
        status_probs = [w / sum(weights.values()) for w in weights.values()]

        subscription_ids: list[int] = []
        user_ids: list[int] = []
        plans: list[str] = []
        mrrs: list[float] = []
        sub_statuses: list[str] = []
        started_ats: list[datetime] = []
        ended_ats: list[datetime | None] = []
        trial_ends_ats: list[datetime | None] = []

        for i, user_id in enumerate(self._user_ids):
            subscription_ids.append(i + 1)
            user_ids.append(user_id)

            plan = self._user_plans.get(user_id, "free")
            plans.append(plan)
            mrrs.append(float(PLAN_MRR.get(plan, Decimal("0.00"))))

            # Weighted status selection (OrderedDict required by Faker)
            status = self.fake.random_element(
                elements=OrderedDict(zip(statuses, status_probs, strict=True))
            )
            sub_statuses.append(status)

            started_at = self.fake.date_time_between(start_date="-2y", end_date="-30d")
            started_ats.append(started_at)

            # Set end date for churned/cancelled
            if status in ("churned", "cancelled"):
                ended_at: datetime | None = self.fake.date_time_between(
                    start_date=started_at, end_date="now"
                )
            else:
                ended_at = None
            ended_ats.append(ended_at)

            # Set trial end for trial subscriptions
            if status == "trial":
                trial_end: datetime | None = started_at + timedelta(days=14)
            else:
                trial_end = None
            trial_ends_ats.append(trial_end)

        self._log_generation("subscriptions", len(self._user_ids))

        return pa.table(
            {
                "subscription_id": pa.array(subscription_ids, type=pa.int64()),
                "user_id": pa.array(user_ids, type=pa.int64()),
                "plan": pa.array(plans, type=pa.string()),
                "mrr": pa.array(mrrs, type=pa.float64()),
                "status": pa.array(sub_statuses, type=pa.string()),
                "started_at": pa.array(started_ats, type=pa.timestamp("us")),
                "ended_at": pa.array(ended_ats, type=pa.timestamp("us")),
                "trial_ends_at": pa.array(trial_ends_ats, type=pa.timestamp("us")),
            }
        )

    def _generate_event_properties(self, event_type: str, _user_id: int) -> dict[str, Any]:
        """Generate realistic event properties based on event type.

        Args:
            event_type: Type of event
            _user_id: User generating the event (reserved for future use)

        Returns:
            Dictionary of event properties
        """
        properties: dict[str, Any] = {}

        if event_type == "page_view":
            pages = ["/dashboard", "/settings", "/billing", "/reports", "/profile"]
            properties["page"] = self.fake.random_element(elements=pages)
            properties["referrer"] = self.fake.random_element(
                elements=["direct", "search", "social", "email"]
            )
        elif event_type == "feature_use":
            features = ["export", "filter", "chart", "share", "notification"]
            properties["feature"] = self.fake.random_element(elements=features)
            properties["duration_ms"] = self.fake.random_int(100, 30000)
        elif event_type == "api_call":
            endpoints = ["/api/v1/data", "/api/v1/users", "/api/v1/reports"]
            properties["endpoint"] = self.fake.random_element(elements=endpoints)
            properties["status_code"] = self.fake.random_element(
                elements=[200, 200, 200, 201, 400, 401, 500]  # Mostly success
            )
            properties["latency_ms"] = self.fake.random_int(10, 500)
        elif event_type in ("upgrade", "downgrade"):
            plans = ["free", "starter", "pro", "enterprise"]
            properties["from_plan"] = self.fake.random_element(elements=plans)
            properties["to_plan"] = self.fake.random_element(elements=plans)

        properties["user_agent"] = self.fake.user_agent()
        return properties

    def reset(self) -> None:
        """Reset the generator state."""
        self._user_ids = []
        self._user_plans = {}
        self._organization_ids = []
        self.fake.seed_instance(self.seed)
