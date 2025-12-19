"""Tests for testing.traceability.reporter module.

These tests verify the generate_matrix function that orchestrates
requirement parsing, test scanning, and mapping to create a complete
TraceabilityMatrix.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from testing.traceability.models import (
    CoverageStatus,
    TraceabilityMatrix,
)


class TestGenerateMatrix:
    """Tests for generate_matrix function."""

    def test_generate_matrix_can_be_imported(self) -> None:
        """Verify generate_matrix function can be imported."""
        from testing.traceability.reporter import generate_matrix

        assert generate_matrix is not None
        assert callable(generate_matrix)

    def test_generate_matrix_with_no_files(self, tmp_path: Path) -> None:
        """Generate matrix with empty inputs."""
        from testing.traceability.reporter import generate_matrix

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[],
        )

        assert matrix.feature_id == "006"
        assert matrix.feature_name == "Integration Testing"
        assert matrix.requirements == []
        assert matrix.tests == []
        assert matrix.mappings == []
        assert matrix.get_coverage_percentage() == 100.0  # Empty = 100%

    def test_generate_matrix_with_uncovered_requirements(self, tmp_path: Path) -> None:
        """Generate matrix with requirements but no tests."""
        from testing.traceability.reporter import generate_matrix

        # Create spec file with requirements
        spec_content = dedent(
            """
            # Feature Spec

            ## Requirements

            #### Test Traceability

            - **FR-001**: System MUST provide traceability
            - **FR-002**: System MUST generate reports
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        # Create empty test directory
        test_dir = tmp_path / "tests"
        test_dir.mkdir()

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[test_dir],
        )

        assert len(matrix.requirements) == 2
        assert len(matrix.tests) == 0
        assert len(matrix.mappings) == 2
        assert matrix.get_coverage_percentage() == 0.0

    def test_generate_matrix_with_covered_requirements(self, tmp_path: Path) -> None:
        """Generate matrix with matching requirements and tests."""
        from testing.traceability.reporter import generate_matrix

        # Create spec file
        spec_content = dedent(
            """
            #### Test Traceability

            - **FR-001**: System MUST provide traceability
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        # Create test file
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("FR-001")
            def test_traceability():
                pass
        """
        )
        (test_dir / "test_trace.py").write_text(test_content)

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[test_dir],
        )

        assert len(matrix.requirements) == 1
        assert len(matrix.tests) == 1
        assert len(matrix.mappings) == 1
        assert matrix.mappings[0].coverage_status == CoverageStatus.COVERED
        assert matrix.get_coverage_percentage() == 100.0

    def test_generate_matrix_mixed_coverage(self, tmp_path: Path) -> None:
        """Generate matrix with partially covered requirements."""
        from testing.traceability.reporter import generate_matrix

        # Create spec file with 2 requirements
        spec_content = dedent(
            """
            #### Test Execution

            - **FR-001**: First requirement (covered)
            - **FR-002**: Second requirement (uncovered)
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        # Create test file that only covers FR-001
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("FR-001")
            def test_first():
                pass
        """
        )
        (test_dir / "test_partial.py").write_text(test_content)

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[test_dir],
        )

        assert len(matrix.requirements) == 2
        assert len(matrix.tests) == 1
        assert len(matrix.mappings) == 2
        assert matrix.get_coverage_percentage() == 50.0

        # Check specific mappings
        fr_001 = next(m for m in matrix.mappings if m.requirement_id == "FR-001")
        fr_002 = next(m for m in matrix.mappings if m.requirement_id == "FR-002")
        assert fr_001.coverage_status == CoverageStatus.COVERED
        assert fr_002.coverage_status == CoverageStatus.UNCOVERED

    def test_generate_matrix_multiple_spec_files(self, tmp_path: Path) -> None:
        """Generate matrix from multiple spec files."""
        from testing.traceability.reporter import generate_matrix

        # Create two spec files
        spec1 = tmp_path / "spec1.md"
        spec1.write_text("- **FR-001**: First spec requirement")

        spec2 = tmp_path / "spec2.md"
        spec2.write_text("- **FR-002**: Second spec requirement")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec1, spec2],
            test_dirs=[],
        )

        assert len(matrix.requirements) == 2
        assert {r.id for r in matrix.requirements} == {"FR-001", "FR-002"}
        assert len(matrix.spec_files) == 2

    def test_generate_matrix_multiple_test_dirs(self, tmp_path: Path) -> None:
        """Generate matrix from multiple test directories."""
        from testing.traceability.reporter import generate_matrix

        # Create spec
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Requirement")

        # Create two test directories
        test_dir1 = tmp_path / "tests1"
        test_dir1.mkdir()
        test_content1 = dedent(
            """
            import pytest

            @pytest.mark.requirement("FR-001")
            def test_from_dir1():
                pass
        """
        )
        (test_dir1 / "test_a.py").write_text(test_content1)

        test_dir2 = tmp_path / "tests2"
        test_dir2.mkdir()
        test_content2 = dedent(
            """
            import pytest

            @pytest.mark.requirement("FR-001")
            def test_from_dir2():
                pass
        """
        )
        (test_dir2 / "test_b.py").write_text(test_content2)

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[test_dir1, test_dir2],
        )

        assert len(matrix.tests) == 2
        assert len(matrix.mappings[0].test_ids) == 2


class TestGenerateMatrixMetadata:
    """Tests for matrix metadata."""

    def test_matrix_has_generated_at_timestamp(self, tmp_path: Path) -> None:
        """Matrix includes generation timestamp."""
        from testing.traceability.reporter import generate_matrix

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[],
        )

        assert matrix.generated_at is not None

    def test_matrix_stores_spec_file_paths(self, tmp_path: Path) -> None:
        """Matrix stores paths of analyzed spec files."""
        from testing.traceability.reporter import generate_matrix

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Test")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[],
        )

        assert len(matrix.spec_files) == 1
        assert str(spec_file) in matrix.spec_files


class TestGenerateMatrixGaps:
    """Tests for gap detection in matrix."""

    def test_get_gaps_returns_uncovered(self, tmp_path: Path) -> None:
        """get_gaps returns requirements without coverage."""
        from testing.traceability.reporter import generate_matrix

        spec_content = dedent(
            """
            - **FR-001**: Covered requirement
            - **FR-002**: Uncovered requirement
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("FR-001")
            def test_covered():
                pass
        """
        )
        (test_dir / "test_example.py").write_text(test_content)

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[test_dir],
        )

        gaps = matrix.get_gaps()
        assert len(gaps) == 1
        assert gaps[0].id == "FR-002"


class TestReturnType:
    """Tests for return type verification."""

    def test_returns_traceability_matrix(self, tmp_path: Path) -> None:
        """Returned object is TraceabilityMatrix instance."""
        from testing.traceability.reporter import generate_matrix

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[],
        )

        assert isinstance(matrix, TraceabilityMatrix)
