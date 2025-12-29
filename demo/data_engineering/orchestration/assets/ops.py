"""Operations assets - Maintenance tasks.

These demonstrate ops-style assets for maintenance operations:
- Iceberg table optimization (vacuum, compact)
- Simple @op decorator for utility operations
- Auto-discovered via orchestration.asset_modules
- Observability instrumentation with OpenTelemetry traces and OpenLineage events
"""

from typing import Any

from dagster import OpExecutionContext, op

from floe_dagster.observability import ObservabilityOrchestrator


@op(
    description="Vacuum old Iceberg table snapshots",
    required_resource_keys={"observability_orchestrator"},
)
def vacuum_old_snapshots(context: OpExecutionContext, retention_days: int = 30) -> dict[str, Any]:
    """Remove old table snapshots older than retention period.

    Args:
        context: Dagster execution context
        retention_days: Number of days to retain snapshots (default: 30)

    Returns:
        Dictionary with operation results
    """
    orchestrator: ObservabilityOrchestrator = context.resources.observability_orchestrator

    with orchestrator.asset_run(
        context=context,
        asset_key="vacuum_old_snapshots",
        compute_kind="iceberg",
        group_name="maintenance",
    ):
        context.log.info("Vacuuming snapshots older than %d days", retention_days)

        # In a real implementation, this would call catalog.expire_snapshots()
        # For demo purposes, we just log
        return {
            "operation": "vacuum",
            "retention_days": retention_days,
            "tables_processed": 4,
        }


@op(
    description="Compact Iceberg data files",
    required_resource_keys={"observability_orchestrator"},
)
def compact_data_files(
    context: OpExecutionContext,
    catalog: str = "demo",
    min_commits: int = 10,
) -> dict[str, Any]:
    """Compact small data files to improve query performance.

    Args:
        context: Dagster execution context
        catalog: Catalog namespace (default: "demo")
        min_commits: Minimum commits before compaction (default: 10)

    Returns:
        Dictionary with operation results
    """
    orchestrator: ObservabilityOrchestrator = context.resources.observability_orchestrator

    with orchestrator.asset_run(
        context=context,
        asset_key="compact_data_files",
        compute_kind="iceberg",
        group_name="maintenance",
    ):
        context.log.info(
            "Compacting data files for catalog=%s, min_commits=%d",
            catalog,
            min_commits,
        )

        # In a real implementation, this would call catalog.rewrite_data_files()
        # For demo purposes, we just log
        return {
            "operation": "compact",
            "catalog": catalog,
            "min_commits": min_commits,
            "files_compacted": 12,
        }
