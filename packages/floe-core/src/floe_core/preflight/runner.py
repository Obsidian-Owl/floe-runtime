"""Preflight check runner.

Orchestrates execution of all preflight checks.

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from floe_core.preflight.checks import (
    ADLSCheck,
    BaseCheck,
    BigQueryCheck,
    DuckDBCheck,
    GCSCheck,
    PolarisCheck,
    PostgresCheck,
    S3Check,
    SnowflakeCheck,
    TrinoCheck,
)
from floe_core.preflight.models import CheckResult, CheckStatus, PreflightResult

if TYPE_CHECKING:
    from floe_core.preflight.config import PreflightConfig

logger = structlog.get_logger(__name__)


class PreflightRunner:
    """Orchestrates preflight check execution.

    Runs configured preflight checks and aggregates results.

    Attributes:
        config: Preflight configuration
        fail_fast: Stop on first failure

    Example:
        >>> from floe_core.preflight.config import PreflightConfig
        >>> config = PreflightConfig()
        >>> runner = PreflightRunner(config)
        >>> result = runner.run()
        >>> print(result.overall_status)
    """

    def __init__(self, config: PreflightConfig) -> None:
        """Initialize the runner.

        Args:
            config: Preflight configuration defining which checks to run
        """
        self.config = config
        self.fail_fast = config.fail_fast
        self._log = logger.bind(component="preflight_runner")

    def run(self) -> PreflightResult:
        """Run all configured preflight checks.

        Returns:
            PreflightResult with all check outcomes
        """
        start_time = time.monotonic()
        started_at = datetime.now(UTC)
        results: list[CheckResult] = []

        self._log.info("preflight_started", fail_fast=self.fail_fast)

        checks = self._build_checks()
        self._log.info("checks_configured", count=len(checks))

        for check in checks:
            result = check.run()
            results.append(result)

            if self.fail_fast and result.failed:
                self._log.warning(
                    "fail_fast_triggered",
                    check=check.name,
                    status=result.status.value,
                )
                break

        finished_at = datetime.now(UTC)
        total_duration_ms = int((time.monotonic() - start_time) * 1000)

        # Determine overall status
        overall_status = self._determine_overall_status(results)

        self._log.info(
            "preflight_completed",
            overall_status=overall_status.value,
            total_duration_ms=total_duration_ms,
            passed=sum(1 for r in results if r.passed),
            failed=sum(1 for r in results if r.failed),
        )

        return PreflightResult(
            checks=results,
            overall_status=overall_status,
            started_at=started_at,
            finished_at=finished_at,
            total_duration_ms=total_duration_ms,
        )

    def _build_checks(self) -> list[BaseCheck]:
        """Build the list of checks to run based on configuration.

        Returns:
            List of check instances to execute
        """
        checks: list[BaseCheck] = []

        # Compute check
        if self.config.compute.enabled:
            compute_check = self._create_compute_check()
            if compute_check:
                checks.append(compute_check)

        # Storage check
        if self.config.storage.enabled:
            storage_check = self._create_storage_check()
            if storage_check:
                checks.append(storage_check)

        # Catalog check
        if self.config.catalog.enabled:
            checks.append(
                PolarisCheck(
                    uri=self.config.catalog.uri or "http://localhost:8181",
                    timeout_seconds=self.config.catalog.timeout_seconds,
                )
            )

        # PostgreSQL check
        if self.config.postgres.enabled:
            checks.append(
                PostgresCheck(
                    host=self.config.postgres.host,
                    port=self.config.postgres.port,
                    database=self.config.postgres.database,
                    timeout_seconds=self.config.postgres.timeout_seconds,
                )
            )

        return checks

    def _create_compute_check(self) -> BaseCheck | None:
        """Create compute check based on type configuration.

        Returns:
            Compute check instance or None if type unknown
        """
        compute_type = self.config.compute.type.lower()
        timeout = self.config.compute.timeout_seconds

        compute_checks: dict[str, type[BaseCheck]] = {
            "trino": TrinoCheck,
            "snowflake": SnowflakeCheck,
            "bigquery": BigQueryCheck,
            "duckdb": DuckDBCheck,
        }

        check_class = compute_checks.get(compute_type)
        if check_class:
            return check_class(timeout_seconds=timeout)  # type: ignore[call-arg]

        self._log.warning("unknown_compute_type", type=compute_type)
        return None

    def _create_storage_check(self) -> BaseCheck | None:
        """Create storage check based on bucket configuration.

        Returns:
            Storage check instance or None if bucket not configured
        """
        bucket = self.config.storage.bucket
        timeout = self.config.storage.timeout_seconds

        if not bucket:
            self._log.debug("storage_check_skipped", reason="no bucket configured")
            return None

        # Infer storage type from bucket URI prefix
        if bucket.startswith("s3://"):
            return S3Check(bucket=bucket.replace("s3://", ""), timeout_seconds=timeout)
        elif bucket.startswith("gs://"):
            # GCS bucket - extract bucket name, use placeholder project_id
            # In production, project_id would come from environment or ADC
            bucket_name = bucket.replace("gs://", "")
            return GCSCheck(
                project_id="default",
                bucket=bucket_name,
                timeout_seconds=timeout,
            )
        elif bucket.startswith("abfs://") or bucket.startswith("abfss://"):
            # Azure Data Lake Storage
            # Format: abfss://<container>@<account>.dfs.core.windows.net
            parts = bucket.replace("abfss://", "").replace("abfs://", "").split("@")
            if len(parts) == 2:
                container = parts[0]
                account = parts[1].split(".")[0]
                return ADLSCheck(
                    storage_account=account,
                    container=container,
                    timeout_seconds=timeout,
                )
            return None
        else:
            # Default to S3 for unqualified bucket names
            return S3Check(bucket=bucket, timeout_seconds=timeout)

    def _determine_overall_status(self, results: list[CheckResult]) -> CheckStatus:
        """Determine overall preflight status from check results.

        Args:
            results: List of individual check results

        Returns:
            Overall status based on all results
        """
        if not results:
            return CheckStatus.SKIPPED

        if any(r.status == CheckStatus.ERROR for r in results):
            return CheckStatus.ERROR

        if any(r.status == CheckStatus.FAILED for r in results):
            return CheckStatus.FAILED

        if any(r.status == CheckStatus.WARNING for r in results):
            return CheckStatus.WARNING

        if all(r.status == CheckStatus.SKIPPED for r in results):
            return CheckStatus.SKIPPED

        return CheckStatus.PASSED


def run_preflight(config: PreflightConfig) -> PreflightResult:
    """Run preflight checks with the given configuration.

    Convenience function that creates a runner and executes checks.

    Args:
        config: Preflight configuration

    Returns:
        PreflightResult with all check outcomes

    Example:
        >>> from floe_core.preflight.config import PreflightConfig
        >>> config = PreflightConfig()
        >>> result = run_preflight(config)
        >>> if result.passed:
        ...     print("All checks passed!")
    """
    runner = PreflightRunner(config)
    return runner.run()
