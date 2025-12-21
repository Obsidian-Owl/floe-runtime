"""Preflight result models.

Models for representing preflight check results.

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CheckStatus(str, Enum):
    """Status of a preflight check.

    Attributes:
        PASSED: Check passed successfully
        FAILED: Check failed
        SKIPPED: Check was skipped (disabled)
        WARNING: Check passed with warnings
        ERROR: Check encountered an error
    """

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"
    ERROR = "error"


class CheckResult(BaseModel):
    """Result of a single preflight check.

    Attributes:
        name: Check name (e.g., "compute", "storage")
        status: Check status
        message: Human-readable result message
        details: Additional details (connection info, errors, etc.)
        duration_ms: Check duration in milliseconds
        timestamp: When the check was performed

    Example:
        >>> result = CheckResult(
        ...     name="compute",
        ...     status=CheckStatus.PASSED,
        ...     message="Trino connection successful",
        ...     duration_ms=150,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., min_length=1, description="Check name")
    status: CheckStatus = Field(..., description="Check status")
    message: str = Field(default="", description="Result message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional details")
    duration_ms: int = Field(default=0, ge=0, description="Duration in milliseconds")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Check timestamp"
    )

    @property
    def passed(self) -> bool:
        """Check if result indicates success."""
        return self.status in (CheckStatus.PASSED, CheckStatus.SKIPPED, CheckStatus.WARNING)

    @property
    def failed(self) -> bool:
        """Check if result indicates failure."""
        return self.status in (CheckStatus.FAILED, CheckStatus.ERROR)


class PreflightResult(BaseModel):
    """Aggregated result of all preflight checks.

    Attributes:
        checks: List of individual check results
        overall_status: Overall preflight status
        started_at: When preflight started
        finished_at: When preflight finished
        total_duration_ms: Total duration in milliseconds

    Example:
        >>> result = PreflightResult(
        ...     checks=[
        ...         CheckResult(name="compute", status=CheckStatus.PASSED),
        ...         CheckResult(name="storage", status=CheckStatus.PASSED),
        ...     ],
        ...     overall_status=CheckStatus.PASSED,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    checks: list[CheckResult] = Field(default_factory=list, description="Check results")
    overall_status: CheckStatus = Field(default=CheckStatus.PASSED, description="Overall status")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Start time"
    )
    finished_at: datetime | None = Field(default=None, description="End time")
    total_duration_ms: int = Field(default=0, ge=0, description="Total duration")

    @property
    def passed(self) -> bool:
        """Check if all preflight checks passed."""
        return self.overall_status in (CheckStatus.PASSED, CheckStatus.WARNING)

    @property
    def failed(self) -> bool:
        """Check if any preflight check failed."""
        return self.overall_status in (CheckStatus.FAILED, CheckStatus.ERROR)

    @property
    def passed_count(self) -> int:
        """Count of passed checks."""
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        """Count of failed checks."""
        return sum(1 for c in self.checks if c.failed)


class PreflightReport(BaseModel):
    """Human-readable preflight report.

    Formats preflight results for display to users.

    Attributes:
        result: The preflight result
        summary: Short summary message
        recommendations: List of recommendations for failures

    Example:
        >>> report = PreflightReport(
        ...     result=preflight_result,
        ...     summary="All checks passed",
        ...     recommendations=[],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    result: PreflightResult = Field(..., description="Preflight result")
    summary: str = Field(default="", description="Summary message")
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations",
    )

    def to_text(self) -> str:
        """Generate text report.

        Returns:
            Formatted text report for CLI output.
        """
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("FLOE PREFLIGHT CHECK REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Summary
        status_icon = "✅" if self.result.passed else "❌"
        lines.append(f"Status: {status_icon} {self.result.overall_status.value.upper()}")
        lines.append(
            f"Checks: {self.result.passed_count} passed, {self.result.failed_count} failed"
        )
        lines.append(f"Duration: {self.result.total_duration_ms}ms")
        lines.append("")

        # Individual checks
        lines.append("-" * 60)
        lines.append("CHECKS:")
        lines.append("-" * 60)

        for check in self.result.checks:
            icon = "✅" if check.passed else "❌"
            lines.append(f"  {icon} {check.name}: {check.status.value}")
            if check.message:
                lines.append(f"     {check.message}")

        # Recommendations
        if self.recommendations:
            lines.append("")
            lines.append("-" * 60)
            lines.append("RECOMMENDATIONS:")
            lines.append("-" * 60)
            for rec in self.recommendations:
                lines.append(f"  • {rec}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
