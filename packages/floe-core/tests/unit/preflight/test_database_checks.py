"""Unit tests for database preflight check implementations.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-core/tests/unit/preflight/test_database_checks.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from floe_core.preflight.checks.database import PostgresCheck
from floe_core.preflight.models import CheckStatus


class TestPostgresCheck:
    """Tests for PostgresCheck."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes with correct defaults."""
        check = PostgresCheck()
        assert check.host == "localhost"
        assert check.port == 5432
        assert check.database == "postgres"
        assert check.name == "database_postgres"

    @pytest.mark.requirement("007-FR-005")
    def test_custom_host_port_database(self) -> None:
        """Check accepts custom host, port, and database."""
        check = PostgresCheck(host="db.example.com", port=5433, database="dagster")
        assert check.host == "db.example.com"
        assert check.port == 5433
        assert check.database == "dagster"

    @pytest.mark.requirement("007-FR-005")
    def test_connection_string_parsing(self) -> None:
        """Check parses connection string correctly."""
        check = PostgresCheck(connection_string="postgresql://user:pass@db.example.com:5433/mydb")
        assert check.host == "db.example.com"
        assert check.port == 5433
        assert check.database == "mydb"

    @pytest.mark.requirement("007-FR-005")
    def test_connection_string_defaults(self) -> None:
        """Connection string with missing parts uses defaults."""
        check = PostgresCheck(connection_string="postgresql://localhost/")
        assert check.host == "localhost"
        assert check.port == 5432
        assert check.database == "postgres"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_successful_connection(self, mock_socket_class: MagicMock) -> None:
        """Successful connection returns PASSED."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = PostgresCheck(host="localhost", port=5432, database="dagster")
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert "localhost:5432" in result.message
        assert result.details["host"] == "localhost"
        assert result.details["port"] == 5432
        assert result.details["database"] == "dagster"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_connection_refused(self, mock_socket_class: MagicMock) -> None:
        """Connection refused returns FAILED."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 111  # ECONNREFUSED
        mock_socket_class.return_value = mock_socket

        check = PostgresCheck()
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "Cannot connect" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_dns_failure(self, mock_socket_class: MagicMock) -> None:
        """DNS failure returns FAILED."""
        import socket

        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = socket.gaierror("DNS lookup failed")
        mock_socket_class.return_value = mock_socket

        check = PostgresCheck(host="nonexistent.example.com")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "DNS resolution failed" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_timeout(self, mock_socket_class: MagicMock) -> None:
        """Timeout returns FAILED."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = TimeoutError("Connection timed out")
        mock_socket_class.return_value = mock_socket

        check = PostgresCheck()
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "timed out" in result.message

    @pytest.mark.requirement("007-FR-005")
    def test_connection_string_overrides_explicit_params(self) -> None:
        """Connection string takes precedence over explicit parameters."""
        check = PostgresCheck(
            host="wrong.host.com",
            port=9999,
            database="wrong_db",
            connection_string="postgresql://correct.host.com:5432/correct_db",
        )
        assert check.host == "correct.host.com"
        assert check.port == 5432
        assert check.database == "correct_db"
