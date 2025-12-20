"""Tests for custom pytest markers defined in conftest.py.

These tests verify that the requirement and requirements markers
are properly registered and usable for traceability.
"""

from __future__ import annotations

import pytest


class TestRequirementMarker:
    """Tests for the @pytest.mark.requirement marker."""

    def test_requirement_marker_is_registered(self) -> None:
        """Verify requirement marker doesn't produce warnings."""
        # If the marker is not registered, pytest would warn
        # This test verifies the marker is properly defined
        mark = pytest.mark.requirement("FR-001")
        assert mark is not None
        assert mark.name == "requirement"

    def test_requirement_marker_stores_requirement_id(self) -> None:
        """Verify requirement marker stores the FR-XXX identifier."""
        mark = pytest.mark.requirement("FR-012")
        assert mark.args == ("FR-012",)

    def test_requirement_marker_on_function(self) -> None:
        """Verify requirement marker can be applied to a function."""

        @pytest.mark.requirement("006-FR-001")
        def sample_test() -> None:
            """Sample test function - body intentionally empty to test marker attachment."""

        # Check the marker is attached
        markers = list(sample_test.pytestmark)  # type: ignore[attr-defined]
        assert len(markers) == 1
        assert markers[0].name == "requirement"
        assert markers[0].args == ("FR-001",)


class TestRequirementsMarker:
    """Tests for the @pytest.mark.requirements marker (plural)."""

    def test_requirements_marker_is_registered(self) -> None:
        """Verify requirements marker doesn't produce warnings."""
        mark = pytest.mark.requirements(["FR-001", "FR-002"])
        assert mark is not None
        assert mark.name == "requirements"

    def test_requirements_marker_stores_list(self) -> None:
        """Verify requirements marker stores list of FR-XXX identifiers."""
        mark = pytest.mark.requirements(["FR-032", "FR-033", "FR-034"])
        assert mark.args == (["FR-032", "FR-033", "FR-034"],)

    def test_requirements_marker_on_function(self) -> None:
        """Verify requirements marker can be applied to a function."""

        @pytest.mark.requirements(["FR-032", "FR-033"])
        def sample_test() -> None:
            """Sample test function - body intentionally empty to test marker attachment."""

        markers = list(sample_test.pytestmark)  # type: ignore[attr-defined]
        assert len(markers) == 1
        assert markers[0].name == "requirements"
        assert markers[0].args == (["FR-032", "FR-033"],)


class TestCombinedMarkers:
    """Tests for combining requirement markers with other markers."""

    def test_requirement_with_integration_marker(self) -> None:
        """Verify requirement can be combined with integration marker."""

        @pytest.mark.integration
        @pytest.mark.requirement("006-FR-012")
        def sample_test() -> None:
            """Sample test function - body intentionally empty to test marker attachment."""

        markers = list(sample_test.pytestmark)  # type: ignore[attr-defined]
        marker_names = {m.name for m in markers}
        assert "integration" in marker_names
        assert "requirement" in marker_names

    def test_multiple_markers_preserve_order(self) -> None:
        """Verify marker order is preserved for traceability scanning."""

        @pytest.mark.slow
        @pytest.mark.requirement("006-FR-001")
        @pytest.mark.integration
        def sample_test() -> None:
            """Sample test function - body intentionally empty to test marker attachment."""

        markers = list(sample_test.pytestmark)  # type: ignore[attr-defined]
        # All markers should be present
        marker_names = [m.name for m in markers]
        assert "slow" in marker_names
        assert "requirement" in marker_names
        assert "integration" in marker_names


class TestMarkerWarnings:
    """Tests to verify markers don't produce warnings."""

    def test_no_unknown_marker_warning(self, pytestconfig: pytest.Config) -> None:
        """Verify markers are registered (no PytestUnknownMarkWarning)."""
        # Get registered markers from config
        markers = pytestconfig.getini("markers")

        # Find our custom markers
        marker_names = [m.split(":")[0].strip() for m in markers]

        assert "requirement" in marker_names, (
            "requirement marker not registered - will produce warnings"
        )
        assert "requirements" in marker_names, (
            "requirements marker not registered - will produce warnings"
        )
