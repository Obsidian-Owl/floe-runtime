"""Tests for testing.traceability.models Pydantic models.

These tests verify the data models for the traceability system:
- Requirement: Functional requirement from spec files
- Test: Integration test with requirement markers
- TraceabilityMapping: Requirement-to-test mapping
- TraceabilityMatrix: Complete feature traceability
- TraceabilityReport: CI-compatible report format
"""

from __future__ import annotations

from pydantic import ValidationError
import pytest


class TestRequirementCategory:
    """Tests for RequirementCategory enum."""

    def test_all_categories_exist(self) -> None:
        """Verify all expected categories are defined."""
        from testing.traceability.models import RequirementCategory

        expected = {
            "traceability",
            "execution",
            "package_coverage",
            "infrastructure",
            "shared_fixtures",
            "production_config",
            "observability",
            "row_level_security",
            "standalone_first",
            "contract_boundary",
        }
        actual = {c.value for c in RequirementCategory}
        assert actual == expected

    def test_category_is_string_enum(self) -> None:
        """Verify category values are strings."""
        from testing.traceability.models import RequirementCategory

        assert RequirementCategory.TRACEABILITY.value == "traceability"
        assert isinstance(RequirementCategory.TRACEABILITY.value, str)


class TestRequirement:
    """Tests for Requirement model."""

    def test_valid_requirement(self) -> None:
        """Test creating a valid requirement."""
        from testing.traceability.models import Requirement, RequirementCategory

        req = Requirement(
            id="FR-001",
            spec_file="specs/006-integration-testing/spec.md",
            line_number=42,
            text="The system SHALL generate traceability matrices",
            category=RequirementCategory.TRACEABILITY,
        )

        assert req.id == "FR-001"
        assert req.spec_file == "specs/006-integration-testing/spec.md"
        assert req.line_number == 42
        assert req.category == RequirementCategory.TRACEABILITY
        assert req.priority == "P2"  # Default

    def test_requirement_with_priority(self) -> None:
        """Test requirement with explicit priority."""
        from testing.traceability.models import Requirement, RequirementCategory

        req = Requirement(
            id="FR-010",
            spec_file="spec.md",
            line_number=1,
            text="Critical requirement",
            category=RequirementCategory.EXECUTION,
            priority="P1",
        )

        assert req.priority == "P1"

    def test_invalid_requirement_id_format(self) -> None:
        """Test that invalid requirement ID raises ValidationError."""
        from testing.traceability.models import Requirement, RequirementCategory

        with pytest.raises(ValidationError) as exc_info:
            Requirement(
                id="INVALID",  # Should be FR-XXX
                spec_file="spec.md",
                line_number=1,
                text="Test",
                category=RequirementCategory.TRACEABILITY,
            )

        assert "id" in str(exc_info.value)

    def test_invalid_priority_format(self) -> None:
        """Test that invalid priority raises ValidationError."""
        from testing.traceability.models import Requirement, RequirementCategory

        with pytest.raises(ValidationError) as exc_info:
            Requirement(
                id="FR-001",
                spec_file="spec.md",
                line_number=1,
                text="Test",
                category=RequirementCategory.TRACEABILITY,
                priority="HIGH",  # Should be P1, P2, or P3
            )

        assert "priority" in str(exc_info.value)


class TestTestMarker:
    """Tests for TestMarker enum."""

    def test_all_markers_exist(self) -> None:
        """Verify all expected markers are defined."""
        from testing.traceability.models import TestMarker

        expected = {"integration", "e2e", "slow", "requires_docker"}
        actual = {m.value for m in TestMarker}
        assert actual == expected


class TestTest:
    """Tests for Test model."""

    def test_valid_test(self) -> None:
        """Test creating a valid test."""
        from testing.traceability.models import Test

        test = Test(
            file_path="packages/floe-polaris/tests/integration/test_catalog.py",
            function_name="test_create_namespace",
            package="floe-polaris",
        )

        assert test.file_path == "packages/floe-polaris/tests/integration/test_catalog.py"
        assert test.function_name == "test_create_namespace"
        assert test.class_name is None
        assert test.markers == []
        assert test.requirement_ids == []
        assert test.package == "floe-polaris"

    def test_test_with_class_and_markers(self) -> None:
        """Test creating a test with class and markers."""
        from testing.traceability.models import Test, TestMarker

        test = Test(
            file_path="tests/integration/test_polaris.py",
            function_name="test_connection",
            class_name="TestPolarisCatalog",
            markers=[TestMarker.INTEGRATION, TestMarker.REQUIRES_DOCKER],
            requirement_ids=["FR-012", "FR-013"],
            package="floe-polaris",
        )

        assert test.class_name == "TestPolarisCatalog"
        assert TestMarker.INTEGRATION in test.markers
        assert "FR-012" in test.requirement_ids


class TestCoverageStatus:
    """Tests for CoverageStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """Verify all expected statuses are defined."""
        from testing.traceability.models import CoverageStatus

        expected = {"covered", "partial", "uncovered", "excluded"}
        actual = {s.value for s in CoverageStatus}
        assert actual == expected


class TestTraceabilityMapping:
    """Tests for TraceabilityMapping model."""

    def test_valid_mapping(self) -> None:
        """Test creating a valid mapping."""
        from testing.traceability.models import CoverageStatus, TraceabilityMapping

        mapping = TraceabilityMapping(
            requirement_id="FR-001",
            test_ids=["test_file.py::TestClass::test_method"],
            coverage_status=CoverageStatus.COVERED,
        )

        assert mapping.requirement_id == "FR-001"
        assert len(mapping.test_ids) == 1
        assert mapping.coverage_status == CoverageStatus.COVERED
        assert mapping.notes is None

    def test_mapping_defaults(self) -> None:
        """Test mapping with default values."""
        from testing.traceability.models import CoverageStatus, TraceabilityMapping

        mapping = TraceabilityMapping(requirement_id="FR-002")

        assert mapping.test_ids == []
        assert mapping.coverage_status == CoverageStatus.UNCOVERED
        assert mapping.notes is None

    def test_mapping_with_notes(self) -> None:
        """Test mapping with notes."""
        from testing.traceability.models import CoverageStatus, TraceabilityMapping

        mapping = TraceabilityMapping(
            requirement_id="FR-003",
            coverage_status=CoverageStatus.EXCLUDED,
            notes="Not testable in CI - requires manual verification",
        )

        assert mapping.notes == "Not testable in CI - requires manual verification"


class TestTraceabilityMatrix:
    """Tests for TraceabilityMatrix model."""

    def test_valid_matrix(self) -> None:
        """Test creating a valid matrix."""
        from testing.traceability.models import (
            CoverageStatus,
            Requirement,
            RequirementCategory,
            Test,
            TraceabilityMapping,
            TraceabilityMatrix,
        )

        matrix = TraceabilityMatrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=["specs/006-integration-testing/spec.md"],
            requirements=[
                Requirement(
                    id="FR-001",
                    spec_file="spec.md",
                    line_number=10,
                    text="Test requirement",
                    category=RequirementCategory.TRACEABILITY,
                )
            ],
            tests=[
                Test(
                    file_path="test.py",
                    function_name="test_func",
                    package="floe-core",
                )
            ],
            mappings=[
                TraceabilityMapping(
                    requirement_id="FR-001",
                    test_ids=["test.py::test_func"],
                    coverage_status=CoverageStatus.COVERED,
                )
            ],
        )

        assert matrix.feature_id == "006"
        assert matrix.feature_name == "Integration Testing"
        assert len(matrix.requirements) == 1
        assert len(matrix.tests) == 1
        assert len(matrix.mappings) == 1
        assert matrix.generated_at is not None

    def test_coverage_percentage_all_covered(self) -> None:
        """Test coverage percentage when all requirements are covered."""
        from testing.traceability.models import (
            CoverageStatus,
            Requirement,
            RequirementCategory,
            TraceabilityMapping,
            TraceabilityMatrix,
        )

        matrix = TraceabilityMatrix(
            feature_id="006",
            feature_name="Test",
            spec_files=[],
            requirements=[
                Requirement(
                    id="FR-001",
                    spec_file="s.md",
                    line_number=1,
                    text="R1",
                    category=RequirementCategory.TRACEABILITY,
                ),
                Requirement(
                    id="FR-002",
                    spec_file="s.md",
                    line_number=2,
                    text="R2",
                    category=RequirementCategory.TRACEABILITY,
                ),
            ],
            tests=[],
            mappings=[
                TraceabilityMapping(
                    requirement_id="FR-001", coverage_status=CoverageStatus.COVERED
                ),
                TraceabilityMapping(
                    requirement_id="FR-002", coverage_status=CoverageStatus.EXCLUDED
                ),
            ],
        )

        assert matrix.get_coverage_percentage() == pytest.approx(100.0)

    def test_coverage_percentage_partial(self) -> None:
        """Test coverage percentage with partial coverage."""
        from testing.traceability.models import (
            CoverageStatus,
            Requirement,
            RequirementCategory,
            TraceabilityMapping,
            TraceabilityMatrix,
        )

        matrix = TraceabilityMatrix(
            feature_id="006",
            feature_name="Test",
            spec_files=[],
            requirements=[
                Requirement(
                    id=f"FR-00{i}",
                    spec_file="s.md",
                    line_number=i,
                    text=f"R{i}",
                    category=RequirementCategory.TRACEABILITY,
                )
                for i in range(1, 5)
            ],
            tests=[],
            mappings=[
                TraceabilityMapping(
                    requirement_id="FR-001", coverage_status=CoverageStatus.COVERED
                ),
                TraceabilityMapping(
                    requirement_id="FR-002", coverage_status=CoverageStatus.UNCOVERED
                ),
                TraceabilityMapping(
                    requirement_id="FR-003", coverage_status=CoverageStatus.PARTIAL
                ),
                TraceabilityMapping(
                    requirement_id="FR-004", coverage_status=CoverageStatus.UNCOVERED
                ),
            ],
        )

        # Only FR-001 is COVERED (1/4 = 25%)
        assert matrix.get_coverage_percentage() == pytest.approx(25.0)

    def test_coverage_percentage_empty(self) -> None:
        """Test coverage percentage with no requirements returns 100%."""
        from testing.traceability.models import TraceabilityMatrix

        matrix = TraceabilityMatrix(
            feature_id="006",
            feature_name="Test",
            spec_files=[],
            requirements=[],
            tests=[],
            mappings=[],
        )

        assert matrix.get_coverage_percentage() == pytest.approx(100.0)

    def test_get_gaps(self) -> None:
        """Test getting uncovered requirements."""
        from testing.traceability.models import (
            CoverageStatus,
            Requirement,
            RequirementCategory,
            TraceabilityMapping,
            TraceabilityMatrix,
        )

        req1 = Requirement(
            id="FR-001",
            spec_file="s.md",
            line_number=1,
            text="Covered",
            category=RequirementCategory.TRACEABILITY,
        )
        req2 = Requirement(
            id="FR-002",
            spec_file="s.md",
            line_number=2,
            text="Uncovered gap",
            category=RequirementCategory.EXECUTION,
        )

        matrix = TraceabilityMatrix(
            feature_id="006",
            feature_name="Test",
            spec_files=[],
            requirements=[req1, req2],
            tests=[],
            mappings=[
                TraceabilityMapping(
                    requirement_id="FR-001", coverage_status=CoverageStatus.COVERED
                ),
                TraceabilityMapping(
                    requirement_id="FR-002", coverage_status=CoverageStatus.UNCOVERED
                ),
            ],
        )

        gaps = matrix.get_gaps()
        assert len(gaps) == 1
        assert gaps[0].id == "FR-002"
        assert gaps[0].text == "Uncovered gap"


class TestTestResult:
    """Tests for TestResult model."""

    def test_valid_test_result(self) -> None:
        """Test creating a valid test result."""
        from testing.traceability.models import TestResult

        result = TestResult(
            test_id="test_file.py::TestClass::test_method",
            status="passed",
            duration_ms=150,
        )

        assert result.test_id == "test_file.py::TestClass::test_method"
        assert result.status == "passed"
        assert result.duration_ms == 150
        assert result.error_message is None

    def test_failed_test_result(self) -> None:
        """Test creating a failed test result with error message."""
        from testing.traceability.models import TestResult

        result = TestResult(
            test_id="test.py::test_func",
            status="failed",
            duration_ms=50,
            error_message="AssertionError: expected True",
        )

        assert result.status == "failed"
        assert result.error_message == "AssertionError: expected True"


class TestPackageCoverage:
    """Tests for PackageCoverage model."""

    def test_valid_package_coverage(self) -> None:
        """Test creating valid package coverage."""
        from testing.traceability.models import PackageCoverage

        coverage = PackageCoverage(
            package="floe-polaris",
            total_requirements=10,
            covered=7,
            partial=1,
            uncovered=2,
            coverage_percentage=70.0,
        )

        assert coverage.package == "floe-polaris"
        assert coverage.total_requirements == 10
        assert coverage.covered == 7
        assert coverage.coverage_percentage == pytest.approx(70.0)


class TestTraceabilityReport:
    """Tests for TraceabilityReport model."""

    def test_valid_report(self) -> None:
        """Test creating a valid report."""
        from testing.traceability.models import (
            PackageCoverage,
            TestResult,
            TraceabilityReport,
        )

        report = TraceabilityReport(
            feature_id="006",
            generated_at="2025-12-19T10:00:00Z",
            total_requirements=35,
            covered=28,
            partial=3,
            uncovered=4,
            excluded=0,
            coverage_percentage=80.0,
            packages=[
                PackageCoverage(
                    package="floe-core",
                    total_requirements=10,
                    covered=8,
                    partial=1,
                    uncovered=1,
                    coverage_percentage=80.0,
                )
            ],
            test_results=[
                TestResult(
                    test_id="test.py::test_func",
                    status="passed",
                    duration_ms=100,
                )
            ],
            gaps=["FR-030", "FR-031", "FR-032", "FR-033"],
        )

        assert report.feature_id == "006"
        assert report.total_requirements == 35
        assert report.covered == 28
        assert report.coverage_percentage == pytest.approx(80.0)
        assert len(report.gaps) == 4
        assert "FR-030" in report.gaps
