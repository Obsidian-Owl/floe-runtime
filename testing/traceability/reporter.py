"""Reporter for generating traceability matrices and reports.

This module provides high-level functions for generating complete
traceability matrices and CI-compatible reports.

Functions:
    generate_matrix: Create a complete TraceabilityMatrix from specs and tests

Usage:
    from testing.traceability.reporter import generate_matrix

    matrix = generate_matrix(
        feature_id="006",
        feature_name="Integration Testing",
        spec_files=[Path("specs/006-integration-testing/spec.md")],
        test_dirs=[Path("packages/*/tests/integration/")],
    )

    print(f"Coverage: {matrix.get_coverage_percentage():.1f}%")
    for gap in matrix.get_gaps():
        print(f"  - {gap.id}: {gap.text[:50]}...")

See Also:
    testing.traceability.models for TraceabilityMatrix definition
    testing.traceability.parser for requirement extraction
    testing.traceability.scanner for test discovery
    testing.traceability.mapper for requirement-to-test mapping
"""

from __future__ import annotations

from pathlib import Path

from testing.traceability.mapper import map_requirements_to_tests
from testing.traceability.models import TraceabilityMatrix
from testing.traceability.parser import parse_requirements
from testing.traceability.scanner import scan_tests


def generate_matrix(
    feature_id: str,
    feature_name: str,
    spec_files: list[Path],
    test_dirs: list[Path],
) -> TraceabilityMatrix:
    """Generate a complete traceability matrix.

    Orchestrates requirement parsing, test scanning, and mapping to
    create a TraceabilityMatrix with full coverage analysis.

    Args:
        feature_id: Feature identifier (e.g., "006").
        feature_name: Human-readable feature name.
        spec_files: List of specification file paths to parse.
        test_dirs: List of test directory paths to scan.

    Returns:
        TraceabilityMatrix with requirements, tests, and mappings.

    Example:
        >>> matrix = generate_matrix(
        ...     feature_id="006",
        ...     feature_name="Integration Testing",
        ...     spec_files=[Path("specs/006/spec.md")],
        ...     test_dirs=[Path("packages/*/tests/integration/")],
        ... )
        >>> print(f"Coverage: {matrix.get_coverage_percentage():.1f}%")
        Coverage: 75.0%
    """
    # Parse requirements from all spec files
    all_requirements = []
    spec_file_paths = []
    for spec_file in spec_files:
        if spec_file.exists():
            requirements = parse_requirements(spec_file)
            all_requirements.extend(requirements)
            spec_file_paths.append(str(spec_file))

    # Scan for tests in all test directories
    all_tests = scan_tests(test_dirs)

    # Create mappings between requirements and tests
    mappings = map_requirements_to_tests(all_requirements, all_tests)

    # Build and return the matrix
    return TraceabilityMatrix(
        feature_id=feature_id,
        feature_name=feature_name,
        spec_files=spec_file_paths,
        requirements=all_requirements,
        tests=all_tests,
        mappings=mappings,
    )


__all__ = [
    "generate_matrix",
]
