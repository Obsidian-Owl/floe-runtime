"""floe-core: Core schemas and compilation for floe-runtime.

This package provides:
- FloeSpec: Pydantic schema for floe.yaml configuration
- CompiledArtifacts: Output contract consumed by other packages
- Compiler: Transform FloeSpec → CompiledArtifacts
- JSON Schema export utilities
"""

from __future__ import annotations

__version__ = "0.1.0"

# Public API exports will be added as schemas are implemented
# from floe_core.schemas import FloeSpec, CompiledArtifacts
# from floe_core.compiler import Compiler
# from floe_core.errors import ValidationError, CompilationError

__all__ = [
    "__version__",
    # "FloeSpec",
    # "CompiledArtifacts",
    # "Compiler",
    # "ValidationError",
    # "CompilationError",
]
