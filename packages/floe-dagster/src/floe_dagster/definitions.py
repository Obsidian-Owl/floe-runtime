"""Dagster definitions entry point.

T047: [US1] Create Dagster definitions entry point

This module provides the main entry point for loading Dagster definitions
from CompiledArtifacts configuration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dagster import Definitions

from floe_dagster.assets import FloeAssetFactory


def load_definitions_from_artifacts(
    artifacts_path: str | Path = ".floe/compiled_artifacts.json",
) -> Definitions:
    """Load Dagster Definitions from CompiledArtifacts file.

    Reads CompiledArtifacts JSON file and creates complete Dagster
    Definitions including dbt assets and resources.

    Args:
        artifacts_path: Path to compiled_artifacts.json file.

    Returns:
        Dagster Definitions object.

    Raises:
        FileNotFoundError: If artifacts file doesn't exist.
        ValueError: If artifacts are invalid.

    Example:
        >>> # In definitions.py at project root
        >>> from floe_dagster.definitions import load_definitions_from_artifacts
        >>> defs = load_definitions_from_artifacts()
    """
    path = Path(artifacts_path)
    if not path.exists():
        raise FileNotFoundError(
            f"CompiledArtifacts not found at {artifacts_path}. "
            f"Run 'floe compile' to generate it."
        )

    with open(path) as f:
        artifacts = json.load(f)

    return FloeAssetFactory.create_definitions(artifacts)


def load_definitions_from_dict(artifacts: dict[str, Any]) -> Definitions:
    """Load Dagster Definitions from CompiledArtifacts dictionary.

    Useful for testing or programmatic configuration.

    Args:
        artifacts: CompiledArtifacts dictionary.

    Returns:
        Dagster Definitions object.

    Example:
        >>> artifacts = {...}
        >>> defs = load_definitions_from_dict(artifacts)
    """
    return FloeAssetFactory.create_definitions(artifacts)


# Default definitions for Dagster to discover
# Uncomment and configure when deploying:
# defs = load_definitions_from_artifacts()
