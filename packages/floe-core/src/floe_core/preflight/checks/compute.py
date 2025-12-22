"""Compute engine preflight checks.

Connectivity checks for supported compute engines:
- Trino
- Snowflake
- BigQuery
- DuckDB

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

import socket
from typing import Any

import structlog

from floe_core.preflight.checks.base import BaseCheck
from floe_core.preflight.models import CheckResult, CheckStatus

logger = structlog.get_logger(__name__)


class TrinoCheck(BaseCheck):
    """Preflight check for Trino connectivity.

    Verifies that Trino is reachable and responding.

    Attributes:
        host: Trino coordinator host
        port: Trino coordinator port
        catalog: Optional catalog to verify

    Example:
        >>> check = TrinoCheck(host="trino.example.com", port=8080)
        >>> result = check.run()
        >>> result.passed
        True
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        catalog: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize Trino check.

        Args:
            host: Trino coordinator hostname
            port: Trino coordinator port
            catalog: Optional catalog to verify access
            timeout_seconds: Connection timeout
        """
        super().__init__(name="compute_trino", timeout_seconds=timeout_seconds)
        self.host = host
        self.port = port
        self.catalog = catalog

    def _execute(self) -> CheckResult:
        """Check Trino connectivity.

        Returns:
            CheckResult indicating Trino status.
        """
        details: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "catalog": self.catalog,
        }

        # TCP connectivity check
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result != 0:
                return self._make_result(
                    status=CheckStatus.FAILED,
                    message=f"Cannot connect to Trino at {self.host}:{self.port}",
                    details=details,
                )

        except socket.gaierror as e:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"DNS resolution failed for {self.host}",
                details={**details, "error": str(e)},
            )
        except TimeoutError:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"Connection timed out to {self.host}:{self.port}",
                details=details,
            )

        # HTTP health check (optional - depends on trino package availability)
        try:
            import urllib.request

            # URL is from validated configuration, not user input
            url = f"http://{self.host}:{self.port}/v1/info"
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
            message=f"Trino reachable at {self.host}:{self.port}",
            details=details,
        )


class SnowflakeCheck(BaseCheck):
    """Preflight check for Snowflake connectivity.

    Verifies that Snowflake account is reachable.

    Attributes:
        account: Snowflake account identifier
        region: Optional region (inferred from account if not provided)

    Example:
        >>> check = SnowflakeCheck(account="my_account")
        >>> result = check.run()
        >>> result.passed
        True
    """

    def __init__(
        self,
        account: str,
        region: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize Snowflake check.

        Args:
            account: Snowflake account identifier
            region: Optional region for account
            timeout_seconds: Connection timeout
        """
        super().__init__(name="compute_snowflake", timeout_seconds=timeout_seconds)
        self.account = account
        self.region = region

    def _execute(self) -> CheckResult:
        """Check Snowflake connectivity.

        Returns:
            CheckResult indicating Snowflake status.
        """
        # Build Snowflake URL
        if self.region:
            host = f"{self.account}.{self.region}.snowflakecomputing.com"
        else:
            host = f"{self.account}.snowflakecomputing.com"

        details: dict[str, Any] = {
            "account": self.account,
            "region": self.region,
            "host": host,
        }

        # DNS and TCP connectivity check
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            socket.gethostbyname(host)

            # Try HTTPS port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((host, 443))
            sock.close()

            if result != 0:
                return self._make_result(
                    status=CheckStatus.FAILED,
                    message=f"Cannot connect to Snowflake at {host}:443",
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
            message=f"Snowflake reachable at {host}",
            details=details,
        )


class BigQueryCheck(BaseCheck):
    """Preflight check for BigQuery connectivity.

    Verifies that BigQuery API is reachable.

    Attributes:
        project_id: GCP project ID
        location: Optional BigQuery location

    Example:
        >>> check = BigQueryCheck(project_id="my-project")
        >>> result = check.run()
        >>> result.passed
        True
    """

    BIGQUERY_API_HOST = "bigquery.googleapis.com"

    def __init__(
        self,
        project_id: str,
        location: str = "US",
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize BigQuery check.

        Args:
            project_id: GCP project ID
            location: BigQuery location/region
            timeout_seconds: Connection timeout
        """
        super().__init__(name="compute_bigquery", timeout_seconds=timeout_seconds)
        self.project_id = project_id
        self.location = location

    def _execute(self) -> CheckResult:
        """Check BigQuery connectivity.

        Returns:
            CheckResult indicating BigQuery status.
        """
        details: dict[str, Any] = {
            "project_id": self.project_id,
            "location": self.location,
            "api_host": self.BIGQUERY_API_HOST,
        }

        # DNS and TCP connectivity check to BigQuery API
        try:
            socket.setdefaulttimeout(self.timeout_seconds)
            socket.gethostbyname(self.BIGQUERY_API_HOST)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((self.BIGQUERY_API_HOST, 443))
            sock.close()

            if result != 0:
                return self._make_result(
                    status=CheckStatus.FAILED,
                    message=f"Cannot connect to BigQuery API at {self.BIGQUERY_API_HOST}",
                    details=details,
                )

        except socket.gaierror as e:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"DNS resolution failed for {self.BIGQUERY_API_HOST}",
                details={**details, "error": str(e)},
            )
        except TimeoutError:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"Connection timed out to {self.BIGQUERY_API_HOST}",
                details=details,
            )

        return self._make_result(
            status=CheckStatus.PASSED,
            message=f"BigQuery API reachable for project {self.project_id}",
            details=details,
        )


class DuckDBCheck(BaseCheck):
    """Preflight check for DuckDB availability.

    Verifies that DuckDB is installed and functional.
    DuckDB is an embedded database, so this check verifies
    the Python package is available.

    Example:
        >>> check = DuckDBCheck()
        >>> result = check.run()
        >>> result.passed
        True
    """

    def __init__(
        self,
        database_path: str | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        """Initialize DuckDB check.

        Args:
            database_path: Optional path to DuckDB file (None for in-memory)
            timeout_seconds: Check timeout (usually fast)
        """
        super().__init__(name="compute_duckdb", timeout_seconds=timeout_seconds)
        self.database_path = database_path

    def _execute(self) -> CheckResult:
        """Check DuckDB availability.

        Returns:
            CheckResult indicating DuckDB status.
        """
        details: dict[str, Any] = {
            "database_path": self.database_path or ":memory:",
        }

        # Check if DuckDB package is available
        try:
            import duckdb

            details["version"] = duckdb.__version__

            # Test connection
            conn = duckdb.connect(self.database_path or ":memory:")
            result = conn.execute("SELECT 1 AS test").fetchone()
            conn.close()

            if result and result[0] == 1:
                return self._make_result(
                    status=CheckStatus.PASSED,
                    message=f"DuckDB {duckdb.__version__} available and functional",
                    details=details,
                )
            else:
                return self._make_result(
                    status=CheckStatus.FAILED,
                    message="DuckDB query returned unexpected result",
                    details=details,
                )

        except ImportError:
            return self._make_result(
                status=CheckStatus.FAILED,
                message="DuckDB package not installed",
                details={**details, "error": "ImportError: No module named 'duckdb'"},
            )
        except Exception as e:
            return self._make_result(
                status=CheckStatus.FAILED,
                message=f"DuckDB connection failed: {e}",
                details={**details, "error": str(e)},
            )
