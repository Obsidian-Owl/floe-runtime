"""Floe Demo Dagster Definitions.

This module provides Dagster orchestration for the demo e-commerce pipeline.
It includes:
- Scheduled jobs for synthetic data generation
- Sensor-based triggers for on-demand runs
- Asset definitions for dbt model execution

Covers: 007-FR-029 (E2E validation tests)
Covers: 007-FR-031 (Medallion architecture orchestration)
"""

from __future__ import annotations

from demo.orchestration.definitions import defs

__all__ = ["defs"]
