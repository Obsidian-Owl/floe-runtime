"""Preflight validation module.

Pre-deployment validation for floe-runtime deployments.
Validates connectivity and configuration before deployment.

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

from floe_core.preflight.config import PreflightConfig
from floe_core.preflight.models import (
    CheckResult,
    CheckStatus,
    PreflightReport,
    PreflightResult,
)
from floe_core.preflight.output import (
    format_result_json,
    format_result_table,
    print_result,
)
from floe_core.preflight.runner import PreflightRunner, run_preflight

__all__ = [
    "CheckResult",
    "CheckStatus",
    "PreflightConfig",
    "PreflightReport",
    "PreflightResult",
    "PreflightRunner",
    "format_result_json",
    "format_result_table",
    "print_result",
    "run_preflight",
]
