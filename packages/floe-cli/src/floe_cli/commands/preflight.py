"""floe preflight command - Pre-deployment validation checks.

T046: Register preflight command in floe-cli

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

from dataclasses import dataclass

import click

from floe_cli.output import error, info, success
from floe_core.preflight import PreflightConfig


@dataclass
class PreflightOptions:
    """Grouped preflight CLI options to reduce parameter count (S107)."""

    compute: bool
    storage: bool
    catalog: bool
    postgres: bool
    compute_type: str
    bucket: str
    catalog_uri: str
    postgres_host: str
    postgres_port: int
    postgres_database: str
    timeout: int
    fail_fast: bool
    output_format: str
    verbose: bool


def _build_config(opts: PreflightOptions) -> PreflightConfig:
    """Build PreflightConfig from CLI options.

    Args:
        opts: Grouped CLI options

    Returns:
        PreflightConfig for running checks
    """
    from floe_core.preflight import PreflightConfig
    from floe_core.preflight.config import (
        CatalogCheckConfig,
        ComputeCheckConfig,
        PostgresCheckConfig,
        StorageCheckConfig,
    )

    return PreflightConfig(
        compute=ComputeCheckConfig(
            enabled=opts.compute,
            timeout_seconds=opts.timeout,
            type=opts.compute_type,
        ),
        storage=StorageCheckConfig(
            enabled=opts.storage,
            timeout_seconds=opts.timeout,
            bucket=opts.bucket,
        ),
        catalog=CatalogCheckConfig(
            enabled=opts.catalog,
            timeout_seconds=opts.timeout,
            uri=opts.catalog_uri,
        ),
        postgres=PostgresCheckConfig(
            enabled=opts.postgres,
            timeout_seconds=opts.timeout,
            host=opts.postgres_host,
            port=opts.postgres_port,
            database=opts.postgres_database,
        ),
        fail_fast=opts.fail_fast,
        verbose=opts.verbose,
    )


def _log_enabled_checks(opts: PreflightOptions) -> None:
    """Log which checks are enabled in verbose mode.

    Args:
        opts: Grouped CLI options
    """
    enabled_checks = []
    if opts.compute:
        enabled_checks.append(f"compute ({opts.compute_type})")
    if opts.storage:
        enabled_checks.append("storage")
    if opts.catalog:
        enabled_checks.append("catalog")
    if opts.postgres:
        enabled_checks.append("postgres")
    info(f"Running checks: {', '.join(enabled_checks)}")


def _run_preflight_checks(opts: PreflightOptions) -> None:
    """Execute preflight checks and display results.

    Args:
        opts: Grouped CLI options

    Raises:
        SystemExit: With code 0 on success, 1 on failure
    """
    from floe_core.preflight import print_result, run_preflight

    if opts.verbose:
        info("Building preflight configuration...")

    config = _build_config(opts)

    if opts.verbose:
        _log_enabled_checks(opts)

    result = run_preflight(config)
    print_result(result, output_format=opts.output_format)

    # Exit with appropriate code
    if result.passed:
        if opts.output_format == "table":
            success("Preflight checks passed")
        raise SystemExit(0)
    if opts.output_format == "table":
        error("Preflight checks failed")
    raise SystemExit(1)


@click.command()
@click.option(
    "--compute/--no-compute",
    default=True,
    help="Enable/disable compute connectivity check",
)
@click.option(
    "--storage/--no-storage",
    default=True,
    help="Enable/disable storage connectivity check",
)
@click.option(
    "--catalog/--no-catalog",
    default=True,
    help="Enable/disable catalog connectivity check",
)
@click.option(
    "--postgres/--no-postgres",
    default=True,
    help="Enable/disable PostgreSQL connectivity check",
)
@click.option(
    "--compute-type",
    type=click.Choice(["trino", "snowflake", "bigquery", "duckdb"]),
    default="trino",
    help="Compute engine type [default: trino]",
)
@click.option(
    "--bucket",
    default="",
    help="Storage bucket to check (e.g., s3://my-bucket)",
)
@click.option(
    "--catalog-uri",
    default="http://localhost:8181",
    help="Polaris catalog URI [default: http://localhost:8181]",
)
@click.option(
    "--postgres-host",
    default="localhost",
    help="PostgreSQL host [default: localhost]",
)
@click.option(
    "--postgres-port",
    default=5432,
    type=int,
    help="PostgreSQL port [default: 5432]",
)
@click.option(
    "--postgres-database",
    default="dagster",
    help="PostgreSQL database [default: dagster]",
)
@click.option(
    "--timeout",
    default=30,
    type=int,
    help="Check timeout in seconds [default: 30]",
)
@click.option(
    "--fail-fast",
    is_flag=True,
    default=False,
    help="Stop on first failure",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format [default: table]",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Verbose output",
)
def preflight(
    compute: bool,
    storage: bool,
    catalog: bool,
    postgres: bool,
    compute_type: str,
    bucket: str,
    catalog_uri: str,
    postgres_host: str,
    postgres_port: int,
    postgres_database: str,
    timeout: int,
    fail_fast: bool,
    output_format: str,
    verbose: bool,
) -> None:
    """Run pre-deployment validation checks.

    Validates connectivity to compute engines, storage, catalog, and database
    before deploying floe pipelines. Use this command to verify infrastructure
    is accessible and properly configured.

    Examples:

        floe preflight

        floe preflight --compute-type snowflake --no-catalog

        floe preflight --bucket s3://my-bucket --format json

        floe preflight --postgres-host db.example.com --fail-fast
    """
    opts = PreflightOptions(
        compute=compute,
        storage=storage,
        catalog=catalog,
        postgres=postgres,
        compute_type=compute_type,
        bucket=bucket,
        catalog_uri=catalog_uri,
        postgres_host=postgres_host,
        postgres_port=postgres_port,
        postgres_database=postgres_database,
        timeout=timeout,
        fail_fast=fail_fast,
        output_format=output_format,
        verbose=verbose,
    )

    try:
        _run_preflight_checks(opts)
    except SystemExit:
        raise
    except Exception as e:
        error(f"Preflight check error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise SystemExit(1) from None
