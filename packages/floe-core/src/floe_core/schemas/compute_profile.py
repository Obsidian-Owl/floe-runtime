"""Compute profile models for floe-runtime.

T006: [Setup] Create schema module compute_profile.py
T033-T037: [Phase 2] Will implement ComputeProfile and related models

This module defines compute backend configuration including:
- ComputeProfile: dbt adapter configuration
- ComputeType: Enum for supported compute types (duckdb, snowflake, bigquery, etc.)
- Connection properties (warehouse, account, etc.)
- Credential references for compute access
"""

from __future__ import annotations

# Supported compute types (dbt adapters)
COMPUTE_TYPES = frozenset(
    {
        "duckdb",
        "snowflake",
        "bigquery",
        "databricks",
        "redshift",
        "postgres",
    }
)

# Default compute type for local development
DEFAULT_COMPUTE_TYPE = "duckdb"

# TODO(T033): Implement ComputeType enum
# TODO(T034): Implement ComputeProfile model
# TODO(T035): Implement compute properties validation
# TODO(T036): Implement adapter-specific property schemas
# TODO(T037): Implement credential reference validation
