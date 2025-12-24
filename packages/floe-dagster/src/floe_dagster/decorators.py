"""Instrumented asset decorators for batteries-included observability.

T094: [US6] Create @floe_asset decorator with auto-instrumentation

This module provides the @floe_asset decorator, a drop-in replacement for
Dagster's @asset that automatically adds observability instrumentation.
Data engineers get tracing and lineage for free without any boilerplate.

Key Features:
    - Automatic OTel span creation with asset attributes
    - Automatic OpenLineage START/COMPLETE/FAIL emission
    - Exception recording to span before re-raising
    - Graceful degradation when observability unavailable
    - Full pass-through of all Dagster @asset parameters

Example:
    >>> from floe_dagster import floe_asset
    >>> from floe_dagster.resources import PolarisCatalogResource
    >>>
    >>> @floe_asset(group="bronze", outputs=["demo.bronze_customers"])
    ... def bronze_customers(context, catalog: PolarisCatalogResource):
    ...     # Pure business logic - observability handled automatically
    ...     data = generate_customers(1000)
    ...     catalog.write_table("demo.bronze_customers", data)
    ...     return {"rows": len(data)}
"""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import TYPE_CHECKING, Any, TypeVar, cast

from dagster import AssetsDefinition, asset

if TYPE_CHECKING:
    from dagster import AssetExecutionContext

F = TypeVar("F", bound=Callable[..., Any])

# Resource key for the ObservabilityOrchestrator in Definitions
ORCHESTRATOR_RESOURCE_KEY = "_floe_observability_orchestrator"


def floe_asset(
    *,
    name: str | None = None,
    key_prefix: list[str] | str | None = None,
    group_name: str | None = None,
    outputs: list[str] | None = None,
    inputs: list[str] | None = None,
    compute_kind: str | None = None,
    description: str | None = None,
    metadata: dict[str, Any] | None = None,
    required_resource_keys: set[str] | None = None,
    **dagster_kwargs: Any,
) -> Callable[[F], AssetsDefinition]:
    """Instrumented asset decorator with automatic observability.

    A drop-in replacement for Dagster's @asset that automatically wraps
    the asset function with ObservabilityOrchestrator.asset_run() for
    tracing and lineage emission.

    The decorator:
    - Creates an OTel span with asset name and group
    - Emits OpenLineage START event on entry
    - Emits OpenLineage COMPLETE on success, FAIL on exception
    - Records exceptions to span before re-raising
    - Works with graceful degradation when observability unavailable

    Args:
        name: Asset name (defaults to function name)
        key_prefix: Asset key prefix for namespacing
        group_name: Asset group for organization
        outputs: Output dataset names for OpenLineage (e.g., ["demo.bronze_customers"])
        inputs: Input dataset names for OpenLineage (e.g., ["demo.raw_customers"])
        compute_kind: Compute kind tag (e.g., "python", "dbt", "sql")
        description: Asset description
        metadata: Static metadata for the asset
        required_resource_keys: Additional required resource keys
        **dagster_kwargs: Pass-through to Dagster's @asset decorator

    Returns:
        Decorated asset definition

    Example:
        >>> @floe_asset(
        ...     group_name="bronze",
        ...     outputs=["demo.bronze_customers"],
        ...     compute_kind="python",
        ... )
        ... def bronze_customers(context):
        ...     # Business logic only
        ...     return {"rows": 1000}

    Note:
        The orchestrator is injected via FloeDefinitions.from_compiled_artifacts().
        If no orchestrator is available, the asset runs normally without
        observability (graceful degradation).
    """

    def decorator(fn: F) -> AssetsDefinition:
        # Determine asset name from function or explicit
        asset_name = name or fn.__name__

        # Build span attributes from decorator arguments
        span_attributes: dict[str, Any] = {
            "asset.name": asset_name,
        }
        if group_name:
            span_attributes["asset.group"] = group_name
        if compute_kind:
            span_attributes["asset.compute_kind"] = compute_kind
        if outputs:
            span_attributes["asset.outputs"] = ",".join(outputs)
        if inputs:
            span_attributes["asset.inputs"] = ",".join(inputs)

        @functools.wraps(fn)
        def wrapper(context: AssetExecutionContext, *args: Any, **kwargs: Any) -> Any:
            # Try to get orchestrator from resources
            orchestrator = None
            try:
                if hasattr(context, "resources"):
                    orchestrator = getattr(
                        context.resources,
                        ORCHESTRATOR_RESOURCE_KEY,
                        None,
                    )
            except Exception:
                # Graceful degradation - resource not available
                pass

            # If no orchestrator, run without instrumentation
            if orchestrator is None:
                return fn(context, *args, **kwargs)

            # Run with observability instrumentation
            with orchestrator.asset_run(
                asset_name,
                outputs=outputs,
                inputs=inputs,
                attributes=span_attributes,
            ) as ctx:
                # Add run_id to context metadata if available
                if ctx.run_id and hasattr(context, "log"):
                    context.log.info(
                        f"Asset {asset_name} started",
                        extra={"run_id": ctx.run_id},
                    )

                result = fn(context, *args, **kwargs)

                # If result is a dict, add attributes
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, (str, int, float, bool)):
                            ctx.set_attribute(f"result.{key}", value)

                return result

        # Merge required resource keys with orchestrator
        merged_resource_keys = set(required_resource_keys or set())
        # Don't require the orchestrator - it's optional for graceful degradation

        # Build Dagster asset kwargs
        asset_kwargs: dict[str, Any] = {
            "name": name,
            "key_prefix": key_prefix,
            "group_name": group_name,
            "compute_kind": compute_kind,
            "description": description,
            "metadata": metadata,
            **dagster_kwargs,
        }

        # Only include non-None values
        asset_kwargs = {k: v for k, v in asset_kwargs.items() if v is not None}

        if merged_resource_keys:
            asset_kwargs["required_resource_keys"] = merged_resource_keys

        # Apply Dagster's @asset decorator
        return cast(AssetsDefinition, asset(**asset_kwargs)(wrapper))

    return decorator
