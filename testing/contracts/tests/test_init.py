"""Tests for testing.contracts module initialization.

These tests verify that the contracts module is properly structured
and exports the expected symbols for contract validation.
"""

from __future__ import annotations

from pathlib import Path


class TestContractsModuleImport:
    """Tests for contracts module imports."""

    def test_contracts_module_import(self) -> None:
        """Verify contracts module can be imported."""
        import testing.contracts

        assert testing.contracts is not None

    def test_contracts_module_has_version(self) -> None:
        """Verify contracts module exports __version__."""
        from testing.contracts import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_contracts_module_has_all(self) -> None:
        """Verify contracts module exports __all__."""
        from testing.contracts import __all__

        assert __all__ is not None
        assert isinstance(__all__, list)
        assert "__version__" in __all__


class TestSchemaConstants:
    """Tests for JSON schema path constants."""

    def test_traceability_matrix_schema_path_exists(self) -> None:
        """Verify TRACEABILITY_MATRIX_SCHEMA_PATH is exported and valid."""
        from testing.contracts import TRACEABILITY_MATRIX_SCHEMA_PATH

        assert TRACEABILITY_MATRIX_SCHEMA_PATH is not None
        assert isinstance(TRACEABILITY_MATRIX_SCHEMA_PATH, Path)
        assert TRACEABILITY_MATRIX_SCHEMA_PATH.name == "traceability-matrix.schema.json"

    def test_test_report_schema_path_exists(self) -> None:
        """Verify TEST_REPORT_SCHEMA_PATH is exported and valid."""
        from testing.contracts import TEST_REPORT_SCHEMA_PATH

        assert TEST_REPORT_SCHEMA_PATH is not None
        assert isinstance(TEST_REPORT_SCHEMA_PATH, Path)
        assert TEST_REPORT_SCHEMA_PATH.name == "test-report.schema.json"

    def test_schema_paths_point_to_existing_files(self) -> None:
        """Verify schema path constants point to existing files."""
        from testing.contracts import (
            TEST_REPORT_SCHEMA_PATH,
            TRACEABILITY_MATRIX_SCHEMA_PATH,
        )

        assert (
            TRACEABILITY_MATRIX_SCHEMA_PATH.exists()
        ), f"Schema file not found: {TRACEABILITY_MATRIX_SCHEMA_PATH}"
        assert TEST_REPORT_SCHEMA_PATH.exists(), f"Schema file not found: {TEST_REPORT_SCHEMA_PATH}"


class TestSchemaLoaders:
    """Tests for JSON schema loading utilities."""

    def test_load_traceability_matrix_schema(self) -> None:
        """Verify traceability matrix schema can be loaded."""
        from testing.contracts import load_traceability_matrix_schema

        schema = load_traceability_matrix_schema()

        assert schema is not None
        assert isinstance(schema, dict)
        assert schema.get("title") == "TraceabilityMatrix"
        assert "properties" in schema
        assert "feature_id" in schema["properties"]

    def test_load_test_report_schema(self) -> None:
        """Verify test report schema can be loaded."""
        from testing.contracts import load_test_report_schema

        schema = load_test_report_schema()

        assert schema is not None
        assert isinstance(schema, dict)
        assert schema.get("title") == "TraceabilityReport"
        assert "properties" in schema
        assert "coverage_percentage" in schema["properties"]

    def test_schemas_are_valid_json_schema(self) -> None:
        """Verify loaded schemas are valid JSON Schema draft-07."""
        from testing.contracts import (
            load_test_report_schema,
            load_traceability_matrix_schema,
        )

        matrix_schema = load_traceability_matrix_schema()
        report_schema = load_test_report_schema()

        # Check $schema property indicates JSON Schema draft-07
        expected_schema = "http://json-schema.org/draft-07/schema#"
        assert matrix_schema.get("$schema") == expected_schema
        assert report_schema.get("$schema") == expected_schema


class TestContractsDirectory:
    """Tests for contracts directory constant."""

    def test_contracts_dir_exists(self) -> None:
        """Verify CONTRACTS_DIR constant points to existing directory."""
        from testing.contracts import CONTRACTS_DIR

        assert CONTRACTS_DIR is not None
        assert isinstance(CONTRACTS_DIR, Path)
        assert CONTRACTS_DIR.exists()
        assert CONTRACTS_DIR.is_dir()

    def test_contracts_dir_contains_schemas(self) -> None:
        """Verify contracts directory contains expected schema files."""
        from testing.contracts import CONTRACTS_DIR

        schema_files = list(CONTRACTS_DIR.glob("*.schema.json"))
        assert len(schema_files) >= 2, f"Expected at least 2 schemas, found {len(schema_files)}"
