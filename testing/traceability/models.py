"""Pydantic models for the traceability system.

This module defines the data models for mapping functional requirements
(FR-XXX) from specification files to integration tests.

Models:
    RequirementCategory: Enum of requirement categories
    Requirement: A functional requirement from a specification
    TestMarker: Enum of pytest markers for integration tests
    Test: An integration test that covers requirements
    CoverageStatus: Enum of coverage statuses
    TraceabilityMapping: Mapping between a requirement and its tests
    TraceabilityMatrix: Complete traceability matrix for a feature
    TestResult: Result of a single test execution
    PackageCoverage: Coverage summary for a package
    TraceabilityReport: CI-compatible traceability report

See Also:
    specs/006-integration-testing/data-model.md for detailed documentation
    specs/006-integration-testing/contracts/ for JSON schemas
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RequirementCategory(str, Enum):
    """Categories for functional requirements.

    These categories help organize requirements by their primary concern
    and enable filtering in coverage reports.
    """

    TRACEABILITY = "traceability"
    EXECUTION = "execution"
    PACKAGE_COVERAGE = "package_coverage"
    INFRASTRUCTURE = "infrastructure"
    SHARED_FIXTURES = "shared_fixtures"
    PRODUCTION_CONFIG = "production_config"
    OBSERVABILITY = "observability"
    ROW_LEVEL_SECURITY = "row_level_security"
    STANDALONE_FIRST = "standalone_first"
    CONTRACT_BOUNDARY = "contract_boundary"


class Requirement(BaseModel):
    """A functional requirement from a specification.

    Requirements are extracted from spec.md files and identified by
    their FR-XXX identifier pattern.

    Attributes:
        id: Unique identifier (e.g., "FR-001")
        spec_file: Path to the specification file
        line_number: Line number in spec file where requirement is defined
        text: Full text of the requirement
        category: Category classification
        priority: Priority level (P1, P2, P3)

    Example:
        >>> req = Requirement(
        ...     id="FR-001",
        ...     spec_file="specs/006-integration-testing/spec.md",
        ...     line_number=42,
        ...     text="The system SHALL generate traceability matrices",
        ...     category=RequirementCategory.TRACEABILITY,
        ... )
    """

    id: str = Field(..., pattern=r"^FR-\d{3}$")
    spec_file: str
    line_number: int
    text: str
    category: RequirementCategory
    priority: str = Field(default="P2", pattern=r"^P[1-3]$")


class TestMarker(str, Enum):
    """Pytest markers for integration tests.

    These markers are used to categorize tests and control test execution.
    """

    INTEGRATION = "integration"
    E2E = "e2e"
    SLOW = "slow"
    REQUIRES_DOCKER = "requires_docker"


class Test(BaseModel):
    """An integration test that covers requirements.

    Tests are discovered by scanning test files for functions decorated
    with @pytest.mark.requirement or @pytest.mark.requirements markers.

    Attributes:
        file_path: Path to the test file
        function_name: Test function name
        class_name: Test class name (if any)
        markers: List of pytest markers
        requirement_ids: List of FR-XXX IDs this test covers
        package: Package name (e.g., "floe-core")

    Example:
        >>> test = Test(
        ...     file_path="packages/floe-polaris/tests/integration/test_catalog.py",
        ...     function_name="test_create_namespace",
        ...     class_name="TestPolarisCatalog",
        ...     markers=[TestMarker.INTEGRATION],
        ...     requirement_ids=["FR-012"],
        ...     package="floe-polaris",
        ... )
    """

    file_path: str
    function_name: str
    class_name: str | None = None
    markers: list[TestMarker] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    package: str


class CoverageStatus(str, Enum):
    """Coverage status for a requirement.

    Attributes:
        COVERED: Has at least one passing test
        PARTIAL: Has tests but they're incomplete/failing
        UNCOVERED: No tests exist
        EXCLUDED: Intentionally not tested (document reason)
    """

    COVERED = "covered"
    PARTIAL = "partial"
    UNCOVERED = "uncovered"
    EXCLUDED = "excluded"


class TraceabilityMapping(BaseModel):
    """Mapping between a requirement and its tests.

    Attributes:
        requirement_id: The requirement ID (FR-XXX)
        test_ids: List of test identifiers (file::class::function)
        coverage_status: Current coverage status
        notes: Optional notes about coverage

    Example:
        >>> mapping = TraceabilityMapping(
        ...     requirement_id="FR-001",
        ...     test_ids=["test_report.py::TestMatrix::test_generation"],
        ...     coverage_status=CoverageStatus.COVERED,
        ... )
    """

    requirement_id: str
    test_ids: list[str] = Field(default_factory=list)
    coverage_status: CoverageStatus = CoverageStatus.UNCOVERED
    notes: str | None = None


class TraceabilityMatrix(BaseModel):
    """Complete traceability matrix for a feature.

    The matrix aggregates all requirements, tests, and their mappings
    for a specific feature, enabling coverage analysis and gap detection.

    Attributes:
        feature_id: Feature identifier (e.g., "006")
        feature_name: Human-readable feature name
        generated_at: Timestamp of generation
        spec_files: List of specification files analyzed
        requirements: All requirements extracted
        tests: All tests discovered
        mappings: Requirement-to-test mappings

    Example:
        >>> matrix = TraceabilityMatrix(
        ...     feature_id="006",
        ...     feature_name="Integration Testing",
        ...     spec_files=["specs/006-integration-testing/spec.md"],
        ...     requirements=[...],
        ...     tests=[...],
        ...     mappings=[...],
        ... )
        >>> print(f"Coverage: {matrix.get_coverage_percentage():.1f}%")
    """

    feature_id: str
    feature_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    spec_files: list[str]
    requirements: list[Requirement]
    tests: list[Test]
    mappings: list[TraceabilityMapping]

    def get_coverage_percentage(self) -> float:
        """Calculate overall coverage percentage.

        Returns:
            Percentage of requirements that are COVERED or EXCLUDED.
            Returns 100.0 if there are no requirements.
        """
        if not self.requirements:
            return 100.0
        covered = sum(
            1
            for m in self.mappings
            if m.coverage_status in (CoverageStatus.COVERED, CoverageStatus.EXCLUDED)
        )
        return (covered / len(self.requirements)) * 100

    def get_gaps(self) -> list[Requirement]:
        """Get requirements without test coverage.

        Returns:
            List of Requirement objects with UNCOVERED status.
        """
        uncovered_ids = {
            m.requirement_id for m in self.mappings if m.coverage_status == CoverageStatus.UNCOVERED
        }
        return [r for r in self.requirements if r.id in uncovered_ids]


class TestResult(BaseModel):
    """Result of a single test execution.

    Used in TraceabilityReport to track test execution status.

    Attributes:
        test_id: Test identifier (file::class::function)
        status: Execution status (passed, failed, skipped, error)
        duration_ms: Test duration in milliseconds
        error_message: Error message if failed/error
    """

    test_id: str
    status: str
    duration_ms: int
    error_message: str | None = None


class PackageCoverage(BaseModel):
    """Coverage summary for a package.

    Provides per-package breakdown of requirement coverage.

    Attributes:
        package: Package name (e.g., "floe-polaris")
        total_requirements: Total FR-XXX count for this package
        covered: Fully covered count
        partial: Partially covered count
        uncovered: Uncovered count
        coverage_percentage: Package coverage percentage
    """

    package: str
    total_requirements: int
    covered: int
    partial: int
    uncovered: int
    coverage_percentage: float


class TraceabilityReport(BaseModel):
    """CI-compatible traceability report.

    This model matches the test-report.schema.json contract and is
    designed for integration with CI/CD pipelines.

    Attributes:
        feature_id: Feature identifier
        generated_at: ISO 8601 timestamp
        total_requirements: Total FR-XXX count
        covered: Fully covered count
        partial: Partially covered count
        uncovered: Uncovered count
        excluded: Excluded count
        coverage_percentage: Overall percentage
        packages: Per-package breakdown
        test_results: Test execution results
        gaps: List of uncovered requirement IDs

    Example:
        >>> report = generate_report(feature_id="006")
        >>> if report.coverage_percentage < 80:
        ...     print(f"Coverage {report.coverage_percentage:.1f}% below threshold")
        ...     sys.exit(1)
    """

    feature_id: str
    generated_at: str
    total_requirements: int
    covered: int
    partial: int
    uncovered: int
    excluded: int
    coverage_percentage: float
    packages: list[PackageCoverage]
    test_results: list[TestResult]
    gaps: list[str]
