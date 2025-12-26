"""Job loader for converting JobDefinition to Dagster jobs.

T020: [010-orchestration-auto-discovery] Create job loader
Covers: 010-FR-011 through 010-FR-012

This module converts JobDefinition from floe.yaml into Dagster job definitions,
supporting both batch (asset selection) and ops (custom operations) jobs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dagster import JobDefinition as DagsterJobDefinition

    from floe_core.schemas.job_definition import JobDefinition


def load_jobs(jobs: dict[str, JobDefinition]) -> list[DagsterJobDefinition]:
    """Load jobs from JobDefinition dictionary.

    Converts JobDefinition configurations from floe.yaml into Dagster job definitions.
    Supports both batch jobs (asset selections) and ops jobs (custom operations).

    Args:
        jobs: Dictionary of job name to JobDefinition.

    Returns:
        List of Dagster JobDefinition objects.

    Example:
        >>> from floe_core.schemas.job_definition import BatchJob
        >>> jobs_config = {
        ...     "bronze_job": BatchJob(
        ...         type="batch",
        ...         selection=["group:bronze"],
        ...     )
        ... }
        >>> dagster_jobs = load_jobs(jobs_config)
    """
    if not jobs:
        return []

    dagster_jobs: list[DagsterJobDefinition] = []

    for job_name, job_def in jobs.items():
        if job_def.type == "batch":
            dagster_job = _create_batch_job(job_name, job_def)
        elif job_def.type == "ops":
            dagster_job = _create_ops_job(job_name, job_def)
        else:
            msg = f"Unknown job type: {job_def.type}"
            raise ValueError(msg)

        if dagster_job:
            dagster_jobs.append(dagster_job)

    return dagster_jobs


def _create_batch_job(
    job_name: str,
    job_def: JobDefinition,
) -> DagsterJobDefinition:
    """Create Dagster batch job from BatchJob definition.

    Args:
        job_name: Name of the job.
        job_def: BatchJob definition.

    Returns:
        Dagster JobDefinition for asset selection.
    """
    from dagster import define_asset_job

    selection_expr = ",".join(job_def.selection)

    job_kwargs = {
        "name": job_name,
        "selection": selection_expr,
    }

    if job_def.description:
        job_kwargs["description"] = job_def.description

    if job_def.tags:
        job_kwargs["tags"] = job_def.tags

    return define_asset_job(**job_kwargs)


def _create_ops_job(
    job_name: str,
    job_def: JobDefinition,
) -> DagsterJobDefinition:
    """Create Dagster ops job from OpsJob definition.

    Args:
        job_name: Name of the job.
        job_def: OpsJob definition.

    Returns:
        Dagster JobDefinition for ops execution.

    Raises:
        ImportError: If target_function cannot be imported.
    """
    import importlib

    from dagster import job as dagster_job_decorator

    module_path, function_name = job_def.target_function.rsplit(".", 1)

    try:
        module = importlib.import_module(module_path)
        op_function = getattr(module, function_name)
    except (ImportError, AttributeError) as e:
        msg = f"Cannot import {job_def.target_function}: {e}"
        raise ImportError(msg) from e

    @dagster_job_decorator(
        name=job_name,
        description=job_def.description,
        tags=job_def.tags or {},
    )
    def generated_ops_job():
        if job_def.args:
            op_function(**job_def.args)
        else:
            op_function()

    return generated_ops_job
