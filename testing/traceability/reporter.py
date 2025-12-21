"""Reporter for generating traceability matrices and reports.

This module provides high-level functions for generating complete
traceability matrices and CI-compatible reports.

Functions:
    generate_matrix: Create a complete TraceabilityMatrix from specs and tests
    generate_multi_feature_report: Create coverage report across all features
    format_multi_feature_console: Format multi-feature report for console

Usage:
    from testing.traceability.reporter import generate_multi_feature_report

    # Generate report across all features
    report = generate_multi_feature_report()
    print(format_multi_feature_console(report))

See Also:
    testing.traceability.models for TraceabilityMatrix definition
    testing.traceability.parser for requirement extraction
    testing.traceability.scanner for test discovery
    testing.traceability.mapper for requirement-to-test mapping
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from testing.traceability.mapper import map_requirements_to_tests
from testing.traceability.models import (
    CoverageStatus,
    FeatureCoverage,
    MultiFeatureReport,
    RequirementMarker,
    TraceabilityMatrix,
)
from testing.traceability.parser import parse_requirements
from testing.traceability.scanner import scan_tests

# Feature names mapping
FEATURE_NAMES: dict[str, str] = {
    "001": "Core Foundation",
    "002": "CLI Interface",
    "003": "Orchestration Layer",
    "004": "Storage Catalog",
    "005": "Consumption Layer",
    "006": "Integration Testing",
}


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


def generate_multi_feature_report(
    project_root: Path | None = None,
) -> MultiFeatureReport:
    """Generate a comprehensive coverage report across all features.

    Auto-discovers all specification files and test directories, then
    generates coverage analysis for each feature (001-006+).

    Args:
        project_root: Root directory of the project. Defaults to
            discovering from current working directory.

    Returns:
        MultiFeatureReport with per-feature breakdown and totals.

    Example:
        >>> report = generate_multi_feature_report()
        >>> print(f"Overall: {report.total_coverage_percentage:.1f}%")
        >>> for feature in report.features:
        ...     print(f"{feature.feature_id}: {feature.coverage_percentage:.1f}%")
    """
    if project_root is None:
        # Try to find project root by looking for specs/ directory
        project_root = Path.cwd()
        while project_root != project_root.parent:
            if (project_root / "specs").exists():
                break
            project_root = project_root.parent

    specs_dir = project_root / "specs"
    packages_dir = project_root / "packages"
    testing_dir = project_root / "testing"

    # Discover all spec files
    spec_files_by_feature: dict[str, list[Path]] = defaultdict(list)
    if specs_dir.exists():
        for spec_dir in specs_dir.iterdir():
            if spec_dir.is_dir() and spec_dir.name[:3].isdigit():
                feature_id = spec_dir.name[:3]
                spec_file = spec_dir / "spec.md"
                if spec_file.exists():
                    spec_files_by_feature[feature_id].append(spec_file)

    # Discover all test directories
    test_dirs: list[Path] = []
    if packages_dir.exists():
        for pkg_dir in packages_dir.iterdir():
            if pkg_dir.is_dir():
                integration_dir = pkg_dir / "tests" / "integration"
                if integration_dir.exists():
                    test_dirs.append(integration_dir)
                e2e_dir = pkg_dir / "tests" / "e2e"
                if e2e_dir.exists():
                    test_dirs.append(e2e_dir)
    if (testing_dir / "tests").exists():
        test_dirs.append(testing_dir / "tests")
    if (testing_dir / "traceability" / "tests").exists():
        test_dirs.append(testing_dir / "traceability" / "tests")

    # Scan all tests once
    all_tests = scan_tests(test_dirs)

    # Count markers by feature
    markers_by_feature: dict[str, int] = defaultdict(int)
    covered_reqs_by_feature: dict[str, set[str]] = defaultdict(set)

    for test in all_tests:
        for req_id in test.requirement_ids:
            marker = RequirementMarker.from_string(req_id)
            if marker:
                markers_by_feature[marker.feature_id] += 1
                covered_reqs_by_feature[marker.feature_id].add(marker.full_id)

    # Parse requirements for each feature
    features: list[FeatureCoverage] = []
    gaps_by_feature: dict[str, list[str]] = {}
    total_requirements = 0
    total_covered = 0
    total_markers = 0

    for feature_id in sorted(spec_files_by_feature.keys()):
        spec_files = spec_files_by_feature[feature_id]
        feature_name = FEATURE_NAMES.get(feature_id, f"Feature {feature_id}")

        # Parse requirements for this feature
        all_requirements: list[str] = []
        for spec_file in spec_files:
            requirements = parse_requirements(spec_file)
            all_requirements.extend([r.id for r in requirements])

        total_reqs = len(all_requirements)
        covered_set = covered_reqs_by_feature.get(feature_id, set())
        covered_count = len([r for r in all_requirements if r in covered_set])
        uncovered_count = total_reqs - covered_count
        coverage_pct = (covered_count / total_reqs * 100) if total_reqs > 0 else 100.0
        marker_count = markers_by_feature.get(feature_id, 0)

        # Track gaps
        uncovered_reqs = [r for r in all_requirements if r not in covered_set]
        if uncovered_reqs:
            gaps_by_feature[feature_id] = uncovered_reqs

        features.append(
            FeatureCoverage(
                feature_id=feature_id,
                feature_name=feature_name,
                total_requirements=total_reqs,
                covered=covered_count,
                uncovered=uncovered_count,
                coverage_percentage=coverage_pct,
                total_markers=marker_count,
            )
        )

        total_requirements += total_reqs
        total_covered += covered_count
        total_markers += marker_count

    overall_pct = (total_covered / total_requirements * 100) if total_requirements > 0 else 100.0

    return MultiFeatureReport(
        features=features,
        total_requirements=total_requirements,
        total_covered=total_covered,
        total_coverage_percentage=overall_pct,
        total_markers=total_markers,
        gaps_by_feature=gaps_by_feature,
    )


def format_multi_feature_console(report: MultiFeatureReport) -> str:
    """Format multi-feature report for terminal output.

    Creates a human-readable console report showing per-feature coverage
    and overall statistics.

    Args:
        report: MultiFeatureReport to format.

    Returns:
        Formatted string suitable for terminal display.

    Example:
        >>> report = generate_multi_feature_report()
        >>> print(format_multi_feature_console(report))
        Multi-Feature Traceability Report
        ==================================
        ...
    """
    lines: list[str] = []

    # Header
    lines.append("Multi-Feature Traceability Report")
    lines.append("=" * 70)
    lines.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")

    # Summary table header
    lines.append(f"{'Feature':<6} {'Name':<25} {'Reqs':>5} {'Cover':>5} {'Pct':>6} {'Markers':>8}")
    lines.append("-" * 70)

    # Per-feature rows
    for feature in report.features:
        lines.append(
            f"{feature.feature_id:<6} {feature.feature_name:<25} "
            f"{feature.total_requirements:>5} {feature.covered:>5} "
            f"{feature.coverage_percentage:>5.1f}% {feature.total_markers:>8}"
        )

    # Totals
    lines.append("-" * 70)
    lines.append(
        f"{'TOTAL':<6} {'':<25} {report.total_requirements:>5} "
        f"{report.total_covered:>5} {report.total_coverage_percentage:>5.1f}% "
        f"{report.total_markers:>8}"
    )
    lines.append("")

    # Coverage gaps summary
    total_gaps = sum(len(gaps) for gaps in report.gaps_by_feature.values())
    if total_gaps > 0:
        lines.append(f"Coverage Gaps: {total_gaps} uncovered requirements")
        lines.append("-" * 40)
        for feature_id, gaps in sorted(report.gaps_by_feature.items()):
            feature_name = FEATURE_NAMES.get(feature_id, f"Feature {feature_id}")
            lines.append(f"  {feature_id} - {feature_name} ({len(gaps)} gaps):")
            for gap in gaps[:5]:  # Show first 5 gaps
                lines.append(f"    - {gap}")
            if len(gaps) > 5:
                lines.append(f"    ... and {len(gaps) - 5} more")
        lines.append("")
    else:
        lines.append("No coverage gaps - all requirements covered!")
        lines.append("")

    return "\n".join(lines)


def format_multi_feature_json(report: MultiFeatureReport) -> str:
    """Format multi-feature report as CI-compatible JSON.

    Args:
        report: MultiFeatureReport to format.

    Returns:
        JSON string with structured multi-feature data.
    """
    import json

    report_data = {
        "generated_at": report.generated_at.isoformat(),
        "total_requirements": report.total_requirements,
        "total_covered": report.total_covered,
        "total_coverage_percentage": report.total_coverage_percentage,
        "total_markers": report.total_markers,
        "features": [
            {
                "feature_id": f.feature_id,
                "feature_name": f.feature_name,
                "total_requirements": f.total_requirements,
                "covered": f.covered,
                "uncovered": f.uncovered,
                "coverage_percentage": f.coverage_percentage,
                "total_markers": f.total_markers,
            }
            for f in report.features
        ],
        "gaps_by_feature": report.gaps_by_feature,
    }

    return json.dumps(report_data, indent=2)


__all__ = [
    "generate_matrix",
    "format_console_report",
    "format_json_report",
    "generate_multi_feature_report",
    "format_multi_feature_console",
    "format_multi_feature_json",
    "FEATURE_NAMES",
]
