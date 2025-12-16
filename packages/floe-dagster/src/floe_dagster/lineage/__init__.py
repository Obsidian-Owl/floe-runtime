"""OpenLineage integration for data lineage tracking.

T011: Create lineage subpackage __init__.py

This package provides OpenLineage event emission for data lineage
tracking during pipeline execution.

Key Components:
    - OpenLineageEmitter: Emits START, COMPLETE, FAIL events
    - LineageDatasetBuilder: Builds Dataset objects from dbt nodes
    - ClassificationFacetBuilder: Builds facets from governance config

Features:
    - Automatic lineage capture from dbt model execution
    - Column-level classification metadata in facets
    - Input/output dataset tracking
    - Graceful degradation when endpoint unavailable

Example:
    >>> from floe_dagster.lineage import OpenLineageEmitter
    >>> emitter = OpenLineageEmitter(endpoint="http://lineage:5000")
    >>> emitter.emit_start(run_id="abc123", job_name="my_model")
    >>> # ... execute dbt model ...
    >>> emitter.emit_complete(
    ...     run_id="abc123",
    ...     job_name="my_model",
    ...     inputs=[input_dataset],
    ...     outputs=[output_dataset]
    ... )
"""

from __future__ import annotations

from floe_dagster.lineage.builder import LineageDatasetBuilder
from floe_dagster.lineage.client import OpenLineageEmitter
from floe_dagster.lineage.config import OpenLineageConfig
from floe_dagster.lineage.events import LineageDataset, LineageEvent, LineageEventType
from floe_dagster.lineage.facets import (
    ColumnClassification,
    build_classification_facet,
)

__all__: list[str] = [
    # Config
    "OpenLineageConfig",
    # Events
    "LineageEventType",
    "LineageDataset",
    "LineageEvent",
    # Facets
    "ColumnClassification",
    "build_classification_facet",
    # Builder
    "LineageDatasetBuilder",
    # Client
    "OpenLineageEmitter",
]
