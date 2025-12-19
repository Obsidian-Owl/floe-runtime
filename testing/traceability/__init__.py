"""Traceability module for mapping functional requirements to integration tests.

This module provides tools for:
- Extracting requirements (FR-XXX) from specification files
- Scanning tests for requirement markers
- Generating traceability matrices and coverage reports
- CI/CD integration for coverage threshold enforcement

Key Components:
    - models: Pydantic models (Requirement, Test, TraceabilityMapping, TraceabilityMatrix)
    - parser: Extract requirements from spec.md files
    - scanner: Discover tests with @pytest.mark.requirement markers
    - mapper: Create requirement-to-test mappings
    - reporter: Generate coverage reports in various formats

Usage:
    from testing.traceability import generate_matrix, generate_report

    # Generate traceability matrix
    matrix = generate_matrix(
        spec_files=["specs/006-integration-testing/spec.md"],
        test_dirs=["packages/*/tests/integration/"]
    )

    # Check coverage
    print(f"Coverage: {matrix.get_coverage_percentage():.1f}%")

    # Generate CI report
    report = generate_report(feature_id="006")
    if report.coverage_percentage < 80:
        sys.exit(1)

See Also:
    - specs/006-integration-testing/data-model.md for entity definitions
    - specs/006-integration-testing/spec.md for functional requirements
"""

from __future__ import annotations

__version__ = "0.1.0"

# Exports will be added as modules are implemented:
# - T002: models (Requirement, Test, TraceabilityMapping, TraceabilityMatrix, etc.)
# - T006: parser (parse_requirements)
# - T007: scanner (scan_tests)
# - T008: mapper (map_requirements_to_tests)
# - T013: reporter (generate_matrix, generate_report)

from testing.traceability.mapper import map_requirements_to_tests
from testing.traceability.models import (
    CoverageStatus,
    PackageCoverage,
    Requirement,
    RequirementCategory,
    Test,
    TestMarker,
    TestResult,
    TraceabilityMapping,
    TraceabilityMatrix,
    TraceabilityReport,
)
from testing.traceability.parser import parse_requirements
from testing.traceability.reporter import (
    format_console_report,
    format_json_report,
    generate_matrix,
)
from testing.traceability.scanner import scan_tests

__all__: list[str] = [
    "__version__",
    # Models (T002)
    "RequirementCategory",
    "Requirement",
    "TestMarker",
    "Test",
    "CoverageStatus",
    "TraceabilityMapping",
    "TraceabilityMatrix",
    "TestResult",
    "PackageCoverage",
    "TraceabilityReport",
    # Functions (T006-T015)
    "parse_requirements",
    "scan_tests",
    "map_requirements_to_tests",
    "generate_matrix",
    "format_console_report",
    "format_json_report",
]
