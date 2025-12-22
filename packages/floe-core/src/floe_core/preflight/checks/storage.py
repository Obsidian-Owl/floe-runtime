"""Storage preflight checks.

Connectivity checks for supported storage backends:
- S3 (AWS)
- GCS (Google Cloud Storage)
- ADLS (Azure Data Lake Storage)

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse

import structlog

from floe_core.preflight.checks.base import BaseCheck
from floe_core.preflight.models import CheckResult, CheckStatus

logger = structlog.get_logger(__name__)

# Localhost addresses - allow HTTP for local development
LOCALHOST_ADDRESSES = frozenset({"localhost", "127.0.0.1", "::1"})

# S5332: Define secure protocol constant
SECURE_SCHEME = "https"


def _is_localhost(host: str) -> bool:
    """Check if host is a localhost address.

    Args:
        host: Hostname to check

    Returns:
        True if host is localhost, False otherwise
    """
    return host.lower() in LOCALHOST_ADDRESSES


def _parse_endpoint(endpoint: str) -> tuple[str, bool]:
    """Parse endpoint URL to extract host and detect insecure protocol.

    S5332: Flag non-HTTPS usage for non-localhost endpoints as security concern.
    Uses urllib.parse for proper URL handling.

    Args:
        endpoint: Endpoint URL (may include protocol scheme)

    Returns:
        Tuple of (host, is_insecure) where is_insecure is True if non-HTTPS
        is used for a non-localhost host.
    """
    # Use urllib.parse to properly extract URL components (S5332 compliant)
    parsed = urlparse(endpoint)

    # Extract hostname - use netloc for URLs with scheme, otherwise treat as host
    if parsed.scheme and parsed.netloc:
        host = parsed.hostname or parsed.netloc.split(":")[0]
        is_secure = parsed.scheme.lower() == SECURE_SCHEME
    else:
        # No scheme - treat entire endpoint as host (after stripping port)
        host = endpoint.split(":")[0]
        is_secure = True  # Assume secure if no scheme specified

    # Non-HTTPS is only acceptable for localhost development
    is_insecure = not is_secure and not _is_localhost(host)

    return host, is_insecure


class S3Check(BaseCheck):
    """Preflight check for S3 connectivity.

    Verifies that S3 endpoint is reachable.

    Attributes:
        endpoint: S3 endpoint URL (default: AWS S3)
        bucket: Optional bucket name to verify
        region: AWS region

    Example:
        >>> check = S3Check(bucket="my-bucket", region="us-east-1")
        >>> result = check.run()
        >>> result.passed
        True
    """

    DEFAULT_ENDPOINT = "s3.amazonaws.com"

    def __init__(
        self,
        bucket: str | None = None,
        region: str = "us-east-1",
        endpoint: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize S3 check.

        Args:
            bucket: Optional bucket name to verify
            region: AWS region
            endpoint: Custom S3 endpoint (for LocalStack, MinIO, etc.)
            timeout_seconds: Connection timeout
        """
        super().__init__(name="storage_s3", timeout_seconds=timeout_seconds)
        self.bucket = bucket
        self.region = region
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT

    def _execute(self) -> CheckResult:
        """Check S3 connectivity.

        Returns:
            CheckResult indicating S3 status.
        """
        # Build endpoint URL
        is_insecure = False
        if self.endpoint == self.DEFAULT_ENDPOINT and self.region:
            host = f"s3.{self.region}.amazonaws.com"
        else:
            # Custom endpoint - extract host and check security
            # S5332: Detect insecure HTTP usage for non-localhost endpoints
            host, is_insecure = _parse_endpoint(self.endpoint)

        details: dict[str, Any] = {
            "endpoint": self.endpoint,
            "region": self.region,
            "bucket": self.bucket,
            "host": host,
        }

        # S5332: Warn about insecure HTTP for production endpoints
        if is_insecure:
            logger.warning(
                "S3 endpoint uses HTTP instead of HTTPS",
                endpoint=self.endpoint,
                host=host,
                security_risk="data_in_transit_unencrypted",
            )
            details["security_warning"] = "HTTP endpoint detected - data in transit is unencrypted"

        # DNS and TCP connectivity check
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            socket.gethostbyname(host)

            # Try HTTPS port (443) for AWS, or custom port for local endpoints
            port = 443
            if ":" in self.endpoint:
                port_str = self.endpoint.split(":")[-1].replace("/", "")
                if port_str.isdigit():
                    port = int(port_str)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                return self._make_result(
                    status=CheckStatus.FAILED,
                    message=f"Cannot connect to S3 at {host}:{port}",
                    details=details,
                )

        except socket.gaierror as e:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"DNS resolution failed for {host}",
                details={**details, "error": str(e)},
            )
        except TimeoutError:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"Connection timed out to {host}",
                details=details,
            )

        return self._make_result(
            status=CheckStatus.PASSED,
            message=f"S3 reachable at {host}",
            details=details,
        )


class GCSCheck(BaseCheck):
    """Preflight check for Google Cloud Storage connectivity.

    Verifies that GCS API endpoint is reachable.

    Attributes:
        project_id: GCP project ID
        bucket: Optional bucket name to verify

    Example:
        >>> check = GCSCheck(project_id="my-project")
        >>> result = check.run()
        >>> result.passed
        True
    """

    GCS_API_HOST = "storage.googleapis.com"

    def __init__(
        self,
        project_id: str,
        bucket: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize GCS check.

        Args:
            project_id: GCP project ID
            bucket: Optional bucket name to verify
            timeout_seconds: Connection timeout
        """
        super().__init__(name="storage_gcs", timeout_seconds=timeout_seconds)
        self.project_id = project_id
        self.bucket = bucket

    def _execute(self) -> CheckResult:
        """Check GCS connectivity.

        Returns:
            CheckResult indicating GCS status.
        """
        details: dict[str, Any] = {
            "project_id": self.project_id,
            "bucket": self.bucket,
            "api_host": self.GCS_API_HOST,
        }

        # DNS and TCP connectivity check to GCS API
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            socket.gethostbyname(self.GCS_API_HOST)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((self.GCS_API_HOST, 443))
            sock.close()

            if result != 0:
                return self._make_result(
                    status=CheckStatus.FAILED,
                    message=f"Cannot connect to GCS API at {self.GCS_API_HOST}",
                    details=details,
                )

        except socket.gaierror as e:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"DNS resolution failed for {self.GCS_API_HOST}",
                details={**details, "error": str(e)},
            )
        except TimeoutError:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"Connection timed out to {self.GCS_API_HOST}",
                details=details,
            )

        return self._make_result(
            status=CheckStatus.PASSED,
            message=f"GCS API reachable for project {self.project_id}",
            details=details,
        )


class ADLSCheck(BaseCheck):
    """Preflight check for Azure Data Lake Storage connectivity.

    Verifies that ADLS endpoint is reachable.

    Attributes:
        storage_account: Azure storage account name
        container: Optional container name to verify

    Example:
        >>> check = ADLSCheck(storage_account="mystorageaccount")
        >>> result = check.run()
        >>> result.passed
        True
    """

    def __init__(
        self,
        storage_account: str,
        container: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize ADLS check.

        Args:
            storage_account: Azure storage account name
            container: Optional container name to verify
            timeout_seconds: Connection timeout
        """
        super().__init__(name="storage_adls", timeout_seconds=timeout_seconds)
        self.storage_account = storage_account
        self.container = container

    def _execute(self) -> CheckResult:
        """Check ADLS connectivity.

        Returns:
            CheckResult indicating ADLS status.
        """
        # Build ADLS Gen2 endpoint
        host = f"{self.storage_account}.dfs.core.windows.net"

        details: dict[str, Any] = {
            "storage_account": self.storage_account,
            "container": self.container,
            "host": host,
        }

        # DNS and TCP connectivity check
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            socket.gethostbyname(host)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((host, 443))
            sock.close()

            if result != 0:
                return self._make_result(
                    status=CheckStatus.FAILED,
                    message=f"Cannot connect to ADLS at {host}",
                    details=details,
                )

        except socket.gaierror as e:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"DNS resolution failed for {host}",
                details={**details, "error": str(e)},
            )
        except TimeoutError:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"Connection timed out to {host}",
                details=details,
            )

        return self._make_result(
            status=CheckStatus.PASSED,
            message=f"ADLS reachable at {host}",
            details=details,
        )
