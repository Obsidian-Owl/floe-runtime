"""Mapper for creating requirement-to-test mappings.

This module provides functionality to map functional requirements (FR-XXX)
to their covering tests, producing TraceabilityMapping objects.

Functions:
    map_requirements_to_tests: Create mappings from requirements and tests

Usage:
    from testing.traceability.mapper import map_requirements_to_tests
    from testing.traceability.parser import parse_requirements
    from testing.traceability.scanner import scan_tests

    requirements = parse_requirements(Path("spec.md"))
    tests = scan_tests([Path("packages/*/tests/integration/")])
    mappings = map_requirements_to_tests(requirements, tests)

See Also:
    testing.traceability.models for Requirement, Test, TraceabilityMapping
    testing.traceability.parser for requirement extraction
    testing.traceability.scanner for test discovery
"""

from __future__ import annotations

from testing.traceability.models import (
    CoverageStatus,
    Requirement,
    Test,
    TraceabilityMapping,
)


def map_requirements_to_tests(
    requirements: list[Requirement],
    tests: list[Test],
) -> list[TraceabilityMapping]:
    """Map requirements to their covering tests.

    Creates TraceabilityMapping objects that link each requirement to
    the tests that cover it, based on matching requirement IDs.

    Args:
        requirements: List of requirements extracted from spec files.
        tests: List of tests with requirement markers.

    Returns:
        List of TraceabilityMapping objects, one per requirement.
        Each mapping includes:
        - requirement_id: The FR-XXX identifier
        - test_ids: List of test identifiers (file::class::function)
        - coverage_status: COVERED if tests exist, UNCOVERED otherwise

    Example:
        >>> from testing.traceability.mapper import map_requirements_to_tests
        >>> mappings = map_requirements_to_tests(requirements, tests)
        >>> for m in mappings:
        ...     print(f"{m.requirement_id}: {m.coverage_status.value}")
        FR-001: covered
        FR-002: uncovered
    """
    if not requirements:
        return []

    # Build lookup: requirement_id -> list of test_ids
    req_to_tests: dict[str, list[str]] = {req.id: [] for req in requirements}

    for test in tests:
        test_id = _generate_test_id(test)
        for req_id in test.requirement_ids:
            if req_id in req_to_tests:
                req_to_tests[req_id].append(test_id)

    # Create mappings
    mappings: list[TraceabilityMapping] = []
    for req in requirements:
        test_ids = req_to_tests[req.id]
        coverage_status = CoverageStatus.COVERED if test_ids else CoverageStatus.UNCOVERED
        mapping = TraceabilityMapping(
            requirement_id=req.id,
            test_ids=test_ids,
            coverage_status=coverage_status,
        )
        mappings.append(mapping)

    return mappings


def _generate_test_id(test: Test) -> str:
    """Generate a test identifier in pytest format.

    Format: file_path::class_name::function_name (with class)
    or: file_path::function_name (without class)

    Args:
        test: Test object to generate ID for.

    Returns:
        Test identifier string.
    """
    if test.class_name:
        return f"{test.file_path}::{test.class_name}::{test.function_name}"
    return f"{test.file_path}::{test.function_name}"


__all__ = [
    "map_requirements_to_tests",
]
