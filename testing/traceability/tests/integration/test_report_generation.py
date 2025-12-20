"""Integration tests for traceability report generation.

These tests verify that the traceability system works correctly with
actual project spec files and integration test directories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from testing.traceability.models import CoverageStatus
from testing.traceability.reporter import (
    format_console_report,
    format_json_report,
    generate_matrix,
)

# Project root for finding actual spec files and test directories
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


class TestRealSpecFilesParsing:
    """Tests that verify parsing of actual project spec files."""

    @pytest.mark.requirement("006-FR-006")
    def test_parse_feature_006_spec(self) -> None:
        """Parse the actual 006-integration-testing spec file."""
        spec_path = PROJECT_ROOT / "specs" / "006-integration-testing" / "spec.md"

        if not spec_path.exists():
            pytest.fail(f"Spec file not found: {spec_path}")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_path],
            test_dirs=[],
        )

        # Should find requirements in the spec
        assert len(matrix.requirements) > 0, "No requirements found in spec"
        assert matrix.feature_id == "006"

        # Check that FR-012, FR-013, FR-014 are found (storage-catalog reqs)
        req_ids = {r.id for r in matrix.requirements}
        assert "FR-012" in req_ids, "FR-012 (floe-polaris) not found"
        assert "FR-013" in req_ids, "FR-013 (floe-iceberg) not found"
        assert "FR-014" in req_ids, "FR-014 (Dagster IOManager) not found"


class TestRealTestDirectoryScanning:
    """Tests that verify scanning of actual project test directories."""

    @pytest.mark.requirement("006-FR-006")
    def test_scan_floe_polaris_integration_tests(self) -> None:
        """Scan actual floe-polaris integration tests."""
        test_dir = PROJECT_ROOT / "packages" / "floe-polaris" / "tests" / "integration"

        if not test_dir.exists():
            pytest.fail(f"Test directory not found: {test_dir}")

        # Use empty spec to just scan tests
        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[test_dir],
        )

        # Should find tests with @pytest.mark.requirement("006-FR-012")
        fr012_tests = [t for t in matrix.tests if "FR-012" in t.requirement_ids]
        assert len(fr012_tests) > 0, "No FR-012 tests found in floe-polaris"

    @pytest.mark.requirement("006-FR-006")
    def test_scan_floe_iceberg_integration_tests(self) -> None:
        """Scan actual floe-iceberg integration tests."""
        test_dir = PROJECT_ROOT / "packages" / "floe-iceberg" / "tests" / "integration"

        if not test_dir.exists():
            pytest.fail(f"Test directory not found: {test_dir}")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[test_dir],
        )

        # Should find tests with @pytest.mark.requirement("006-FR-013") and FR-014
        fr013_tests = [t for t in matrix.tests if "FR-013" in t.requirement_ids]
        fr014_tests = [t for t in matrix.tests if "FR-014" in t.requirement_ids]

        assert len(fr013_tests) > 0, "No FR-013 tests found in floe-iceberg"
        assert len(fr014_tests) > 0, "No FR-014 tests found in floe-iceberg"


class TestEndToEndTraceabilityReport:
    """End-to-end integration tests for full traceability report generation."""

    @pytest.mark.requirement("006-FR-006")
    def test_generate_full_traceability_matrix(self) -> None:
        """Generate complete traceability matrix for feature 006."""
        spec_path = PROJECT_ROOT / "specs" / "006-integration-testing" / "spec.md"
        test_dirs = [
            PROJECT_ROOT / "packages" / "floe-polaris" / "tests" / "integration",
            PROJECT_ROOT / "packages" / "floe-iceberg" / "tests" / "integration",
        ]

        # Filter to existing directories
        existing_test_dirs = [d for d in test_dirs if d.exists()]

        if not spec_path.exists():
            pytest.fail(f"Spec file not found: {spec_path}")
        if not existing_test_dirs:
            pytest.fail("No test directories found")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_path],
            test_dirs=existing_test_dirs,
        )

        # Verify matrix structure
        assert matrix.feature_id == "006"
        assert matrix.feature_name == "Integration Testing"
        assert len(matrix.requirements) > 0
        assert len(matrix.tests) > 0
        assert len(matrix.mappings) > 0

        # Verify coverage tracking
        coverage = matrix.get_coverage_percentage()
        assert 0.0 <= coverage <= 100.0

        # FR-012, FR-013, FR-014 should be covered
        covered_reqs = [
            m.requirement_id for m in matrix.mappings if m.coverage_status == CoverageStatus.COVERED
        ]
        assert "FR-012" in covered_reqs, "FR-012 should be covered"
        assert "FR-013" in covered_reqs, "FR-013 should be covered"
        assert "FR-014" in covered_reqs, "FR-014 should be covered"

    @pytest.mark.requirement("006-FR-006")
    def test_console_report_format(self) -> None:
        """Verify console report format with real data."""
        spec_path = PROJECT_ROOT / "specs" / "006-integration-testing" / "spec.md"
        test_dirs = [
            PROJECT_ROOT / "packages" / "floe-polaris" / "tests" / "integration",
            PROJECT_ROOT / "packages" / "floe-iceberg" / "tests" / "integration",
        ]
        existing_test_dirs = [d for d in test_dirs if d.exists()]

        if not spec_path.exists() or not existing_test_dirs:
            pytest.skip("Required files not found")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_path],
            test_dirs=existing_test_dirs,
        )

        report = format_console_report(matrix)

        # Verify report structure
        assert "006" in report
        assert "Integration Testing" in report
        assert "Coverage:" in report
        assert "Requirements:" in report

        # Should show covered requirements
        assert "[COVERED]" in report or "Covered Requirements" in report

    @pytest.mark.requirement("006-FR-006")
    def test_json_report_format(self) -> None:
        """Verify JSON report format with real data."""
        import json

        spec_path = PROJECT_ROOT / "specs" / "006-integration-testing" / "spec.md"
        test_dirs = [
            PROJECT_ROOT / "packages" / "floe-polaris" / "tests" / "integration",
            PROJECT_ROOT / "packages" / "floe-iceberg" / "tests" / "integration",
        ]
        existing_test_dirs = [d for d in test_dirs if d.exists()]

        if not spec_path.exists() or not existing_test_dirs:
            pytest.skip("Required files not found")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_path],
            test_dirs=existing_test_dirs,
        )

        report = format_json_report(matrix)
        data = json.loads(report)

        # Verify JSON structure
        assert data["feature_id"] == "006"
        assert data["feature_name"] == "Integration Testing"
        assert "coverage_percentage" in data
        assert "requirements" in data
        assert "tests" in data
        assert "mappings" in data
        assert "gaps" in data

        # Verify data integrity
        assert isinstance(data["requirements"], list)
        assert isinstance(data["tests"], list)
        assert len(data["requirements"]) > 0
        assert len(data["tests"]) > 0


class TestCoverageThresholdValidation:
    """Tests for coverage threshold validation."""

    @pytest.mark.requirement("006-FR-006")
    def test_current_coverage_exceeds_minimum(self) -> None:
        """Verify current coverage meets minimum threshold."""
        spec_path = PROJECT_ROOT / "specs" / "006-integration-testing" / "spec.md"
        test_dirs = [
            PROJECT_ROOT / "packages" / "floe-polaris" / "tests" / "integration",
            PROJECT_ROOT / "packages" / "floe-iceberg" / "tests" / "integration",
        ]
        existing_test_dirs = [d for d in test_dirs if d.exists()]

        if not spec_path.exists() or not existing_test_dirs:
            pytest.skip("Required files not found")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_path],
            test_dirs=existing_test_dirs,
        )

        coverage = matrix.get_coverage_percentage()

        # Minimum threshold: at least 5% coverage (3+ requirements covered)
        minimum_threshold = 5.0
        assert (
            coverage >= minimum_threshold
        ), f"Coverage {coverage:.1f}% is below minimum threshold {minimum_threshold}%"

    @pytest.mark.requirement("006-FR-006")
    def test_storage_catalog_requirements_covered(self) -> None:
        """Verify storage-catalog requirements have test coverage."""
        spec_path = PROJECT_ROOT / "specs" / "006-integration-testing" / "spec.md"
        test_dirs = [
            PROJECT_ROOT / "packages" / "floe-polaris" / "tests" / "integration",
            PROJECT_ROOT / "packages" / "floe-iceberg" / "tests" / "integration",
        ]
        existing_test_dirs = [d for d in test_dirs if d.exists()]

        if not spec_path.exists() or not existing_test_dirs:
            pytest.skip("Required files not found")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_path],
            test_dirs=existing_test_dirs,
        )

        # Check specific storage-catalog requirements are covered
        storage_requirements = ["FR-012", "FR-013", "FR-014"]
        for req_id in storage_requirements:
            mapping = next(
                (m for m in matrix.mappings if m.requirement_id == req_id),
                None,
            )
            assert mapping is not None, f"Requirement {req_id} not found in mappings"
            assert (
                mapping.coverage_status == CoverageStatus.COVERED
            ), f"Requirement {req_id} is not covered"
            assert len(mapping.test_ids) > 0, f"Requirement {req_id} has no linked tests"
