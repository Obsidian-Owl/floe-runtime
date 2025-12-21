"""Unit tests for storage preflight check implementations.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-core/tests/unit/preflight/test_storage_checks.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from floe_core.preflight.checks.storage import (
    ADLSCheck,
    GCSCheck,
    S3Check,
)
from floe_core.preflight.models import CheckStatus


class TestS3Check:
    """Tests for S3Check."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes with correct defaults."""
        check = S3Check()
        assert check.bucket is None
        assert check.region == "us-east-1"
        assert check.endpoint == S3Check.DEFAULT_ENDPOINT
        assert check.name == "storage_s3"

    @pytest.mark.requirement("007-FR-005")
    def test_custom_bucket_and_region(self) -> None:
        """Check accepts custom bucket and region."""
        check = S3Check(bucket="my-bucket", region="eu-west-1")
        assert check.bucket == "my-bucket"
        assert check.region == "eu-west-1"

    @pytest.mark.requirement("007-FR-005")
    def test_custom_endpoint(self) -> None:
        """Check accepts custom endpoint for LocalStack/MinIO."""
        check = S3Check(endpoint="http://localhost:4566")
        assert check.endpoint == "http://localhost:4566"

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

        check = S3Check(bucket="test-bucket", region="us-east-1")
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert "s3.us-east-1.amazonaws.com" in result.message
        assert result.details["bucket"] == "test-bucket"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    def test_dns_failure(self, mock_gethostbyname: MagicMock) -> None:
        """DNS failure returns FAILED."""
        import socket

        mock_gethostbyname.side_effect = socket.gaierror("DNS lookup failed")

        check = S3Check(region="us-east-1")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "DNS resolution failed" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    @patch("socket.socket")
    def test_connection_refused(
        self, mock_socket_class: MagicMock, mock_gethostbyname: MagicMock
    ) -> None:
        """Connection refused returns FAILED."""
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 111  # ECONNREFUSED
        mock_socket_class.return_value = mock_socket

        check = S3Check()
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "Cannot connect" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    @patch("socket.socket")
    def test_custom_endpoint_port_extraction(
        self, mock_socket_class: MagicMock, mock_gethostbyname: MagicMock
    ) -> None:
        """Custom endpoint with port is handled correctly."""
        mock_gethostbyname.return_value = "127.0.0.1"
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        check = S3Check(endpoint="http://localhost:4566")
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert result.details["host"] == "localhost"


class TestGCSCheck:
    """Tests for GCSCheck."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes with project ID."""
        check = GCSCheck(project_id="my-project")
        assert check.project_id == "my-project"
        assert check.bucket is None
        assert check.name == "storage_gcs"

    @pytest.mark.requirement("007-FR-005")
    def test_with_bucket(self) -> None:
        """Check accepts bucket name."""
        check = GCSCheck(project_id="my-project", bucket="my-bucket")
        assert check.bucket == "my-bucket"

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

        check = GCSCheck(project_id="my-project")
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert "my-project" in result.message
        assert result.details["api_host"] == GCSCheck.GCS_API_HOST

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    def test_dns_failure(self, mock_gethostbyname: MagicMock) -> None:
        """DNS failure returns FAILED."""
        import socket

        mock_gethostbyname.side_effect = socket.gaierror("DNS lookup failed")

        check = GCSCheck(project_id="my-project")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "DNS resolution failed" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    @patch("socket.socket")
    def test_connection_refused(
        self, mock_socket_class: MagicMock, mock_gethostbyname: MagicMock
    ) -> None:
        """Connection refused returns FAILED."""
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 111
        mock_socket_class.return_value = mock_socket

        check = GCSCheck(project_id="my-project")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "Cannot connect" in result.message


class TestADLSCheck:
    """Tests for ADLSCheck."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Check initializes with storage account."""
        check = ADLSCheck(storage_account="mystorageaccount")
        assert check.storage_account == "mystorageaccount"
        assert check.container is None
        assert check.name == "storage_adls"

    @pytest.mark.requirement("007-FR-005")
    def test_with_container(self) -> None:
        """Check accepts container name."""
        check = ADLSCheck(storage_account="mystorageaccount", container="mycontainer")
        assert check.container == "mycontainer"

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

        check = ADLSCheck(storage_account="mystorageaccount")
        result = check.run()

        assert result.status == CheckStatus.PASSED
        assert "mystorageaccount.dfs.core.windows.net" in result.message
        assert result.details["host"] == "mystorageaccount.dfs.core.windows.net"

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    def test_dns_failure(self, mock_gethostbyname: MagicMock) -> None:
        """DNS failure returns FAILED."""
        import socket

        mock_gethostbyname.side_effect = socket.gaierror("DNS lookup failed")

        check = ADLSCheck(storage_account="nonexistent")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "DNS resolution failed" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    @patch("socket.socket")
    def test_connection_refused(
        self, mock_socket_class: MagicMock, mock_gethostbyname: MagicMock
    ) -> None:
        """Connection refused returns FAILED."""
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 111
        mock_socket_class.return_value = mock_socket

        check = ADLSCheck(storage_account="mystorageaccount")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "Cannot connect" in result.message

    @pytest.mark.requirement("007-FR-005")
    @patch("socket.gethostbyname")
    @patch("socket.socket")
    def test_timeout(self, mock_socket_class: MagicMock, mock_gethostbyname: MagicMock) -> None:
        """Timeout returns FAILED."""
        mock_gethostbyname.return_value = "1.2.3.4"
        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = TimeoutError("Connection timed out")
        mock_socket_class.return_value = mock_socket

        check = ADLSCheck(storage_account="mystorageaccount")
        result = check.run()

        assert result.status == CheckStatus.FAILED
        assert "timed out" in result.message
