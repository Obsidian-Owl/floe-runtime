"""Temporal distribution utilities.

This module provides helpers for creating realistic time-series patterns
including daily/weekly seasonality, trends, and noise.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from typing import Any


class TemporalDistribution:
    """Helper for generating time-series data with realistic patterns.

    Supports:
    - Daily seasonality (business hours peaks)
    - Weekly seasonality (weekday/weekend patterns)
    - Linear trends (growth/decline)
    - Random noise

    Example:
        >>> temporal = TemporalDistribution(
        ...     daily_peak_hours=(10, 14, 18, 21),
        ...     weekend_factor=0.3,
        ...     trend_percent=0.02,
        ... )
        >>> count = temporal.adjusted_count(base_count=100, date=datetime.now())
    """

    def __init__(
        self,
        daily_peak_hours: tuple[int, ...] = (10, 14, 18, 21),
        weekend_factor: float = 0.3,
        trend_percent: float = 0.0,
        noise_percent: float = 0.1,
        seed: int | None = None,
    ) -> None:
        """Initialize temporal distribution.

        Args:
            daily_peak_hours: Hours of day with peak activity (0-23)
            weekend_factor: Multiplier for weekend activity (0.0-1.0)
            trend_percent: Monthly growth rate (0.02 = 2% growth)
            noise_percent: Random variation (0.1 = ±10%)
            seed: Random seed for reproducibility
        """
        self.daily_peak_hours = daily_peak_hours
        self.weekend_factor = weekend_factor
        self.trend_percent = trend_percent
        self.noise_percent = noise_percent
        self._rng = random.Random(seed)

    def daily_factor(self, hour: int) -> float:
        """Calculate activity factor based on hour of day.

        Args:
            hour: Hour of day (0-23)

        Returns:
            Multiplier for base activity (0.0-1.0)
        """
        # Simple model: peaks at specified hours, low at night
        if 0 <= hour < 6:
            return 0.1  # Night: very low
        elif 6 <= hour < 9:
            return 0.5 + (hour - 6) * 0.15  # Morning ramp-up
        elif hour in self.daily_peak_hours:
            return 1.0  # Peak hours
        elif 9 <= hour < 18:
            return 0.7  # Business hours
        elif 18 <= hour < 22:
            return 0.8  # Evening
        else:
            return 0.3  # Late night

    def weekly_factor(self, weekday: int) -> float:
        """Calculate activity factor based on day of week.

        Args:
            weekday: Day of week (0=Monday, 6=Sunday)

        Returns:
            Multiplier for base activity
        """
        if weekday >= 5:  # Weekend
            return self.weekend_factor
        elif weekday == 0:  # Monday
            return 0.9  # Slightly lower
        elif weekday == 4:  # Friday
            return 0.85  # End of week slowdown
        else:
            return 1.0  # Tue-Thu: peak

    def trend_factor(self, date: datetime, base_date: datetime | None = None) -> float:
        """Calculate trend factor based on time elapsed.

        Args:
            date: Current date
            base_date: Reference date for trend calculation

        Returns:
            Multiplier based on trend
        """
        if self.trend_percent == 0:
            return 1.0

        base = base_date or datetime(2024, 1, 1)
        months_elapsed = (date.year - base.year) * 12 + (date.month - base.month)
        return 1.0 + (self.trend_percent * months_elapsed)

    def noise_factor(self) -> float:
        """Generate random noise factor.

        Returns:
            Multiplier with random variation
        """
        return 1.0 + self._rng.uniform(-self.noise_percent, self.noise_percent)

    def combined_factor(
        self,
        dt: datetime,
        base_date: datetime | None = None,
    ) -> float:
        """Calculate combined factor for all temporal patterns.

        Args:
            dt: DateTime to calculate factor for
            base_date: Reference date for trend

        Returns:
            Combined multiplier
        """
        daily = self.daily_factor(dt.hour)
        weekly = self.weekly_factor(dt.weekday())
        trend = self.trend_factor(dt, base_date)
        noise = self.noise_factor()

        return daily * weekly * trend * noise

    def adjusted_count(
        self,
        base_count: int,
        date: datetime,
        base_date: datetime | None = None,
    ) -> int:
        """Calculate adjusted record count for a given date.

        Args:
            base_count: Base number of records
            date: Date to generate for
            base_date: Reference date for trend

        Returns:
            Adjusted count based on temporal factors
        """
        factor = self.combined_factor(date, base_date)
        return max(1, int(base_count * factor))

    def generate_timestamps(
        self,
        count: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[datetime]:
        """Generate timestamps with realistic intraday distribution.

        Args:
            count: Number of timestamps to generate
            start_date: Start of time range
            end_date: End of time range

        Returns:
            List of timestamps weighted toward peak hours
        """
        timestamps: list[datetime] = []
        total_seconds = int((end_date - start_date).total_seconds())

        for _ in range(count):
            # Generate random timestamp
            random_seconds = self._rng.randint(0, total_seconds)
            ts = start_date + timedelta(seconds=random_seconds)

            # Weight toward peak hours using rejection sampling
            hour_factor = self.daily_factor(ts.hour)
            if self._rng.random() < hour_factor:
                timestamps.append(ts)
            else:
                # Retry with slight offset toward peak hours
                peak_hour = self._rng.choice(self.daily_peak_hours)
                ts = ts.replace(hour=peak_hour, minute=self._rng.randint(0, 59))
                timestamps.append(ts)

        return sorted(timestamps)


# Pre-configured temporal distributions
BUSINESS_HOURS_DISTRIBUTION = TemporalDistribution(
    daily_peak_hours=(10, 11, 14, 15),
    weekend_factor=0.1,
)

ECOMMERCE_DISTRIBUTION = TemporalDistribution(
    daily_peak_hours=(10, 12, 19, 20, 21),
    weekend_factor=0.8,  # Higher weekend activity for e-commerce
)

SAAS_DISTRIBUTION = TemporalDistribution(
    daily_peak_hours=(9, 10, 14, 15, 16),
    weekend_factor=0.2,
    trend_percent=0.03,  # 3% monthly growth
)
