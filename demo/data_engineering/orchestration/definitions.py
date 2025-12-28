"""Dagster Definitions for Floe Demo - Zero Boilerplate.

This demonstrates the power of floe-runtime's auto-discovery architecture:

BEFORE (old approach - 288 lines):
    - Explicit asset imports and declarations
    - Manual job, schedule, sensor definitions
    - Wrapper assets for dbt models (silver_staging, gold_marts)
    - Explicit passing of all definitions

AFTER (new approach - THIS FILE):
    - Everything auto-loaded from floe.yaml orchestration config
    - dbt models auto-discovered as individual assets with per-model observability
    - Python assets auto-discovered from modules
    - Jobs, schedules, sensors declaratively configured
    - Single factory call - NO BOILERPLATE

Data Flow (all auto-discovered):
    1. Bronze Layer: Python assets (demo.bronze_*)
    2. Silver Layer: dbt staging models (auto-loaded from manifest)
    3. Gold Layer: dbt mart models (auto-loaded from manifest)
    4. Jobs: Defined in floe.yaml orchestration.jobs
    5. Schedules: Defined in floe.yaml orchestration.schedules
    6. Sensors: Defined in floe.yaml orchestration.sensors

Two-Tier Architecture:
    Data engineers configure pipelines in floe.yaml (THIS CONFIG).
    Platform engineers configure infrastructure in platform.yaml.
    FloeDefinitions.from_compiled_artifacts() auto-loads both.

Platform Configuration Auto-Loading:
    - FloeDefinitions reads FLOE_PLATFORM_FILE environment variable
    - Resolves platform.yaml from FLOE_PLATFORM_ENV (local, dev, staging, prod)
    - Creates catalog, observability, and dbt resources automatically
    - No infrastructure configuration needed in THIS file

The Result:
    288 lines of boilerplate → 1 line of factory call = 99.7% reduction

Note: This file intentionally does NOT use `from __future__ import annotations`
because Dagster 1.12.x's type validation uses identity checks that break with
PEP 563 string annotations.
"""

from floe_dagster import FloeDefinitions

# =============================================================================
# Definitions - Everything Auto-Loaded from floe.yaml
# =============================================================================
#
# This single line replaces 288 lines of manual definitions.
#
# Auto-loaded from floe.yaml orchestration config:
#   ✅ Bronze assets from: demo.data_engineering.orchestration.assets.bronze
#   ✅ Ops assets from: demo.data_engineering.orchestration.assets.ops
#   ✅ dbt models as individual assets with per-model observability
#   ✅ Jobs: demo_bronze, demo_pipeline, maintenance
#   ✅ Schedules: bronze_refresh_schedule, transform_pipeline_schedule
#   ✅ Sensors: file_arrival_sensor
#
# Auto-loaded from platform.yaml (via FLOE_PLATFORM_FILE):
#   ✅ CatalogResource (Polaris/Iceberg)
#   ✅ ObservabilityOrchestrator (Jaeger tracing + Marquez lineage)
#   ✅ DbtCliResource (dbt execution)
#
# To run the demo:
#   export FLOE_PLATFORM_ENV=local  # or dev, staging, prod
#   dagster dev
#

defs = FloeDefinitions.from_compiled_artifacts(namespace="data_engineering")
