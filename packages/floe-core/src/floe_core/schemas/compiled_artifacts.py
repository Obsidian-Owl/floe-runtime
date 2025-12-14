"""CompiledArtifacts: Output contract for runtime consumers.

This module defines the CompiledArtifacts Pydantic model - the sole
integration contract between floe-core (compiler) and floe-dagster (runtime).

Changes to this schema require version bumping (semantic versioning).
Backward compatibility: 3-version deprecation policy.

TODO: Implement per docs/04-building-blocks.md section 2.3
"""

from __future__ import annotations
