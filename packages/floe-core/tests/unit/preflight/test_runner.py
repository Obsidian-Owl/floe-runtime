"""Unit tests for preflight runner.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-core/tests/unit/preflight/test_runner.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from floe_core.preflight.config import (
    CatalogCheckConfig,
    ComputeCheckConfig,
    PostgresCheckConfig,
    PreflightConfig,
    StorageCheckConfig,
)
from floe_core.preflight.models import CheckResult, CheckStatus
from floe_core.preflight.runner import PreflightRunner, run_preflight


class TestPreflightRunner:
    """Tests for PreflightRunner."""

    @pytest.mark.requirement("007-FR-005")
    def test_initialization(self) -> None:
        """Runner initializes with config."""
        config = PreflightConfig()
        runner = PreflightRunner(config)

        assert runner.config == config
        assert runner.fail_fast is False

    @pytest.mark.requirement("007-FR-005")
    def test_initialization_fail_fast(self) -> None:
        """Runner respects fail_fast setting."""
        config = PreflightConfig(fail_fast=True)
        runner = PreflightRunner(config)

        assert runner.fail_fast is True

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.TrinoCheck")
    @patch("floe_core.preflight.runner.PolarisCheck")
    @patch("floe_core.preflight.runner.PostgresCheck")
    def test_run_all_checks_pass(
        self,
        mock_postgres: MagicMock,
        mock_polaris: MagicMock,
        mock_trino: MagicMock,
    ) -> None:
        """All checks passing returns PASSED status."""
        # Configure mocks
        mock_trino_instance = MagicMock()
        mock_trino_instance.run.return_value = CheckResult(
            name="compute_trino", status=CheckStatus.PASSED
        )
        mock_trino.return_value = mock_trino_instance

        mock_polaris_instance = MagicMock()
        mock_polaris_instance.run.return_value = CheckResult(
            name="catalog_polaris", status=CheckStatus.PASSED
        )
        mock_polaris.return_value = mock_polaris_instance

        mock_postgres_instance = MagicMock()
        mock_postgres_instance.run.return_value = CheckResult(
            name="database_postgres", status=CheckStatus.PASSED
        )
        mock_postgres.return_value = mock_postgres_instance

        config = PreflightConfig(
            storage=StorageCheckConfig(enabled=False),  # Disable storage (needs bucket)
        )
        runner = PreflightRunner(config)
        result = runner.run()

        assert result.overall_status == CheckStatus.PASSED
        assert result.passed is True
        assert len(result.checks) == 3

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.TrinoCheck")
    @patch("floe_core.preflight.runner.PolarisCheck")
    @patch("floe_core.preflight.runner.PostgresCheck")
    def test_run_one_check_fails(
        self,
        mock_postgres: MagicMock,
        mock_polaris: MagicMock,
        mock_trino: MagicMock,
    ) -> None:
        """One failing check returns FAILED status."""
        mock_trino_instance = MagicMock()
        mock_trino_instance.run.return_value = CheckResult(
            name="compute_trino", status=CheckStatus.PASSED
        )
        mock_trino.return_value = mock_trino_instance

        mock_polaris_instance = MagicMock()
        mock_polaris_instance.run.return_value = CheckResult(
            name="catalog_polaris", status=CheckStatus.FAILED
        )
        mock_polaris.return_value = mock_polaris_instance

        mock_postgres_instance = MagicMock()
        mock_postgres_instance.run.return_value = CheckResult(
            name="database_postgres", status=CheckStatus.PASSED
        )
        mock_postgres.return_value = mock_postgres_instance

        config = PreflightConfig(
            storage=StorageCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        result = runner.run()

        assert result.overall_status == CheckStatus.FAILED
        assert result.failed is True
        assert result.failed_count == 1
        assert result.passed_count == 2

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.TrinoCheck")
    def test_fail_fast_stops_on_first_failure(self, mock_trino: MagicMock) -> None:
        """Fail fast stops after first failure."""
        mock_trino_instance = MagicMock()
        mock_trino_instance.run.return_value = CheckResult(
            name="compute_trino", status=CheckStatus.FAILED
        )
        mock_trino.return_value = mock_trino_instance

        config = PreflightConfig(
            fail_fast=True,
            storage=StorageCheckConfig(enabled=False),
            catalog=CatalogCheckConfig(enabled=True),
            postgres=PostgresCheckConfig(enabled=True),
        )
        runner = PreflightRunner(config)
        result = runner.run()

        # Should only have run one check
        assert len(result.checks) == 1
        assert result.overall_status == CheckStatus.FAILED

    @pytest.mark.requirement("007-FR-005")
    def test_no_checks_enabled(self) -> None:
        """No enabled checks returns SKIPPED."""
        config = PreflightConfig(
            compute=ComputeCheckConfig(enabled=False),
            storage=StorageCheckConfig(enabled=False),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        result = runner.run()

        assert result.overall_status == CheckStatus.SKIPPED
        assert len(result.checks) == 0

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.TrinoCheck")
    def test_error_status_takes_precedence(self, mock_trino: MagicMock) -> None:
        """ERROR status takes precedence over FAILED."""
        mock_trino_instance = MagicMock()
        mock_trino_instance.run.return_value = CheckResult(
            name="compute_trino", status=CheckStatus.ERROR
        )
        mock_trino.return_value = mock_trino_instance

        config = PreflightConfig(
            storage=StorageCheckConfig(enabled=False),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        result = runner.run()

        assert result.overall_status == CheckStatus.ERROR


class TestPreflightRunnerComputeTypes:
    """Tests for compute type selection."""

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.TrinoCheck")
    def test_trino_compute_type(self, mock_trino: MagicMock) -> None:
        """Trino compute type creates TrinoCheck."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = CheckResult(
            name="compute_trino", status=CheckStatus.PASSED
        )
        mock_trino.return_value = mock_instance

        config = PreflightConfig(
            compute=ComputeCheckConfig(type="trino"),
            storage=StorageCheckConfig(enabled=False),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        runner.run()

        mock_trino.assert_called_once()

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.SnowflakeCheck")
    def test_snowflake_compute_type(self, mock_snowflake: MagicMock) -> None:
        """Snowflake compute type creates SnowflakeCheck."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = CheckResult(
            name="compute_snowflake", status=CheckStatus.PASSED
        )
        mock_snowflake.return_value = mock_instance

        config = PreflightConfig(
            compute=ComputeCheckConfig(type="snowflake"),
            storage=StorageCheckConfig(enabled=False),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        runner.run()

        mock_snowflake.assert_called_once()

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.BigQueryCheck")
    def test_bigquery_compute_type(self, mock_bigquery: MagicMock) -> None:
        """BigQuery compute type creates BigQueryCheck."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = CheckResult(
            name="compute_bigquery", status=CheckStatus.PASSED
        )
        mock_bigquery.return_value = mock_instance

        config = PreflightConfig(
            compute=ComputeCheckConfig(type="bigquery"),
            storage=StorageCheckConfig(enabled=False),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        runner.run()

        mock_bigquery.assert_called_once()

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.DuckDBCheck")
    def test_duckdb_compute_type(self, mock_duckdb: MagicMock) -> None:
        """DuckDB compute type creates DuckDBCheck."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = CheckResult(
            name="compute_duckdb", status=CheckStatus.PASSED
        )
        mock_duckdb.return_value = mock_instance

        config = PreflightConfig(
            compute=ComputeCheckConfig(type="duckdb"),
            storage=StorageCheckConfig(enabled=False),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        runner.run()

        mock_duckdb.assert_called_once()


class TestPreflightRunnerStorageTypes:
    """Tests for storage type inference."""

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.S3Check")
    def test_s3_bucket_prefix(self, mock_s3: MagicMock) -> None:
        """s3:// prefix creates S3Check."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = CheckResult(name="storage_s3", status=CheckStatus.PASSED)
        mock_s3.return_value = mock_instance

        config = PreflightConfig(
            compute=ComputeCheckConfig(enabled=False),
            storage=StorageCheckConfig(bucket="s3://my-bucket"),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        runner.run()

        mock_s3.assert_called_once()

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.GCSCheck")
    def test_gs_bucket_prefix(self, mock_gcs: MagicMock) -> None:
        """gs:// prefix creates GCSCheck."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = CheckResult(name="storage_gcs", status=CheckStatus.PASSED)
        mock_gcs.return_value = mock_instance

        config = PreflightConfig(
            compute=ComputeCheckConfig(enabled=False),
            storage=StorageCheckConfig(bucket="gs://my-bucket"),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        runner.run()

        mock_gcs.assert_called_once()

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.ADLSCheck")
    def test_adls_bucket_prefix(self, mock_adls: MagicMock) -> None:
        """abfss:// prefix creates ADLSCheck."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = CheckResult(name="storage_adls", status=CheckStatus.PASSED)
        mock_adls.return_value = mock_instance

        config = PreflightConfig(
            compute=ComputeCheckConfig(enabled=False),
            storage=StorageCheckConfig(bucket="abfss://container@account.dfs.core.windows.net"),
            catalog=CatalogCheckConfig(enabled=False),
            postgres=PostgresCheckConfig(enabled=False),
        )
        runner = PreflightRunner(config)
        runner.run()

        mock_adls.assert_called_once()


class TestRunPreflight:
    """Tests for run_preflight convenience function."""

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.runner.TrinoCheck")
    @patch("floe_core.preflight.runner.PolarisCheck")
    @patch("floe_core.preflight.runner.PostgresCheck")
    def test_run_preflight_function(
        self,
        mock_postgres: MagicMock,
        mock_polaris: MagicMock,
        mock_trino: MagicMock,
    ) -> None:
        """run_preflight convenience function works."""
        for mock in [mock_trino, mock_polaris, mock_postgres]:
            mock_instance = MagicMock()
            mock_instance.run.return_value = CheckResult(name="test", status=CheckStatus.PASSED)
            mock.return_value = mock_instance

        config = PreflightConfig(
            storage=StorageCheckConfig(enabled=False),
        )
        result = run_preflight(config)

        assert result.overall_status == CheckStatus.PASSED
        assert result.passed is True
