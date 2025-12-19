"""Contract validation module for testing infrastructure.

This module provides utilities for working with JSON Schema contracts
used in the floe-runtime testing system.

Key Components:
    - CONTRACTS_DIR: Path to the contracts directory
    - TRACEABILITY_MATRIX_SCHEMA_PATH: Path to traceability matrix schema
    - TEST_REPORT_SCHEMA_PATH: Path to test report schema
    - load_traceability_matrix_schema(): Load the traceability matrix JSON schema
    - load_test_report_schema(): Load the test report JSON schema

Usage:
    from testing.contracts import (
        load_traceability_matrix_schema,
        load_test_report_schema,
    )

    # Load schema for validation
    schema = load_traceability_matrix_schema()

    # Use with jsonschema for validation
    from jsonschema import validate
    validate(instance=my_data, schema=schema)

See Also:
    - specs/006-integration-testing/contracts/ for JSON schema definitions
    - testing/traceability/models.py for Pydantic model equivalents
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__version__ = "0.1.0"

# Path to the contracts directory in specs
CONTRACTS_DIR: Path = (
    Path(__file__).parent.parent.parent / "specs" / "006-integration-testing" / "contracts"
)

# Schema file paths
TRACEABILITY_MATRIX_SCHEMA_PATH: Path = CONTRACTS_DIR / "traceability-matrix.schema.json"
TEST_REPORT_SCHEMA_PATH: Path = CONTRACTS_DIR / "test-report.schema.json"


def load_traceability_matrix_schema() -> dict[str, Any]:
    """Load the traceability matrix JSON schema.

    Returns:
        The traceability matrix JSON schema as a dictionary.

    Raises:
        FileNotFoundError: If the schema file doesn't exist.
        json.JSONDecodeError: If the schema file contains invalid JSON.

    Example:
        >>> schema = load_traceability_matrix_schema()
        >>> schema["title"]
        'TraceabilityMatrix'
    """
    return _load_schema(TRACEABILITY_MATRIX_SCHEMA_PATH)


def load_test_report_schema() -> dict[str, Any]:
    """Load the test report JSON schema.

    Returns:
        The test report JSON schema as a dictionary.

    Raises:
        FileNotFoundError: If the schema file doesn't exist.
        json.JSONDecodeError: If the schema file contains invalid JSON.

    Example:
        >>> schema = load_test_report_schema()
        >>> schema["title"]
        'TraceabilityReport'
    """
    return _load_schema(TEST_REPORT_SCHEMA_PATH)


def _load_schema(path: Path) -> dict[str, Any]:
    """Load a JSON schema from a file path.

    Args:
        path: Path to the JSON schema file.

    Returns:
        The JSON schema as a dictionary.

    Raises:
        FileNotFoundError: If the schema file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    with path.open("r", encoding="utf-8") as f:
        schema: dict[str, Any] = json.load(f)
    return schema


__all__: list[str] = [
    "__version__",
    # Path constants
    "CONTRACTS_DIR",
    "TRACEABILITY_MATRIX_SCHEMA_PATH",
    "TEST_REPORT_SCHEMA_PATH",
    # Schema loaders
    "load_traceability_matrix_schema",
    "load_test_report_schema",
]
