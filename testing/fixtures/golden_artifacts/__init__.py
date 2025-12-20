"""Golden artifact utilities for contract testing.

This module provides utilities for loading versioned golden artifacts
that represent the blessed CompiledArtifacts contract.

Golden artifacts are static JSON files that serve as the immutable contract
reference. If the CompiledArtifacts model changes in a way that breaks
backward compatibility, tests loading these files will fail immediately.

Usage:
    from testing.fixtures.golden_artifacts import load_golden_artifact, GOLDEN_ARTIFACTS_DIR

    # Load a specific golden artifact
    artifact = load_golden_artifact("v1.0.0", "minimal.json")

    # Validate against CompiledArtifacts model
    from floe_core.compiler.models import CompiledArtifacts
    compiled = CompiledArtifacts.model_validate(artifact)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Root directory for golden artifacts
GOLDEN_ARTIFACTS_DIR = Path(__file__).parent

# Available versions
AVAILABLE_VERSIONS = ["v1.0.0"]

# Artifact types per version
ARTIFACT_TYPES = {
    "v1.0.0": ["minimal.json", "full.json", "docker_integration.json", "production.json"],
}


def load_golden_artifact(version: str, artifact_name: str) -> dict[str, Any]:
    """Load a golden artifact JSON file.

    Args:
        version: Contract version (e.g., "v1.0.0").
        artifact_name: Name of artifact file (e.g., "minimal.json").

    Returns:
        Parsed JSON as dictionary.

    Raises:
        ValueError: If version or artifact_name is invalid.
        FileNotFoundError: If artifact file doesn't exist.

    Example:
        >>> artifact = load_golden_artifact("v1.0.0", "minimal.json")
        >>> artifact["version"]
        '1.0.0'
    """
    if version not in AVAILABLE_VERSIONS:
        raise ValueError(
            f"Unknown version '{version}'. Available: {AVAILABLE_VERSIONS}"
        )

    if artifact_name not in ARTIFACT_TYPES.get(version, []):
        raise ValueError(
            f"Unknown artifact '{artifact_name}' for version {version}. "
            f"Available: {ARTIFACT_TYPES.get(version, [])}"
        )

    artifact_path = GOLDEN_ARTIFACTS_DIR / version / artifact_name
    if not artifact_path.exists():
        raise FileNotFoundError(f"Golden artifact not found: {artifact_path}")

    with artifact_path.open() as f:
        data = json.load(f)

    # Strip JSON Schema metadata fields (not part of CompiledArtifacts contract)
    data.pop("$schema", None)
    data.pop("$comment", None)

    return data


def load_all_golden_artifacts(version: str) -> dict[str, dict[str, Any]]:
    """Load all golden artifacts for a specific version.

    Args:
        version: Contract version (e.g., "v1.0.0").

    Returns:
        Dictionary mapping artifact name to parsed JSON.

    Example:
        >>> artifacts = load_all_golden_artifacts("v1.0.0")
        >>> list(artifacts.keys())
        ['minimal.json', 'full.json', 'docker_integration.json', 'production.json']
    """
    if version not in AVAILABLE_VERSIONS:
        raise ValueError(
            f"Unknown version '{version}'. Available: {AVAILABLE_VERSIONS}"
        )

    result = {}
    for artifact_name in ARTIFACT_TYPES.get(version, []):
        result[artifact_name] = load_golden_artifact(version, artifact_name)
    return result


def get_golden_artifact_path(version: str, artifact_name: str) -> Path:
    """Get the path to a golden artifact file.

    Args:
        version: Contract version.
        artifact_name: Name of artifact file.

    Returns:
        Path to the artifact file.
    """
    return GOLDEN_ARTIFACTS_DIR / version / artifact_name


def list_versions() -> list[str]:
    """List all available golden artifact versions.

    Returns:
        List of version strings.
    """
    return list(AVAILABLE_VERSIONS)


def list_artifacts(version: str) -> list[str]:
    """List all artifact files for a version.

    Args:
        version: Contract version.

    Returns:
        List of artifact file names.
    """
    return list(ARTIFACT_TYPES.get(version, []))
