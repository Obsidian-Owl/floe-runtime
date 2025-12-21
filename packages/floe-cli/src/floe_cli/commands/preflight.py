"""floe preflight command - Pre-deployment validation checks.

T046: Register preflight command in floe-cli

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

import click

from floe_cli.output import error, info, success


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
    try:
        # Import here to avoid heavy imports at CLI startup
        from floe_core.preflight import PreflightConfig, print_result, run_preflight
        from floe_core.preflight.config import (
            CatalogCheckConfig,
            ComputeCheckConfig,
            PostgresCheckConfig,
            StorageCheckConfig,
        )

        if verbose:
            info("Building preflight configuration...")

        # Build configuration from CLI options
        config = PreflightConfig(
            compute=ComputeCheckConfig(
                enabled=compute,
                timeout_seconds=timeout,
                type=compute_type,
            ),
            storage=StorageCheckConfig(
                enabled=storage,
                timeout_seconds=timeout,
                bucket=bucket,
            ),
            catalog=CatalogCheckConfig(
                enabled=catalog,
                timeout_seconds=timeout,
                uri=catalog_uri,
            ),
            postgres=PostgresCheckConfig(
                enabled=postgres,
                timeout_seconds=timeout,
                host=postgres_host,
                port=postgres_port,
                database=postgres_database,
            ),
            fail_fast=fail_fast,
            verbose=verbose,
        )

        if verbose:
            enabled_checks = []
            if compute:
                enabled_checks.append(f"compute ({compute_type})")
            if storage:
                enabled_checks.append("storage")
            if catalog:
                enabled_checks.append("catalog")
            if postgres:
                enabled_checks.append("postgres")
            info(f"Running checks: {', '.join(enabled_checks)}")

        # Run preflight checks
        result = run_preflight(config)

        # Display results
        print_result(result, output_format=output_format)

        # Exit with appropriate code
        if result.passed:
            if output_format == "table":
                success("Preflight checks passed")
            raise SystemExit(0)
        else:
            if output_format == "table":
                error("Preflight checks failed")
            raise SystemExit(1)

    except SystemExit:
        raise
    except Exception as e:
        error(f"Preflight check error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise SystemExit(1) from None
