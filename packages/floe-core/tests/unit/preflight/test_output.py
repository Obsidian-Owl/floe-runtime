"""Unit tests for preflight output formatting.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-core/tests/unit/preflight/test_output.py -v
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from rich.console import Console

from floe_core.preflight.models import CheckResult, CheckStatus, PreflightResult
from floe_core.preflight.output import (
    format_result_json,
    format_result_table,
    print_result,
)


@pytest.fixture
def sample_checks() -> list[CheckResult]:
    """Create sample check results for testing."""
    return [
        CheckResult(
            name="compute_trino",
            status=CheckStatus.PASSED,
            message="Trino reachable at localhost:8080",
            duration_ms=150,
        ),
        CheckResult(
            name="storage_s3",
            status=CheckStatus.PASSED,
            message="S3 reachable at s3.us-east-1.amazonaws.com",
            duration_ms=200,
        ),
        CheckResult(
            name="catalog_polaris",
            status=CheckStatus.FAILED,
            message="Cannot connect to Polaris at localhost:8181",
            details={"host": "localhost", "port": 8181},
            duration_ms=50,
        ),
    ]


@pytest.fixture
def sample_result(sample_checks: list[CheckResult]) -> PreflightResult:
    """Create sample preflight result."""
    return PreflightResult(
        checks=sample_checks,
        overall_status=CheckStatus.FAILED,
        total_duration_ms=400,
    )


class TestFormatResultTable:
    """Tests for format_result_table."""

    @pytest.mark.requirement("007-FR-005")
    def test_outputs_to_console(self, sample_result: PreflightResult) -> None:
        """Table output is written to console."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        format_result_table(sample_result, console=console)

        content = output.getvalue()
        assert "FLOE PREFLIGHT CHECK REPORT" in content
        assert "compute_trino" in content
        assert "storage_s3" in content
        assert "catalog_polaris" in content

    @pytest.mark.requirement("007-FR-005")
    def test_shows_overall_status(self, sample_result: PreflightResult) -> None:
        """Table shows overall status."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        format_result_table(sample_result, console=console)

        content = output.getvalue()
        assert "FAILED" in content

    @pytest.mark.requirement("007-FR-005")
    def test_shows_pass_fail_counts(self, sample_result: PreflightResult) -> None:
        """Table shows pass/fail counts."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        format_result_table(sample_result, console=console)

        content = output.getvalue()
        assert "2 passed" in content
        assert "1 failed" in content

    @pytest.mark.requirement("007-FR-005")
    def test_shows_duration(self, sample_result: PreflightResult) -> None:
        """Table shows duration."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        format_result_table(sample_result, console=console)

        content = output.getvalue()
        assert "400ms" in content

    @pytest.mark.requirement("007-FR-005")
    def test_shows_failed_check_details(self, sample_result: PreflightResult) -> None:
        """Table shows failed check details."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        format_result_table(sample_result, console=console)

        content = output.getvalue()
        assert "Failed Check Details" in content
        assert "catalog_polaris" in content
        assert "host" in content

    @pytest.mark.requirement("007-FR-005")
    def test_creates_console_if_not_provided(self, sample_result: PreflightResult) -> None:
        """Creates console if not provided."""
        # Should not raise
        format_result_table(sample_result)


class TestFormatResultJson:
    """Tests for format_result_json."""

    @pytest.mark.requirement("007-FR-005")
    def test_returns_valid_json(self, sample_result: PreflightResult) -> None:
        """Returns valid JSON string."""
        json_str = format_result_json(sample_result)
        parsed = json.loads(json_str)

        assert parsed["status"] == "failed"
        assert parsed["passed"] is False
        assert len(parsed["checks"]) == 3

    @pytest.mark.requirement("007-FR-005")
    def test_includes_summary(self, sample_result: PreflightResult) -> None:
        """JSON includes summary section."""
        json_str = format_result_json(sample_result)
        parsed = json.loads(json_str)

        assert parsed["summary"]["total"] == 3
        assert parsed["summary"]["passed"] == 2
        assert parsed["summary"]["failed"] == 1

    @pytest.mark.requirement("007-FR-005")
    def test_includes_duration(self, sample_result: PreflightResult) -> None:
        """JSON includes duration."""
        json_str = format_result_json(sample_result)
        parsed = json.loads(json_str)

        assert parsed["duration_ms"] == 400

    @pytest.mark.requirement("007-FR-005")
    def test_includes_check_details(self, sample_result: PreflightResult) -> None:
        """JSON includes check details."""
        json_str = format_result_json(sample_result)
        parsed = json.loads(json_str)

        trino_check = next(c for c in parsed["checks"] if c["name"] == "compute_trino")
        assert trino_check["status"] == "passed"
        assert trino_check["duration_ms"] == 150

    @pytest.mark.requirement("007-FR-005")
    def test_includes_failed_check_details(self, sample_result: PreflightResult) -> None:
        """JSON includes details for failed checks."""
        json_str = format_result_json(sample_result)
        parsed = json.loads(json_str)

        polaris_check = next(c for c in parsed["checks"] if c["name"] == "catalog_polaris")
        assert polaris_check["details"]["host"] == "localhost"
        assert polaris_check["details"]["port"] == 8181

    @pytest.mark.requirement("007-FR-005")
    def test_pretty_format(self, sample_result: PreflightResult) -> None:
        """Pretty format uses indentation."""
        json_str = format_result_json(sample_result, pretty=True)
        assert "\n" in json_str
        assert "  " in json_str

    @pytest.mark.requirement("007-FR-005")
    def test_compact_format(self, sample_result: PreflightResult) -> None:
        """Compact format has no indentation."""
        json_str = format_result_json(sample_result, pretty=False)
        # Should be a single line with no indentation
        assert "\n" not in json_str


class TestPrintResult:
    """Tests for print_result."""

    @pytest.mark.requirement("007-FR-005")
    def test_table_format(self, sample_result: PreflightResult) -> None:
        """Uses table format by default."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)

        print_result(sample_result, output_format="table", console=console)

        content = output.getvalue()
        assert "FLOE PREFLIGHT CHECK REPORT" in content

    @pytest.mark.requirement("007-FR-005")
    def test_json_format(self, sample_result: PreflightResult) -> None:
        """Uses JSON format when specified."""
        output = StringIO()
        # Use no_color=True to avoid ANSI escape codes in JSON output
        console = Console(file=output, force_terminal=True, no_color=True)

        print_result(sample_result, output_format="json", console=console)

        content = output.getvalue()
        parsed = json.loads(content)
        assert parsed["status"] == "failed"

    @pytest.mark.requirement("007-FR-005")
    def test_all_passed_result(self) -> None:
        """Shows passed status when all checks pass."""
        result = PreflightResult(
            checks=[
                CheckResult(name="test1", status=CheckStatus.PASSED),
                CheckResult(name="test2", status=CheckStatus.PASSED),
            ],
            overall_status=CheckStatus.PASSED,
        )

        output = StringIO()
        console = Console(file=output, force_terminal=True)

        print_result(result, console=console)

        content = output.getvalue()
        assert "PASSED" in content
        assert "2 passed" in content
        assert "0 failed" in content
