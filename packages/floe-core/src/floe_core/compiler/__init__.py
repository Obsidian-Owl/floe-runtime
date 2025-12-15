"""Compiler module for floe-runtime.

T045: [US2] Export Compiler from compiler/__init__.py

This module exports the Compiler class and output models:
- Compiler: Main compiler class
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

__all__: list[str] = [
    # Compiler class
    "Compiler",
    # Output models
    "CompiledArtifacts",
    "ArtifactMetadata",
    "EnvironmentContext",
    # Extraction function
    "extract_column_classifications",
]
