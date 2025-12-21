"""Tests for testing.traceability.scanner module.

These tests verify test discovery and requirement marker extraction:
- Test file discovery from directories
- @pytest.mark.requirement("FR-XXX") extraction
- @pytest.mark.requirements(["FR-XXX", "FR-YYY"]) extraction
- Package inference from file path
- Class context preservation

Covers:
- FR-001: Traceability matrix mapping (scanner finds requirement markers)
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

# Import models with underscore prefix to avoid pytest collection conflicts
from testing.traceability.models import Test as _Test
from testing.traceability.models import TestMarker as _TestMarker


class TestScanTests:
    """Tests for scan_tests function."""

    def test_scan_tests_can_be_imported(self) -> None:
        """Verify scan_tests function can be imported."""
        from testing.traceability.scanner import scan_tests

        assert scan_tests is not None
        assert callable(scan_tests)

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        """Scanning empty directory returns empty list."""
        from testing.traceability.scanner import scan_tests

        tests = scan_tests([tmp_path])

        assert tests == []

    def test_scan_directory_without_tests(self, tmp_path: Path) -> None:
        """Scanning directory without test files returns empty list."""
        from testing.traceability.scanner import scan_tests

        # Create non-test file
        (tmp_path / "utils.py").write_text("def helper(): pass")

        tests = scan_tests([tmp_path])

        assert tests == []

    def test_scan_test_without_requirement_marker(self, tmp_path: Path) -> None:
        """Test without requirement marker is not included."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            def test_something():
                assert True
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert tests == []

    @pytest.mark.requirement("006-FR-001")
    def test_scan_single_requirement_marker(self, tmp_path: Path) -> None:
        """Test with @pytest.mark.requirement is discovered.

        Covers: FR-001 (traceability matrix requirement marker detection)
        """
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-001")
            def test_traceability():
                assert True
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert tests[0].function_name == "test_traceability"
        assert tests[0].requirement_ids == ["FR-001"]

    def test_scan_multiple_requirements_marker(self, tmp_path: Path) -> None:
        """Test with @pytest.mark.requirements (plural) is discovered."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirements(["FR-032", "FR-033"])
            def test_contract_boundary():
                assert True
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert tests[0].function_name == "test_contract_boundary"
        assert tests[0].requirement_ids == ["FR-032", "FR-033"]

    def test_scan_test_in_class(self, tmp_path: Path) -> None:
        """Test in class preserves class name."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            class TestPolarisCatalog:
                @pytest.mark.requirement("006-FR-012")
                def test_create_namespace(self):
                    assert True
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert tests[0].function_name == "test_create_namespace"
        assert tests[0].class_name == "TestPolarisCatalog"
        assert tests[0].requirement_ids == ["FR-012"]


class TestPackageInference:
    """Tests for package inference from file path."""

    def test_infer_package_from_packages_directory(self, tmp_path: Path) -> None:
        """Package is inferred from packages/*/tests/ path."""
        from testing.traceability.scanner import scan_tests

        # Simulate packages/floe-polaris/tests/integration/test_catalog.py
        test_dir = tmp_path / "packages" / "floe-polaris" / "tests" / "integration"
        test_dir.mkdir(parents=True)

        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-012")
            def test_catalog():
                assert True
        """
        )
        (test_dir / "test_catalog.py").write_text(test_content)

        tests = scan_tests([test_dir])

        assert len(tests) == 1
        assert tests[0].package == "floe-polaris"

    def test_infer_package_unknown(self, tmp_path: Path) -> None:
        """Package is 'unknown' when not in packages directory."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-001")
            def test_something():
                assert True
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert tests[0].package == "unknown"


class TestMarkerExtraction:
    """Tests for extracting additional markers."""

    def test_extract_integration_marker(self, tmp_path: Path) -> None:
        """Integration marker is extracted."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            @pytest.mark.integration
            @pytest.mark.requirement("006-FR-012")
            def test_polaris_connection():
                assert True
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert _TestMarker.INTEGRATION in tests[0].markers

    def test_extract_multiple_markers(self, tmp_path: Path) -> None:
        """Multiple markers are extracted."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            @pytest.mark.integration
            @pytest.mark.slow
            @pytest.mark.requirement("006-FR-005")
            def test_slow_integration():
                assert True
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert _TestMarker.INTEGRATION in tests[0].markers
        assert _TestMarker.SLOW in tests[0].markers


class TestMultipleFiles:
    """Tests for scanning multiple files and directories."""

    def test_scan_multiple_files(self, tmp_path: Path) -> None:
        """Multiple test files are scanned."""
        from testing.traceability.scanner import scan_tests

        test1 = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-001")
            def test_first():
                pass
        """
        )
        test2 = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-002")
            def test_second():
                pass
        """
        )
        (tmp_path / "test_first.py").write_text(test1)
        (tmp_path / "test_second.py").write_text(test2)

        tests = scan_tests([tmp_path])

        assert len(tests) == 2
        req_ids = {t.requirement_ids[0] for t in tests}
        assert req_ids == {"FR-001", "FR-002"}

    def test_scan_multiple_directories(self, tmp_path: Path) -> None:
        """Multiple directories can be scanned."""
        from testing.traceability.scanner import scan_tests

        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        test1 = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-001")
            def test_from_dir1():
                pass
        """
        )
        test2 = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-002")
            def test_from_dir2():
                pass
        """
        )
        (dir1 / "test_a.py").write_text(test1)
        (dir2 / "test_b.py").write_text(test2)

        tests = scan_tests([dir1, dir2])

        assert len(tests) == 2

    def test_scan_nested_directories(self, tmp_path: Path) -> None:
        """Nested directories are recursively scanned."""
        from testing.traceability.scanner import scan_tests

        nested = tmp_path / "subdir" / "deeper"
        nested.mkdir(parents=True)

        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-010")
            def test_nested():
                pass
        """
        )
        (nested / "test_nested.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert tests[0].function_name == "test_nested"


class TestFilePath:
    """Tests for file path handling."""

    def test_file_path_is_stored(self, tmp_path: Path) -> None:
        """File path is stored in test object."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-001")
            def test_example():
                pass
        """
        )
        test_file = tmp_path / "test_example.py"
        test_file.write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert tests[0].file_path == str(test_file)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_nonexistent_directory_ignored(self, tmp_path: Path) -> None:
        """Non-existent directories are silently ignored."""
        from testing.traceability.scanner import scan_tests

        nonexistent = tmp_path / "does_not_exist"

        tests = scan_tests([nonexistent])

        assert tests == []

    def test_malformed_marker_ignored(self, tmp_path: Path) -> None:
        """Malformed requirement markers are ignored."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement()  # Missing argument
            def test_missing_arg():
                pass

            @pytest.mark.requirement("006-FR-001")
            def test_valid():
                pass
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        # Only valid test should be discovered
        assert len(tests) == 1
        assert tests[0].function_name == "test_valid"

    def test_invalid_python_file_skipped(self, tmp_path: Path) -> None:
        """Files with syntax errors are skipped with warning."""
        from testing.traceability.scanner import scan_tests

        # Create a file with syntax error
        (tmp_path / "test_syntax_error.py").write_text("def broken(")

        # Create a valid file
        valid_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-001")
            def test_valid():
                pass
        """
        )
        (tmp_path / "test_valid.py").write_text(valid_content)

        # Should not raise, should skip invalid file
        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert tests[0].function_name == "test_valid"

    def test_returns_test_objects(self, tmp_path: Path) -> None:
        """Returned objects are Test model instances."""
        from testing.traceability.scanner import scan_tests

        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-001")
            def test_example():
                pass
        """
        )
        (tmp_path / "test_example.py").write_text(test_content)

        tests = scan_tests([tmp_path])

        assert len(tests) == 1
        assert isinstance(tests[0], _Test)
