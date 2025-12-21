"""Unit tests for catalog preflight check implementations.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-core/tests/unit/preflight/test_catalog_checks.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from floe_core.preflight.checks.catalog import PolarisCheck
from floe_core.preflight.models import CheckStatus


class TestPolarisCheck:
    """Tests for PolarisCheck."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes with correct defaults."""
        check = PolarisCheck()
        assert check.uri == "http://localhost:8181"
        assert check.catalog_name == "default"
        assert check.name == "catalog_polaris"

    @pytest.mark.requirement("007-FR-005")
    def test_custom_uri_and_catalog(self) -> None:
        """Check accepts custom URI and catalog name."""
        check = PolarisCheck(uri="https://polaris.example.com", catalog_name="production")
        assert check.uri == "https://polaris.example.com"
        assert check.catalog_name == "production"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_successful_connection(self, mock_socket_class: MagicMock) -> None:
        """Successful TCP connection returns PASSED."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = PolarisCheck(uri="http://localhost:8181")

        # Mock urllib to avoid HTTP check
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check.run()

        assert result.status == CheckStatus.PASSED
        assert "localhost" in result.message
        assert result.details["host"] == "localhost"
        assert result.details["port"] == 8181

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_connection_refused(self, mock_socket_class: MagicMock) -> None:
        """Connection refused returns FAILED."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 111  # ECONNREFUSED
        mock_socket_class.return_value = mock_socket

        check = PolarisCheck(uri="http://localhost:8181")
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

        check = PolarisCheck(uri="http://nonexistent.example.com:8181")
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

        check = PolarisCheck(uri="http://localhost:8181")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "timed out" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_https_uri_uses_port_443(self, mock_socket_class: MagicMock) -> None:
        """HTTPS URI defaults to port 443."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = PolarisCheck(uri="https://polaris.example.com")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check.run()

        assert result.status == CheckStatus.PASSED
        assert result.details["port"] == 443

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_custom_port_in_uri(self, mock_socket_class: MagicMock) -> None:
        """Custom port in URI is extracted correctly."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = PolarisCheck(uri="http://localhost:9999")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check.run()

        assert result.status == CheckStatus.PASSED
        assert result.details["port"] == 9999

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_http_check_failure_still_passes(self, mock_socket_class: MagicMock) -> None:
        """HTTP check failure doesn't fail overall check (TCP is sufficient)."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = PolarisCheck(uri="http://localhost:8181")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("HTTP failed")

            result = check.run()

        assert result.status == CheckStatus.PASSED
        assert result.details["api_status"] == "not_checked"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_api_health_check_included(self, mock_socket_class: MagicMock) -> None:
        """API health check status is included in details."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = PolarisCheck(uri="http://localhost:8181")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check.run()

        assert result.details["api_status"] == "healthy"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.socket")
    def test_unhealthy_api_status(self, mock_socket_class: MagicMock) -> None:
        """Unhealthy API status is reported."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = PolarisCheck(uri="http://localhost:8181")

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 503
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = check.run()

        assert result.status == CheckStatus.PASSED  # TCP worked
        assert "unhealthy" in result.details["api_status"]
