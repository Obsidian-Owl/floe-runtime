"""floe-dbt: dbt integration for floe-runtime.

This package provides dbt profile generation and execution
wrapping. dbt owns all SQL - we only invoke it.
"""

from __future__ import annotations

__version__ = "0.1.0"

from floe_dbt.factory import ProfileFactory
from floe_dbt.profiles import (
    ProfileGenerator,
    ProfileGeneratorConfig,
)
from floe_dbt.writer import ProfileWriter

__all__ = [
    "__version__",
    "ProfileFactory",
    "ProfileGenerator",
    "ProfileGeneratorConfig",
    "ProfileWriter",
]
