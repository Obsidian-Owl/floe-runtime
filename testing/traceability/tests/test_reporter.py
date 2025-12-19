"""Tests for testing.traceability.reporter module.

These tests verify the generate_matrix function that orchestrates
requirement parsing, test scanning, and mapping to create a complete
TraceabilityMatrix.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

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
        assert matrix.get_coverage_percentage() == pytest.approx(100.0)  # Empty = 100%

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
        assert matrix.get_coverage_percentage() == pytest.approx(0.0)

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
        assert matrix.get_coverage_percentage() == pytest.approx(100.0)

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
        assert matrix.get_coverage_percentage() == pytest.approx(50.0)

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


class TestFormatConsoleReport:
    """Tests for format_console_report function."""

    def test_format_console_report_can_be_imported(self) -> None:
        """Verify format_console_report function can be imported."""
        from testing.traceability.reporter import format_console_report

        assert format_console_report is not None
        assert callable(format_console_report)

    def test_format_console_report_returns_string(self, tmp_path: Path) -> None:
        """format_console_report returns a string."""
        from testing.traceability.reporter import format_console_report, generate_matrix

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[],
        )

        output = format_console_report(matrix)

        assert isinstance(output, str)

    def test_format_console_report_includes_feature_info(self, tmp_path: Path) -> None:
        """Report includes feature ID and name."""
        from testing.traceability.reporter import format_console_report, generate_matrix

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[],
        )

        output = format_console_report(matrix)

        assert "006" in output
        assert "Integration Testing" in output

    def test_format_console_report_includes_coverage_percentage(self, tmp_path: Path) -> None:
        """Report includes coverage percentage."""
        from testing.traceability.reporter import format_console_report, generate_matrix

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Test requirement")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[],
        )

        output = format_console_report(matrix)

        # Coverage should be 0% since no tests cover the requirement
        assert "0" in output or "0.0" in output

    def test_format_console_report_includes_requirement_count(self, tmp_path: Path) -> None:
        """Report includes total requirement count."""
        from testing.traceability.reporter import format_console_report, generate_matrix

        spec_content = dedent(
            """
            - **FR-001**: First requirement
            - **FR-002**: Second requirement
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[],
        )

        output = format_console_report(matrix)

        # Should mention 2 requirements somewhere
        assert "2" in output

    def test_format_console_report_lists_gaps(self, tmp_path: Path) -> None:
        """Report lists uncovered requirements."""
        from testing.traceability.reporter import format_console_report, generate_matrix

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Uncovered requirement")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[],
        )

        output = format_console_report(matrix)

        assert "FR-001" in output

    def test_format_console_report_shows_covered_requirements(self, tmp_path: Path) -> None:
        """Report shows covered requirements differently from gaps."""
        from testing.traceability.reporter import format_console_report, generate_matrix

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Covered requirement")

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

        output = format_console_report(matrix)

        assert "FR-001" in output
        assert "100" in output  # 100% coverage


class TestFormatJsonReport:
    """Tests for format_json_report function."""

    def test_format_json_report_can_be_imported(self) -> None:
        """Verify format_json_report function can be imported."""
        from testing.traceability.reporter import format_json_report

        assert format_json_report is not None
        assert callable(format_json_report)

    def test_format_json_report_returns_string(self, tmp_path: Path) -> None:
        """format_json_report returns a JSON string."""
        from testing.traceability.reporter import format_json_report, generate_matrix

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[],
        )

        output = format_json_report(matrix)

        assert isinstance(output, str)

    def test_format_json_report_is_valid_json(self, tmp_path: Path) -> None:
        """format_json_report returns valid JSON."""
        import json

        from testing.traceability.reporter import format_json_report, generate_matrix

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[],
        )

        output = format_json_report(matrix)
        data = json.loads(output)

        assert isinstance(data, dict)

    def test_format_json_report_includes_feature_info(self, tmp_path: Path) -> None:
        """JSON output includes feature ID and name."""
        import json

        from testing.traceability.reporter import format_json_report, generate_matrix

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[],
            test_dirs=[],
        )

        output = format_json_report(matrix)
        data = json.loads(output)

        assert data["feature_id"] == "006"
        assert data["feature_name"] == "Integration Testing"

    def test_format_json_report_includes_coverage_percentage(self, tmp_path: Path) -> None:
        """JSON output includes coverage percentage."""
        import json

        from testing.traceability.reporter import format_json_report, generate_matrix

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Test requirement")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[],
        )

        output = format_json_report(matrix)
        data = json.loads(output)

        assert "coverage_percentage" in data
        assert data["coverage_percentage"] == pytest.approx(0.0)

    def test_format_json_report_includes_requirements(self, tmp_path: Path) -> None:
        """JSON output includes requirements list."""
        import json

        from testing.traceability.reporter import format_json_report, generate_matrix

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: First requirement")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[],
        )

        output = format_json_report(matrix)
        data = json.loads(output)

        assert "requirements" in data
        assert len(data["requirements"]) == 1
        assert data["requirements"][0]["id"] == "FR-001"

    def test_format_json_report_includes_gaps(self, tmp_path: Path) -> None:
        """JSON output includes coverage gaps."""
        import json

        from testing.traceability.reporter import format_json_report, generate_matrix

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Uncovered requirement")

        matrix = generate_matrix(
            feature_id="006",
            feature_name="Integration Testing",
            spec_files=[spec_file],
            test_dirs=[],
        )

        output = format_json_report(matrix)
        data = json.loads(output)

        assert "gaps" in data
        assert len(data["gaps"]) == 1
        assert data["gaps"][0]["id"] == "FR-001"

    def test_format_json_report_includes_mappings(self, tmp_path: Path) -> None:
        """JSON output includes requirement-test mappings."""
        import json

        from testing.traceability.reporter import format_json_report, generate_matrix

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Test requirement")

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

        output = format_json_report(matrix)
        data = json.loads(output)

        assert "mappings" in data
        assert len(data["mappings"]) == 1
        assert data["mappings"][0]["requirement_id"] == "FR-001"
        assert data["mappings"][0]["coverage_status"] == "covered"
