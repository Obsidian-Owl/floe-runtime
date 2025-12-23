"""Platform specification models for floe-runtime.

T002: [Setup] Create schema module platform_spec.py
T014-T022: [Phase 2] Will implement full PlatformSpec and nested models

This module defines the platform.yaml schema including:
- PlatformSpec: Root platform specification model
- Environment-specific configuration
- Profile references (storage, catalog, compute)
- Observability configuration
"""

from __future__ import annotations

# Supported environment types
ENVIRONMENT_TYPES = frozenset({"local", "dev", "staging", "prod"})

# Platform spec version for schema compatibility
PLATFORM_SPEC_VERSION = "1.0.0"

# TODO(T014): Implement PlatformSpec root model
# TODO(T015): Implement StorageProfiles container
# TODO(T016): Implement CatalogProfiles container
# TODO(T017): Implement ComputeProfiles container
# TODO(T018): Implement ObservabilityConfig model
# TODO(T019): Implement TracingConfig model
# TODO(T020): Implement LineageConfig model
# TODO(T021): Implement TLSConfig model
# TODO(T022): Implement environment validation
