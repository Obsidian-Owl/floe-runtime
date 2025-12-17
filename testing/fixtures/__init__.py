"""Shared test fixtures for floe-runtime packages.

This module provides factory functions and fixtures for creating test data
that can be shared across all packages.

Exports:
    make_compiled_artifacts: Factory for creating CompiledArtifacts dicts
    COMPUTE_CONFIGS: Pre-defined compute configurations for all 7 targets
    base_metadata: Factory for creating artifact metadata
"""

from __future__ import annotations

from testing.fixtures.artifacts import (
    COMPUTE_CONFIGS,
    base_metadata,
    make_compiled_artifacts,
)

__all__ = [
    "COMPUTE_CONFIGS",
    "base_metadata",
    "make_compiled_artifacts",
]
