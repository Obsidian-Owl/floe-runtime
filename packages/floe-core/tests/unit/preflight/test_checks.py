"""Unit tests for preflight check implementations.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-core/tests/unit/preflight/test_checks.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from floe_core.preflight.checks.base import BaseCheck
from floe_core.preflight.checks.compute import (
    BigQueryCheck,
    DuckDBCheck,
    SnowflakeCheck,
    TrinoCheck,
)
from floe_core.preflight.models import CheckResult, CheckStatus


class ConcreteCheck(BaseCheck):
    """Concrete implementation for testing BaseCheck."""

    def __init__(self, should_pass: bool = True, should_raise: bool = False) -> None:
        super().__init__(name="test_check", timeout_seconds=5)
        self.should_pass = should_pass
        self.should_raise = should_raise

    def _execute(self) -> CheckResult:
        if self.should_raise:
            raise ValueError("Test error")

        if self.should_pass:
            return self._make_result(
                status=CheckStatus.PASSED,
                message="Test passed",
            )
        else:
            return self._make_result(
                status=CheckStatus.FAILED,
                message="Test failed",
            )


class TestBaseCheck:
    """Tests for BaseCheck abstract class."""

    @pytest.mark.requirement("007-FR-005")
    def test_run_success(self) -> None:
        """Successful check returns PASSED status."""
        check = ConcreteCheck(should_pass=True)
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert result.name == "test_check"
        assert result.duration_ms >= 0
        assert result.timestamp is not None

    @pytest.mark.requirement("007-FR-005")
    def test_run_failure(self) -> None:
        """Failed check returns FAILED status."""
        check = ConcreteCheck(should_pass=False)
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert result.message == "Test failed"

    @pytest.mark.requirement("007-FR-005")
    def test_run_exception_handling(self) -> None:
        """Exceptions are caught and return ERROR status."""
        check = ConcreteCheck(should_raise=True)
        result = check.run()

        assert result.status == CheckStatus.ERROR
        assert "ValueError" in result.message
        assert result.details["error"] == "Test error"

    @pytest.mark.requirement("007-FR-005")
    def test_duration_tracking(self) -> None:
        """Duration is tracked in milliseconds."""
        check = ConcreteCheck()
        result = check.run()

        assert result.duration_ms >= 0
        assert isinstance(result.duration_ms, int)


class TestTrinoCheck:
    """Tests for TrinoCheck."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes with correct defaults."""
        check = TrinoCheck()
        assert check.host == "localhost"
        assert check.port == 8080
        assert check.name == "compute_trino"

    @pytest.mark.requirement("007-FR-005")
    def test_custom_host_port(self) -> None:
        """Check accepts custom host and port."""
        check = TrinoCheck(host="trino.example.com", port=443, catalog="iceberg")
        assert check.host == "trino.example.com"
        assert check.port == 443
        assert check.catalog == "iceberg"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_successful_connection(self, mock_socket_class: MagicMock) -> None:
        """Successful TCP connection returns PASSED."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = TrinoCheck(host="localhost", port=8080)

        # Mock urllib to avoid HTTP check
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check.run()

        assert result.status == CheckStatus.PASSED
        assert "localhost:8080" in result.message
        assert result.details["host"] == "localhost"
        assert result.details["port"] == 8080

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_connection_refused(self, mock_socket_class: MagicMock) -> None:
        """Connection refused returns FAILED."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 111  # ECONNREFUSED
        mock_socket_class.return_value = mock_socket

        check = TrinoCheck(host="localhost", port=8080)
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "Cannot connect" in result.message


class TestSnowflakeCheck:
    """Tests for SnowflakeCheck."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes with account."""
        check = SnowflakeCheck(account="myaccount")
        assert check.account == "myaccount"
        assert check.name == "compute_snowflake"

    @pytest.mark.requirement("007-FR-005")
    def test_with_region(self) -> None:
        """Check accepts region."""
        check = SnowflakeCheck(account="myaccount", region="us-east-1")
        assert check.region == "us-east-1"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    @patch("socket.socket")
    def test_successful_connection(
        self, mock_socket_class: MagicMock, mock_gethostbyname: MagicMock
    ) -> None:
        """Successful connection returns PASSED."""
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = SnowflakeCheck(account="myaccount")
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert "myaccount.snowflakecomputing.com" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    def test_dns_failure(self, mock_gethostbyname: MagicMock) -> None:
        """DNS failure returns FAILED."""
        import socket

        mock_gethostbyname.side_effect = socket.gaierror("DNS lookup failed")

        check = SnowflakeCheck(account="nonexistent")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "DNS resolution failed" in result.message


class TestBigQueryCheck:
    """Tests for BigQueryCheck."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes with project ID."""
        check = BigQueryCheck(project_id="my-project")
        assert check.project_id == "my-project"
        assert check.location == "US"
        assert check.name == "compute_bigquery"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    @patch("socket.socket")
    def test_successful_connection(
        self, mock_socket_class: MagicMock, mock_gethostbyname: MagicMock
    ) -> None:
        """Successful connection returns PASSED."""
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = BigQueryCheck(project_id="my-project")
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert "my-project" in result.message
        assert result.details["api_host"] == "bigquery.googleapis.com"


class TestDuckDBCheck:
    """Tests for DuckDBCheck."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes correctly."""
        check = DuckDBCheck()
        assert check.database_path is None
        assert check.name == "compute_duckdb"

    @pytest.mark.requirement("007-FR-005")
    def test_successful_check(self) -> None:
        """DuckDB check passes when package is available."""
        check = DuckDBCheck()
        result = check.run()

        # DuckDB should be installed in test environment
        assert result.status == CheckStatus.PASSED
        assert "DuckDB" in result.message
        assert "version" in result.details

    @pytest.mark.requirement("007-FR-005")
    def test_with_memory_database(self) -> None:
        """In-memory database works correctly."""
        check = DuckDBCheck(database_path=":memory:")
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert result.details["database_path"] == ":memory:"

    @pytest.mark.requirement("007-FR-005")
    @patch.dict("sys.modules", {"duckdb": None})
    def test_missing_package(self) -> None:
        """Missing DuckDB package returns FAILED."""
        # Force reimport to trigger ImportError
        with patch("builtins.__import__") as mock_import:

            def import_side_effect(name: str, *args: object, **kwargs: object) -> object:
                if name == "duckdb":
                    raise ImportError("No module named 'duckdb'")
                return MagicMock()

            mock_import.side_effect = import_side_effect

            check = DuckDBCheck()
            result = check.run()

            assert result.status == CheckStatus.FAILED
            assert "not installed" in result.message
