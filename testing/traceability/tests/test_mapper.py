"""Tests for testing.traceability.mapper module.

These tests verify requirement-to-test mapping logic:
- Matching requirements to tests by FR-XXX ID
- Coverage status determination
- TraceabilityMapping creation
"""

from __future__ import annotations

from testing.traceability.models import (
    CoverageStatus,
    Requirement,
    RequirementCategory,
    TraceabilityMapping,
)

# Import Test with underscore prefix to avoid pytest collection conflicts
from testing.traceability.models import Test as _Test


class TestMapRequirementsToTests:
    """Tests for map_requirements_to_tests function."""

    def test_map_requirements_to_tests_can_be_imported(self) -> None:
        """Verify map_requirements_to_tests function can be imported."""
        from testing.traceability.mapper import map_requirements_to_tests

        assert map_requirements_to_tests is not None
        assert callable(map_requirements_to_tests)

    def test_map_empty_requirements(self) -> None:
        """Mapping with no requirements returns empty list."""
        from testing.traceability.mapper import map_requirements_to_tests

        mappings = map_requirements_to_tests([], [])

        assert mappings == []

    def test_map_uncovered_requirement(self) -> None:
        """Requirement with no matching tests has UNCOVERED status."""
        from testing.traceability.mapper import map_requirements_to_tests

        requirements = [
            Requirement(
                id="FR-001",
                spec_file="spec.md",
                line_number=10,
                text="Must have traceability",
                category=RequirementCategory.TRACEABILITY,
            )
        ]
        tests: list[_Test] = []

        mappings = map_requirements_to_tests(requirements, tests)

        assert len(mappings) == 1
        assert mappings[0].requirement_id == "FR-001"
        assert mappings[0].coverage_status == CoverageStatus.UNCOVERED
        assert mappings[0].test_ids == []

    def test_map_covered_requirement(self) -> None:
        """Requirement with matching test has COVERED status."""
        from testing.traceability.mapper import map_requirements_to_tests

        requirements = [
            Requirement(
                id="FR-001",
                spec_file="spec.md",
                line_number=10,
                text="Must have traceability",
                category=RequirementCategory.TRACEABILITY,
            )
        ]
        tests = [
            _Test(
                file_path="test_example.py",
                function_name="test_traceability",
                class_name=None,
                markers=[],
                requirement_ids=["FR-001"],
                package="floe-core",
            )
        ]

        mappings = map_requirements_to_tests(requirements, tests)

        assert len(mappings) == 1
        assert mappings[0].requirement_id == "FR-001"
        assert mappings[0].coverage_status == CoverageStatus.COVERED
        assert len(mappings[0].test_ids) == 1

    def test_map_multiple_tests_for_requirement(self) -> None:
        """Requirement can be covered by multiple tests."""
        from testing.traceability.mapper import map_requirements_to_tests

        requirements = [
            Requirement(
                id="FR-001",
                spec_file="spec.md",
                line_number=10,
                text="Must have traceability",
                category=RequirementCategory.TRACEABILITY,
            )
        ]
        tests = [
            _Test(
                file_path="test_a.py",
                function_name="test_traceability_a",
                class_name=None,
                markers=[],
                requirement_ids=["FR-001"],
                package="floe-core",
            ),
            _Test(
                file_path="test_b.py",
                function_name="test_traceability_b",
                class_name=None,
                markers=[],
                requirement_ids=["FR-001"],
                package="floe-core",
            ),
        ]

        mappings = map_requirements_to_tests(requirements, tests)

        assert len(mappings) == 1
        assert mappings[0].requirement_id == "FR-001"
        assert mappings[0].coverage_status == CoverageStatus.COVERED
        assert len(mappings[0].test_ids) == 2

    def test_map_test_covering_multiple_requirements(self) -> None:
        """Single test can cover multiple requirements."""
        from testing.traceability.mapper import map_requirements_to_tests

        requirements = [
            Requirement(
                id="FR-032",
                spec_file="spec.md",
                line_number=10,
                text="Contract boundary test 1",
                category=RequirementCategory.CONTRACT_BOUNDARY,
            ),
            Requirement(
                id="FR-033",
                spec_file="spec.md",
                line_number=11,
                text="Contract boundary test 2",
                category=RequirementCategory.CONTRACT_BOUNDARY,
            ),
        ]
        tests = [
            _Test(
                file_path="test_contract.py",
                function_name="test_contract_boundary",
                class_name=None,
                markers=[],
                requirement_ids=["FR-032", "FR-033"],
                package="floe-core",
            )
        ]

        mappings = map_requirements_to_tests(requirements, tests)

        assert len(mappings) == 2
        fr_032 = next(m for m in mappings if m.requirement_id == "FR-032")
        fr_033 = next(m for m in mappings if m.requirement_id == "FR-033")
        assert fr_032.coverage_status == CoverageStatus.COVERED
        assert fr_033.coverage_status == CoverageStatus.COVERED


class TestTestIdGeneration:
    """Tests for test ID generation in mappings."""

    def test_test_id_without_class(self) -> None:
        """Test ID format for module-level function."""
        from testing.traceability.mapper import map_requirements_to_tests

        requirements = [
            Requirement(
                id="FR-001",
                spec_file="spec.md",
                line_number=10,
                text="Test requirement",
                category=RequirementCategory.EXECUTION,
            )
        ]
        tests = [
            _Test(
                file_path="test_example.py",
                function_name="test_something",
                class_name=None,
                markers=[],
                requirement_ids=["FR-001"],
                package="floe-core",
            )
        ]

        mappings = map_requirements_to_tests(requirements, tests)

        assert len(mappings) == 1
        assert "test_example.py::test_something" in mappings[0].test_ids

    def test_test_id_with_class(self) -> None:
        """Test ID format for method in test class."""
        from testing.traceability.mapper import map_requirements_to_tests

        requirements = [
            Requirement(
                id="FR-012",
                spec_file="spec.md",
                line_number=10,
                text="Polaris test",
                category=RequirementCategory.EXECUTION,
            )
        ]
        tests = [
            _Test(
                file_path="test_catalog.py",
                function_name="test_create_namespace",
                class_name="TestPolarisCatalog",
                markers=[],
                requirement_ids=["FR-012"],
                package="floe-polaris",
            )
        ]

        mappings = map_requirements_to_tests(requirements, tests)

        assert len(mappings) == 1
        expected_id = "test_catalog.py::TestPolarisCatalog::test_create_namespace"
        assert expected_id in mappings[0].test_ids


class TestMixedCoverage:
    """Tests for scenarios with mixed coverage."""

    def test_some_covered_some_uncovered(self) -> None:
        """Mixed coverage scenario."""
        from testing.traceability.mapper import map_requirements_to_tests

        requirements = [
            Requirement(
                id="FR-001",
                spec_file="spec.md",
                line_number=10,
                text="Covered requirement",
                category=RequirementCategory.TRACEABILITY,
            ),
            Requirement(
                id="FR-002",
                spec_file="spec.md",
                line_number=11,
                text="Uncovered requirement",
                category=RequirementCategory.TRACEABILITY,
            ),
        ]
        tests = [
            _Test(
                file_path="test_example.py",
                function_name="test_covered",
                class_name=None,
                markers=[],
                requirement_ids=["FR-001"],
                package="floe-core",
            )
        ]

        mappings = map_requirements_to_tests(requirements, tests)

        assert len(mappings) == 2
        fr_001 = next(m for m in mappings if m.requirement_id == "FR-001")
        fr_002 = next(m for m in mappings if m.requirement_id == "FR-002")
        assert fr_001.coverage_status == CoverageStatus.COVERED
        assert fr_002.coverage_status == CoverageStatus.UNCOVERED


class TestReturnType:
    """Tests for return type verification."""

    def test_returns_traceability_mapping_objects(self) -> None:
        """Returned objects are TraceabilityMapping instances."""
        from testing.traceability.mapper import map_requirements_to_tests

        requirements = [
            Requirement(
                id="FR-001",
                spec_file="spec.md",
                line_number=10,
                text="Test requirement",
                category=RequirementCategory.EXECUTION,
            )
        ]
        tests: list[_Test] = []

        mappings = map_requirements_to_tests(requirements, tests)

        assert len(mappings) == 1
        assert isinstance(mappings[0], TraceabilityMapping)
