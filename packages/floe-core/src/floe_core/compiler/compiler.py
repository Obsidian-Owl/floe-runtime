"""Compiler class for floe-runtime.

T044: [US2] Implement Compiler class with compile() method
T037: [US2] Update Compiler to merge FloeSpec with resolved PlatformSpec

This module implements the main Compiler class that transforms
FloeSpec (floe.yaml) + PlatformSpec (platform.yaml) into CompiledArtifacts.

Two-Tier Architecture:
- FloeSpec contains logical profile references (catalog: "default")
- PlatformSpec contains concrete infrastructure configuration
- Compiler resolves references and produces CompiledArtifacts
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from floe_core.compiler.extractor import extract_column_classifications
from floe_core.compiler.models import (
    ArtifactMetadata,
    CompiledArtifacts,
    ResolvedPlatformProfiles,
)
from floe_core.compiler.platform_resolver import PlatformResolver
from floe_core.compiler.profile_resolver import ProfileResolver
from floe_core.schemas import FloeSpec

if TYPE_CHECKING:
    from floe_core.schemas.platform_spec import PlatformSpec

logger = logging.getLogger(__name__)

# Package version - will be updated from pyproject.toml in production
FLOE_CORE_VERSION = "0.1.0"


class Compiler:
    """Compile floe.yaml + platform.yaml to CompiledArtifacts.

    The Compiler transforms a FloeSpec (parsed from floe.yaml) and PlatformSpec
    (parsed from platform.yaml) into CompiledArtifacts, the immutable contract
    consumed by downstream packages (floe-dagster, floe-dbt, floe-cube, floe-polaris).

    Two-Tier Architecture:
    - FloeSpec: Data engineer's view (transforms, governance, observability)
    - PlatformSpec: Platform engineer's view (storage, catalog, compute profiles)
    - Same floe.yaml works across dev/staging/prod environments

    Compilation includes:
    - Parsing and validating floe.yaml
    - Loading and resolving platform.yaml
    - Resolving profile references (catalog: "default" → CatalogProfile)
    - Computing source hash for caching
    - Detecting dbt projects
    - Extracting column classifications from dbt manifest
    - Building immutable CompiledArtifacts

    Example:
        >>> compiler = Compiler()
        >>> # With auto-detected platform.yaml
        >>> artifacts = compiler.compile(Path("project/floe.yaml"))
        >>>
        >>> # With explicit platform.yaml
        >>> platform = PlatformResolver(env="prod").load()
        >>> artifacts = compiler.compile(Path("project/floe.yaml"), platform=platform)
    """

    def __init__(self, platform_env: str | None = None) -> None:
        """Initialize the Compiler.

        Args:
            platform_env: Platform environment to use (e.g., "local", "dev", "prod").
                If not specified, uses FLOE_PLATFORM_ENV environment variable.
        """
        self.platform_env = platform_env

    def compile(
        self,
        spec_path: Path | str,
        platform: PlatformSpec | None = None,
    ) -> CompiledArtifacts:
        """Compile floe.yaml to CompiledArtifacts.

        Args:
            spec_path: Path to floe.yaml file.
            platform: Optional pre-loaded PlatformSpec. If not provided,
                will attempt to load from platform.yaml in standard locations.

        Returns:
            Immutable CompiledArtifacts ready for downstream consumption.

        Raises:
            FileNotFoundError: If floe.yaml not found.
            yaml.YAMLError: If YAML is invalid.
            pydantic.ValidationError: If spec validation fails.
            ProfileNotFoundError: If profile references cannot be resolved.

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

        # Load platform configuration if not provided
        if platform is None:
            platform = self._load_platform(spec_path.parent)

        # Resolve profile references
        resolved_profiles = self._resolve_profiles(spec, platform)

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
            transforms=list(spec.transforms),
            consumption=spec.consumption,
            governance=spec.governance,
            observability=spec.observability,
            resolved_profiles=resolved_profiles,
            dbt_project_path=dbt_project_path,
            dbt_manifest_path=dbt_manifest_path,
            column_classifications=column_classifications,
        )

    def _load_platform(self, project_dir: Path) -> PlatformSpec:
        """Load platform configuration.

        Searches for platform.yaml in standard locations:
        1. platform/<env>/platform.yaml (env from FLOE_PLATFORM_ENV or self.platform_env)
        2. <project_dir>/<env>/platform.yaml
        3. .floe/<env>/platform.yaml
        4. Fallback: platform.yaml without env subdirectory

        Args:
            project_dir: Project directory (parent of floe.yaml).

        Returns:
            Loaded PlatformSpec.

        Raises:
            PlatformNotFoundError: If platform.yaml not found.
        """
        # Include project_dir/platform as first search path for standard layout
        resolver = PlatformResolver(
            env=self.platform_env,
            search_paths=(
                project_dir / "platform",  # Standard: project/platform/{env}/platform.yaml
                project_dir,  # Fallback: project/{env}/platform.yaml
                project_dir / ".floe",  # Fallback: project/.floe/{env}/platform.yaml
            ),
        )
        return resolver.load()

    def _resolve_profiles(
        self,
        spec: FloeSpec,
        platform: PlatformSpec,
    ) -> ResolvedPlatformProfiles:
        """Resolve profile references from FloeSpec against PlatformSpec.

        Args:
            spec: FloeSpec with logical profile references.
            platform: PlatformSpec with concrete profile configurations.

        Returns:
            ResolvedPlatformProfiles with concrete configurations.

        Raises:
            ProfileNotFoundError: If profile reference not found.
        """
        resolver = ProfileResolver(platform)
        profiles = resolver.resolve_all(
            storage=spec.storage,
            catalog=spec.catalog,
            compute=spec.compute,
        )

        return ResolvedPlatformProfiles(
            storage=profiles.storage,
            catalog=profiles.catalog,
            compute=profiles.compute,
            platform_env=self.platform_env or "local",
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
