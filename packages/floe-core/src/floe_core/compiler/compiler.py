"""Compiler class for floe-runtime.

T044: [US2] Implement Compiler class with compile() method

This module implements the main Compiler class that transforms
FloeSpec (floe.yaml) into CompiledArtifacts.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from floe_core.compiler.extractor import extract_column_classifications
from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
from floe_core.schemas import FloeSpec

logger = logging.getLogger(__name__)

# Package version - will be updated from pyproject.toml in production
FLOE_CORE_VERSION = "0.1.0"


class Compiler:
    """Compile floe.yaml to CompiledArtifacts.

    The Compiler transforms a FloeSpec (parsed from floe.yaml) into
    CompiledArtifacts, the immutable contract consumed by downstream
    packages (floe-dagster, floe-dbt, floe-cube, floe-polaris).

    Compilation includes:
    - Parsing and validating floe.yaml
    - Computing source hash for caching
    - Detecting dbt projects
    - Extracting column classifications from dbt manifest
    - Building immutable CompiledArtifacts

    Example:
        >>> compiler = Compiler()
        >>> artifacts = compiler.compile(Path("project/floe.yaml"))
        >>> artifacts.compute.target
        <ComputeTarget.duckdb: 'duckdb'>
    """

    def compile(self, spec_path: Path | str) -> CompiledArtifacts:
        """Compile floe.yaml to CompiledArtifacts.

        Args:
            spec_path: Path to floe.yaml file.

        Returns:
            Immutable CompiledArtifacts ready for downstream consumption.

        Raises:
            FileNotFoundError: If floe.yaml not found.
            yaml.YAMLError: If YAML is invalid.
            pydantic.ValidationError: If spec validation fails.

        Example:
            >>> compiler = Compiler()
            >>> artifacts = compiler.compile("project/floe.yaml")
        """
        spec_path = Path(spec_path)

        if not spec_path.exists():
            raise FileNotFoundError(f"File not found: {spec_path}")

        # Read and hash source content
        source_content = spec_path.read_text()
        source_hash = self._compute_hash(source_content)

        # Parse YAML
        raw_data: dict[str, Any] = yaml.safe_load(source_content)

        # Validate with FloeSpec
        spec = FloeSpec.model_validate(raw_data)

        # Create metadata
        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version=FLOE_CORE_VERSION,
            source_hash=source_hash,
        )

        # Detect dbt project
        project_dir = spec_path.parent
        dbt_project_path = self._find_dbt_project(project_dir, spec)
        dbt_manifest_path: str | None = None
        column_classifications = None

        if dbt_project_path:
            dbt_project_path_obj = Path(dbt_project_path)
            manifest_path = dbt_project_path_obj / "target" / "manifest.json"

            if manifest_path.exists():
                dbt_manifest_path = str(manifest_path)

            # Extract classifications if governance source is dbt_meta
            if spec.governance.classification_source == "dbt_meta":
                try:
                    classifications = extract_column_classifications(
                        dbt_project_path_obj,
                        strict=False,
                    )
                    if classifications:
                        column_classifications = classifications
                except Exception as e:
                    logger.warning(
                        f"Failed to extract classifications: {e}",
                        extra={"dbt_project": dbt_project_path},
                    )

        # Build CompiledArtifacts
        return CompiledArtifacts(
            metadata=metadata,
            compute=spec.compute,
            transforms=list(spec.transforms),
            consumption=spec.consumption,
            governance=spec.governance,
            observability=spec.observability,
            catalog=spec.catalog,
            dbt_project_path=dbt_project_path,
            dbt_manifest_path=dbt_manifest_path,
            column_classifications=column_classifications,
        )

    def _compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content.

        Args:
            content: String content to hash.

        Returns:
            Hex-encoded SHA-256 hash.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _find_dbt_project(
        self,
        start_path: Path,
        spec: FloeSpec,
    ) -> str | None:
        """Find dbt project directory.

        Searches for dbt project based on transforms configuration
        or by searching parent directories.

        Args:
            start_path: Starting directory (usually floe.yaml parent).
            spec: Parsed FloeSpec to check transforms.

        Returns:
            Path to dbt project directory, or None if not found.
        """
        # Check transforms for dbt paths
        for transform in spec.transforms:
            if transform.type == "dbt":
                dbt_path = start_path / transform.path
                if (dbt_path / "dbt_project.yml").exists():
                    return str(dbt_path)

        # Search parent directories (up to 5 levels)
        current = start_path
        for _ in range(5):
            if (current / "dbt_project.yml").exists():
                return str(current)

            if current.parent == current:
                break  # Reached filesystem root

            current = current.parent

        return None
