"""Compiler module for floe-runtime.

This module exports the Compiler class, resolution utilities, and output models:
- Compiler: Main compiler class
- PlatformResolver: Load platform.yaml from file or environment
- ProfileResolver: Resolve logical profile references to concrete configs
- SecretResolver: Validate and resolve secret references
- CompiledArtifacts: Output contract model
- ArtifactMetadata: Compilation metadata model
- EnvironmentContext: Optional SaaS context model
- extract_column_classifications: Classification extraction function
"""

from __future__ import annotations

from floe_core.compiler.compiler import Compiler
from floe_core.compiler.extractor import extract_column_classifications
from floe_core.compiler.models import (
    ArtifactMetadata,
    CompiledArtifacts,
    EnvironmentContext,
)
from floe_core.compiler.platform_resolver import (
    DEFAULT_PLATFORM_ENV,
    PLATFORM_ENV_VAR,
    PLATFORM_FILE_NAME,
    PLATFORM_SEARCH_PATHS,
    PlatformNotFoundError,
    PlatformResolver,
    get_platform_env,
)
from floe_core.compiler.profile_resolver import (
    DEFAULT_PROFILE_NAME,
    PROFILE_TYPES,
    ProfileResolutionError,
    ProfileResolver,
    ResolvedProfiles,
)
from floe_core.compiler.secret_resolver import (
    SecretResolver,
    SecretValidationResult,
    validate_platform_secrets,
)

__all__: list[str] = [
    # Compiler class
    "Compiler",
    # Platform resolution
    "PlatformResolver",
    "PlatformNotFoundError",
    "get_platform_env",
    "PLATFORM_ENV_VAR",
    "DEFAULT_PLATFORM_ENV",
    "PLATFORM_FILE_NAME",
    "PLATFORM_SEARCH_PATHS",
    # Profile resolution
    "ProfileResolver",
    "ProfileResolutionError",
    "ResolvedProfiles",
    "DEFAULT_PROFILE_NAME",
    "PROFILE_TYPES",
    # Secret resolution
    "SecretResolver",
    "SecretValidationResult",
    "validate_platform_secrets",
    # Output models
    "CompiledArtifacts",
    "ArtifactMetadata",
    "EnvironmentContext",
    # Extraction function
    "extract_column_classifications",
]
