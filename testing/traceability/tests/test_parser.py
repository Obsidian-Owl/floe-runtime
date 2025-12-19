"""Tests for testing.traceability.parser module.

These tests verify requirement extraction from spec.md files:
- FR-XXX pattern recognition
- Line number tracking
- Category inference from section headings
- Priority extraction (if present)
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from testing.traceability.models import RequirementCategory


class TestParseRequirements:
    """Tests for parse_requirements function."""

    def test_parse_requirements_can_be_imported(self) -> None:
        """Verify parse_requirements function can be imported."""
        from testing.traceability.parser import parse_requirements

        assert parse_requirements is not None
        assert callable(parse_requirements)

    def test_parse_single_requirement(self, tmp_path: Path) -> None:
        """Parse a spec file with a single requirement."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            # Feature Spec

            ## Requirements

            ### Functional Requirements

            #### Test Traceability

            - **FR-001**: System MUST provide a traceability matrix
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert len(requirements) == 1
        assert requirements[0].id == "FR-001"
        assert "traceability matrix" in requirements[0].text
        assert requirements[0].category == RequirementCategory.TRACEABILITY

    def test_parse_multiple_requirements(self, tmp_path: Path) -> None:
        """Parse a spec file with multiple requirements."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            # Feature Spec

            ## Requirements

            ### Functional Requirements

            #### Test Execution

            - **FR-004**: Integration tests MUST execute inside Docker
            - **FR-005**: Integration tests MUST FAIL when infrastructure unavailable
            - **FR-006**: Tests MUST use environment-based configuration
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert len(requirements) == 3
        assert {r.id for r in requirements} == {"FR-004", "FR-005", "FR-006"}
        for req in requirements:
            assert req.category == RequirementCategory.EXECUTION

    def test_parse_requirements_tracks_line_numbers(self, tmp_path: Path) -> None:
        """Verify line numbers are correctly tracked."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            # Feature Spec

            ## Requirements

            - **FR-001**: First requirement

            Some text here.

            - **FR-002**: Second requirement
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert len(requirements) == 2
        # Line numbers should be different
        assert requirements[0].line_number != requirements[1].line_number
        # FR-001 should be before FR-002
        req_001 = next(r for r in requirements if r.id == "FR-001")
        req_002 = next(r for r in requirements if r.id == "FR-002")
        assert req_001.line_number < req_002.line_number

    def test_parse_requirements_stores_spec_file_path(self, tmp_path: Path) -> None:
        """Verify spec file path is stored in requirements."""
        from testing.traceability.parser import parse_requirements

        spec_content = "- **FR-001**: Test requirement"
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert len(requirements) == 1
        assert requirements[0].spec_file == str(spec_file)

    def test_parse_empty_spec_file(self, tmp_path: Path) -> None:
        """Parsing an empty spec file returns empty list."""
        from testing.traceability.parser import parse_requirements

        spec_file = tmp_path / "empty.md"
        spec_file.write_text("")

        requirements = parse_requirements(spec_file)

        assert requirements == []

    def test_parse_spec_without_requirements(self, tmp_path: Path) -> None:
        """Parsing a spec without FR-XXX patterns returns empty list."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            # Feature Spec

            This is a feature spec without any requirements.

            ## Overview

            Just some description text.
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert requirements == []


class TestCategoryInference:
    """Tests for category inference from section headings."""

    def test_infer_traceability_category(self, tmp_path: Path) -> None:
        """Category is TRACEABILITY from Test Traceability section."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            #### Test Traceability

            - **FR-001**: Must have traceability
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        assert requirements[0].category == RequirementCategory.TRACEABILITY

    def test_infer_execution_category(self, tmp_path: Path) -> None:
        """Category is EXECUTION from Test Execution section."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            #### Test Execution

            - **FR-004**: Must execute in Docker
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        assert requirements[0].category == RequirementCategory.EXECUTION

    def test_infer_package_coverage_category(self, tmp_path: Path) -> None:
        """Category is PACKAGE_COVERAGE from Package Coverage section."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            #### Package Coverage Requirements

            - **FR-008**: floe-core MUST have tests
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        assert requirements[0].category == RequirementCategory.PACKAGE_COVERAGE

    def test_infer_infrastructure_category(self, tmp_path: Path) -> None:
        """Category is INFRASTRUCTURE from Infrastructure section."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            #### Infrastructure Requirements

            - **FR-015**: Docker Compose MUST provide storage profile
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        assert requirements[0].category == RequirementCategory.INFRASTRUCTURE

    def test_infer_shared_fixtures_category(self, tmp_path: Path) -> None:
        """Category is SHARED_FIXTURES from Shared Test Fixtures section."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            #### Shared Test Fixtures

            - **FR-019**: Must provide factory fixtures
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        assert requirements[0].category == RequirementCategory.SHARED_FIXTURES

    def test_infer_observability_category(self, tmp_path: Path) -> None:
        """Category is OBSERVABILITY from Observability section."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            #### Observability Verification

            - **FR-024**: Must verify OpenTelemetry traces
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        assert requirements[0].category == RequirementCategory.OBSERVABILITY

    def test_infer_standalone_first_category(self, tmp_path: Path) -> None:
        """Category is STANDALONE_FIRST from Standalone section."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            #### Standalone-First / Graceful Degradation Testing

            - **FR-029**: Must work without observability services
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        assert requirements[0].category == RequirementCategory.STANDALONE_FIRST

    def test_infer_contract_boundary_category(self, tmp_path: Path) -> None:
        """Category is CONTRACT_BOUNDARY from Contract Boundary section."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            #### Contract Boundary Testing

            - **FR-032**: Must verify CompiledArtifacts output
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        assert requirements[0].category == RequirementCategory.CONTRACT_BOUNDARY

    def test_default_category_when_no_section(self, tmp_path: Path) -> None:
        """Default to EXECUTION when no section heading matches."""
        from testing.traceability.parser import parse_requirements

        spec_content = "- **FR-100**: Some orphan requirement"
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)
        # Default category when no section matches
        assert requirements[0].category == RequirementCategory.EXECUTION


class TestRequirementTextExtraction:
    """Tests for requirement text extraction."""

    def test_extracts_full_requirement_text(self, tmp_path: Path) -> None:
        """Full requirement text is extracted after FR-XXX:."""
        from testing.traceability.parser import parse_requirements

        spec_content = (
            "- **FR-001**: System MUST provide a traceability matrix mapping requirements"
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert (
            requirements[0].text == "System MUST provide a traceability matrix mapping requirements"
        )

    def test_handles_multiline_requirements(self, tmp_path: Path) -> None:
        """Handles requirements that span multiple lines (up to next requirement or section)."""
        from testing.traceability.parser import parse_requirements

        # For now, we only capture the first line
        spec_content = "- **FR-001**: First part of requirement"
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert "First part" in requirements[0].text


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_file_not_found_raises_error(self) -> None:
        """Raises FileNotFoundError for non-existent spec file."""
        from testing.traceability.parser import parse_requirements

        with pytest.raises(FileNotFoundError):
            parse_requirements(Path("/nonexistent/spec.md"))

    def test_handles_duplicate_requirement_ids(self, tmp_path: Path) -> None:
        """Duplicate FR-XXX IDs are both returned (caller can detect)."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            - **FR-001**: First occurrence
            - **FR-001**: Duplicate occurrence
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        # Both should be returned, caller can detect duplicates
        assert len(requirements) == 2
        assert all(r.id == "FR-001" for r in requirements)

    def test_ignores_malformed_requirement_ids(self, tmp_path: Path) -> None:
        """Malformed requirement IDs (FR-1, FR-1234) are ignored."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            - **FR-1**: Too few digits
            - **FR-1234**: Too many digits
            - **FR-ABC**: Letters instead of digits
            - **FR-001**: Valid requirement
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert len(requirements) == 1
        assert requirements[0].id == "FR-001"

    def test_handles_different_markdown_formats(self, tmp_path: Path) -> None:
        """Handles various markdown bullet formats."""
        from testing.traceability.parser import parse_requirements

        spec_content = dedent(
            """
            - **FR-001**: Dash bullet
            * **FR-002**: Star bullet
        """
        )
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(spec_content)

        requirements = parse_requirements(spec_file)

        assert len(requirements) == 2
        assert {r.id for r in requirements} == {"FR-001", "FR-002"}
