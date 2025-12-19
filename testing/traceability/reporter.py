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
from testing.traceability.models import CoverageStatus, TraceabilityMatrix
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


def format_console_report(matrix: TraceabilityMatrix) -> str:
    """Format traceability matrix for terminal output.

    Creates a human-readable console report showing coverage status,
    requirements, and any coverage gaps.

    Args:
        matrix: TraceabilityMatrix to format.

    Returns:
        Formatted string suitable for terminal display.

    Example:
        >>> matrix = generate_matrix(...)
        >>> print(format_console_report(matrix))
        Traceability Report: 006 - Integration Testing
        ================================================
        Coverage: 75.0% (3/4 requirements covered)
        ...
    """
    lines: list[str] = []

    # Header
    lines.append(f"Traceability Report: {matrix.feature_id} - {matrix.feature_name}")
    lines.append("=" * 60)
    lines.append("")

    # Summary statistics
    total_reqs = len(matrix.requirements)
    coverage_pct = matrix.get_coverage_percentage()
    covered_count = sum(1 for m in matrix.mappings if m.coverage_status == CoverageStatus.COVERED)

    lines.append(f"Coverage: {coverage_pct:.1f}%")
    lines.append(f"Requirements: {total_reqs} total, {covered_count} covered")
    lines.append(f"Tests: {len(matrix.tests)}")
    lines.append("")

    # Covered requirements
    covered_mappings = [m for m in matrix.mappings if m.coverage_status == CoverageStatus.COVERED]
    if covered_mappings:
        lines.append("Covered Requirements:")
        lines.append("-" * 40)
        for mapping in covered_mappings:
            req = next((r for r in matrix.requirements if r.id == mapping.requirement_id), None)
            if req:
                lines.append(f"  [COVERED] {req.id}: {req.text[:50]}...")
                for test_id in mapping.test_ids:
                    lines.append(f"            -> {test_id}")
        lines.append("")

    # Coverage gaps
    gaps = matrix.get_gaps()
    if gaps:
        lines.append("Coverage Gaps:")
        lines.append("-" * 40)
        for req in gaps:
            lines.append(f"  [UNCOVERED] {req.id}: {req.text[:50]}...")
        lines.append("")

    return "\n".join(lines)


def format_json_report(matrix: TraceabilityMatrix) -> str:
    """Format traceability matrix as CI-compatible JSON.

    Creates a JSON report suitable for CI/CD integration, containing
    coverage metrics, requirements, mappings, and gaps.

    Args:
        matrix: TraceabilityMatrix to format.

    Returns:
        JSON string with structured traceability data.

    Example:
        >>> matrix = generate_matrix(...)
        >>> json_str = format_json_report(matrix)
        >>> data = json.loads(json_str)
        >>> print(data["coverage_percentage"])
        75.0
    """
    import json

    report_data = {
        "feature_id": matrix.feature_id,
        "feature_name": matrix.feature_name,
        "generated_at": matrix.generated_at.isoformat() if matrix.generated_at else None,
        "coverage_percentage": matrix.get_coverage_percentage(),
        "spec_files": matrix.spec_files,
        "requirements": [
            {
                "id": req.id,
                "text": req.text,
                "category": req.category.value,
                "spec_file": req.spec_file,
                "line_number": req.line_number,
            }
            for req in matrix.requirements
        ],
        "tests": [
            {
                "file_path": test.file_path,
                "function_name": test.function_name,
                "class_name": test.class_name,
                "requirement_ids": test.requirement_ids,
                "package": test.package,
            }
            for test in matrix.tests
        ],
        "mappings": [
            {
                "requirement_id": mapping.requirement_id,
                "test_ids": mapping.test_ids,
                "coverage_status": mapping.coverage_status.value,
            }
            for mapping in matrix.mappings
        ],
        "gaps": [
            {
                "id": req.id,
                "text": req.text,
                "category": req.category.value,
            }
            for req in matrix.get_gaps()
        ],
    }

    return json.dumps(report_data, indent=2)


__all__ = [
    "generate_matrix",
    "format_console_report",
    "format_json_report",
]
