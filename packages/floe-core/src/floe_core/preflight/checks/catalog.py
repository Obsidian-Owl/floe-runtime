"""Catalog preflight checks.

Connectivity checks for supported catalog services:
- Polaris (Iceberg REST Catalog)

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


class PolarisCheck(BaseCheck):
    """Preflight check for Polaris catalog connectivity.

    Verifies that the Polaris REST catalog is reachable.

    Attributes:
        uri: Polaris catalog URI
        catalog_name: Name of the catalog

    Example:
        >>> check = PolarisCheck(uri="http://localhost:8181", catalog_name="default")
        >>> result = check.run()
        >>> result.passed
        True
    """

    def __init__(
        self,
        uri: str = "http://localhost:8181",
        catalog_name: str = "default",
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize Polaris check.

        Args:
            uri: Polaris catalog base URI
            catalog_name: Name of the catalog to check
            timeout_seconds: Connection timeout
        """
        super().__init__(name="catalog_polaris", timeout_seconds=timeout_seconds)
        self.uri = uri
        self.catalog_name = catalog_name

    def _execute(self) -> CheckResult:
        """Check Polaris connectivity.

        Returns:
            CheckResult indicating Polaris status.
        """
        # Parse URI to extract host and port
        parsed = urlparse(self.uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 8181)

        details: dict[str, Any] = {
            "uri": self.uri,
            "catalog_name": self.catalog_name,
            "host": host,
            "port": port,
        }

        # TCP connectivity check
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                return self._make_result(
                    status=CheckStatus.FAILED,
                    message=f"Cannot connect to Polaris at {host}:{port}",
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
                message=f"Connection timed out to {host}:{port}",
                details=details,
            )

        # HTTP health check (optional)
        try:
            import urllib.request

            # Try the Polaris REST catalog config endpoint
            # URL is from validated configuration, not user input
            url = f"{self.uri}/api/catalog/v1/config"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:  # nosec B310
                if response.status == 200:
                    details["api_status"] = "healthy"
                else:
                    details["api_status"] = f"unhealthy (status {response.status})"
        except Exception:
            # HTTP check is optional, TCP is sufficient
            details["api_status"] = "not_checked"

        return self._make_result(
            status=CheckStatus.PASSED,
            message=f"Polaris catalog reachable at {self.uri}",
            details=details,
        )
