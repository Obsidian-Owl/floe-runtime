"""Database preflight checks.

Connectivity checks for supported databases:
- PostgreSQL (for Dagster metadata)

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


class PostgresCheck(BaseCheck):
    """Preflight check for PostgreSQL connectivity.

    Verifies that PostgreSQL is reachable (used for Dagster metadata).

    Attributes:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name

    Example:
        >>> check = PostgresCheck(host="localhost", port=5432, database="dagster")
        >>> result = check.run()
        >>> result.passed
        True
    """

    DEFAULT_PORT = 5432

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        connection_string: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize PostgreSQL check.

        Args:
            host: PostgreSQL hostname
            port: PostgreSQL port
            database: Database name
            connection_string: Optional connection string (overrides host/port/database)
            timeout_seconds: Connection timeout
        """
        super().__init__(name="database_postgres", timeout_seconds=timeout_seconds)

        # Parse connection string if provided
        if connection_string:
            parsed = urlparse(connection_string)
            self.host = parsed.hostname or "localhost"
            self.port = parsed.port or self.DEFAULT_PORT
            self.database = (parsed.path or "/postgres").lstrip("/") or "postgres"
        else:
            self.host = host
            self.port = port
            self.database = database

    def _execute(self) -> CheckResult:
        """Check PostgreSQL connectivity.

        Returns:
            CheckResult indicating PostgreSQL status.
        """
        details: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "database": self.database,
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
                    message=f"Cannot connect to PostgreSQL at {self.host}:{self.port}",
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

        return self._make_result(
            status=CheckStatus.PASSED,
            message=f"PostgreSQL reachable at {self.host}:{self.port}",
            details=details,
        )
