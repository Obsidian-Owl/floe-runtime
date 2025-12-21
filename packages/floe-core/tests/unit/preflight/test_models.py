"""Unit tests for preflight result models.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-core/tests/unit/preflight/test_models.py -v
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from floe_core.preflight.models import (
    CheckResult,
    CheckStatus,
    PreflightReport,
    PreflightResult,
)


class TestCheckStatus:
    """Tests for CheckStatus enum."""

    @pytest.mark.requirement("007-FR-005")
    def test_status_values(self) -> None:
        """All status values are defined."""
        assert CheckStatus.PASSED.value == "passed"
        assert CheckStatus.FAILED.value == "failed"
        assert CheckStatus.SKIPPED.value == "skipped"
        assert CheckStatus.WARNING.value == "warning"
        assert CheckStatus.ERROR.value == "error"


class TestCheckResult:
    """Tests for CheckResult model."""

    @pytest.mark.requirement("007-FR-005")
    def test_create_passed_result(self) -> None:
        """Create a passed check result."""
        result = CheckResult(
            name="compute",
            status=CheckStatus.PASSED,
            message="Connection successful",
            duration_ms=150,
        )
        assert result.name == "compute"
        assert result.status == CheckStatus.PASSED
        assert result.message == "Connection successful"
        assert result.duration_ms == 150
        assert result.passed is True
        assert result.failed is False

    @pytest.mark.requirement("007-FR-005")
    def test_create_failed_result(self) -> None:
        """Create a failed check result."""
        result = CheckResult(
            name="storage",
            status=CheckStatus.FAILED,
            message="Bucket not found",
        )
        assert result.passed is False
        assert result.failed is True

    @pytest.mark.requirement("007-FR-005")
    def test_skipped_counts_as_passed(self) -> None:
        """Skipped status counts as passed."""
        result = CheckResult(
            name="otel",
            status=CheckStatus.SKIPPED,
        )
        assert result.passed is True
        assert result.failed is False

    @pytest.mark.requirement("007-FR-005")
    def test_warning_counts_as_passed(self) -> None:
        """Warning status counts as passed."""
        result = CheckResult(
            name="catalog",
            status=CheckStatus.WARNING,
            message="Slow response time",
        )
        assert result.passed is True
        assert result.failed is False

    @pytest.mark.requirement("007-FR-005")
    def test_error_counts_as_failed(self) -> None:
        """Error status counts as failed."""
        result = CheckResult(
            name="postgres",
            status=CheckStatus.ERROR,
            message="Connection refused",
        )
        assert result.passed is False
        assert result.failed is True

    @pytest.mark.requirement("007-FR-005")
    def test_details_dict(self) -> None:
        """Result can include additional details."""
        result = CheckResult(
            name="compute",
            status=CheckStatus.PASSED,
            details={"host": "trino.example.com", "port": 8080},
        )
        assert result.details["host"] == "trino.example.com"
        assert result.details["port"] == 8080

    @pytest.mark.requirement("007-FR-005")
    def test_timestamp_auto_set(self) -> None:
        """Timestamp is automatically set."""
        result = CheckResult(name="test", status=CheckStatus.PASSED)
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

    @pytest.mark.requirement("007-FR-005")
    def test_name_required(self) -> None:
        """Name is required."""
        with pytest.raises(ValidationError) as exc_info:
            CheckResult(status=CheckStatus.PASSED)  # type: ignore[call-arg]
        assert "name" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-005")
    def test_name_min_length(self) -> None:
        """Name must have at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            CheckResult(name="", status=CheckStatus.PASSED)
        assert "name" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-005")
    def test_duration_non_negative(self) -> None:
        """Duration must be non-negative."""
        with pytest.raises(ValidationError):
            CheckResult(name="test", status=CheckStatus.PASSED, duration_ms=-1)


class TestPreflightResult:
    """Tests for PreflightResult model."""

    @pytest.mark.requirement("007-FR-005")
    def test_empty_result(self) -> None:
        """Empty result defaults to passed."""
        result = PreflightResult()
        assert result.passed is True
        assert result.failed is False
        assert result.passed_count == 0
        assert result.failed_count == 0

    @pytest.mark.requirement("007-FR-005")
    def test_all_checks_passed(self) -> None:
        """Result with all checks passed."""
        result = PreflightResult(
            checks=[
                CheckResult(name="compute", status=CheckStatus.PASSED),
                CheckResult(name="storage", status=CheckStatus.PASSED),
                CheckResult(name="catalog", status=CheckStatus.PASSED),
            ],
            overall_status=CheckStatus.PASSED,
        )
        assert result.passed is True
        assert result.passed_count == 3
        assert result.failed_count == 0

    @pytest.mark.requirement("007-FR-005")
    def test_some_checks_failed(self) -> None:
        """Result with some checks failed."""
        result = PreflightResult(
            checks=[
                CheckResult(name="compute", status=CheckStatus.PASSED),
                CheckResult(name="storage", status=CheckStatus.FAILED),
                CheckResult(name="catalog", status=CheckStatus.PASSED),
            ],
            overall_status=CheckStatus.FAILED,
        )
        assert result.passed is False
        assert result.failed is True
        assert result.passed_count == 2
        assert result.failed_count == 1

    @pytest.mark.requirement("007-FR-005")
    def test_warning_overall_counts_as_passed(self) -> None:
        """Overall warning status counts as passed."""
        result = PreflightResult(
            checks=[
                CheckResult(name="compute", status=CheckStatus.WARNING),
            ],
            overall_status=CheckStatus.WARNING,
        )
        assert result.passed is True
        assert result.failed is False

    @pytest.mark.requirement("007-FR-005")
    def test_duration_tracking(self) -> None:
        """Result tracks total duration."""
        result = PreflightResult(
            checks=[
                CheckResult(name="compute", status=CheckStatus.PASSED, duration_ms=100),
                CheckResult(name="storage", status=CheckStatus.PASSED, duration_ms=200),
            ],
            total_duration_ms=350,  # Includes overhead
        )
        assert result.total_duration_ms == 350


class TestPreflightReport:
    """Tests for PreflightReport model."""

    @pytest.mark.requirement("007-FR-005")
    def test_create_report(self) -> None:
        """Create a preflight report."""
        result = PreflightResult(
            checks=[
                CheckResult(name="compute", status=CheckStatus.PASSED, message="OK"),
            ],
            overall_status=CheckStatus.PASSED,
            total_duration_ms=150,
        )
        report = PreflightReport(
            result=result,
            summary="All checks passed",
            recommendations=[],
        )
        assert report.summary == "All checks passed"
        assert len(report.recommendations) == 0

    @pytest.mark.requirement("007-FR-005")
    def test_report_with_recommendations(self) -> None:
        """Report includes recommendations for failures."""
        result = PreflightResult(
            checks=[
                CheckResult(name="storage", status=CheckStatus.FAILED, message="Access denied"),
            ],
            overall_status=CheckStatus.FAILED,
        )
        report = PreflightReport(
            result=result,
            summary="Storage check failed",
            recommendations=[
                "Verify S3 bucket permissions",
                "Check IAM role has s3:GetObject permission",
            ],
        )
        assert len(report.recommendations) == 2

    @pytest.mark.requirement("007-FR-005")
    def test_to_text_passed(self) -> None:
        """Generate text report for passed result."""
        result = PreflightResult(
            checks=[
                CheckResult(name="compute", status=CheckStatus.PASSED, message="Trino OK"),
                CheckResult(name="storage", status=CheckStatus.PASSED, message="S3 OK"),
            ],
            overall_status=CheckStatus.PASSED,
            total_duration_ms=250,
        )
        report = PreflightReport(result=result)
        text = report.to_text()

        assert "FLOE PREFLIGHT CHECK REPORT" in text
        assert "PASSED" in text
        assert "2 passed" in text
        assert "0 failed" in text
        assert "compute" in text
        assert "storage" in text

    @pytest.mark.requirement("007-FR-005")
    def test_to_text_failed_with_recommendations(self) -> None:
        """Generate text report for failed result with recommendations."""
        result = PreflightResult(
            checks=[
                CheckResult(name="catalog", status=CheckStatus.FAILED, message="Timeout"),
            ],
            overall_status=CheckStatus.FAILED,
        )
        report = PreflightReport(
            result=result,
            recommendations=["Check Polaris is running"],
        )
        text = report.to_text()

        assert "FAILED" in text
        assert "1 failed" in text
        assert "RECOMMENDATIONS" in text
        assert "Check Polaris is running" in text
