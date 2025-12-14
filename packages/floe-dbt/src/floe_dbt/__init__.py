"""floe-dbt: dbt integration for floe-runtime.

This package provides dbt profile generation and execution
wrapping. dbt owns all SQL - we only invoke it.
"""

from __future__ import annotations

__version__ = "0.1.0"

# Public API exports will be added as modules are implemented
# from floe_dbt.profiles import generate_profiles, write_profiles
# from floe_dbt.executor import DbtExecutor

__all__ = ["__version__"]
