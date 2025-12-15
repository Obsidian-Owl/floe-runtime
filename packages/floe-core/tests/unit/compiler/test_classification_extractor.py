"""Unit tests for classification extraction from dbt manifest.

T036: [US2] Unit tests for classification extraction from dbt

Tests the extraction of column-level classification metadata from
dbt manifest.json files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


class TestClassificationExtractionBasic:
    """Tests for basic classification extraction."""

    def test_extract_classifications_import(self) -> None:
        """Test extract_column_classifications can be imported."""
        from floe_core.compiler import extract_column_classifications

        assert extract_column_classifications is not None

    def test_extract_classifications_basic(self, tmp_path: Path) -> None:
        """Test basic classification extraction from manifest."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.customers": {
                    "name": "customers",
                    "resource_type": "model",
                    "columns": {
                        "email": {
                            "name": "email",
                            "meta": {
                                "floe": {
                                    "classification": "pii",
                                    "pii_type": "email",
                                    "sensitivity": "high",
                                }
                            },
                        },
                    },
                }
            },
            "sources": {},
        }

        # Create manifest file
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        manifest_path = target_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        # Extract classifications
        classifications = extract_column_classifications(tmp_path)

        assert "customers" in classifications
        assert "email" in classifications["customers"]
        assert classifications["customers"]["email"].classification == "pii"
        assert classifications["customers"]["email"].pii_type == "email"
        assert classifications["customers"]["email"].sensitivity == "high"

    def test_extract_classifications_multiple_columns(self, tmp_path: Path) -> None:
        """Test extraction with multiple classified columns."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.users": {
                    "name": "users",
                    "resource_type": "model",
                    "columns": {
                        "email": {
                            "name": "email",
                            "meta": {
                                "floe": {
                                    "classification": "pii",
                                    "pii_type": "email",
                                    "sensitivity": "high",
                                }
                            },
                        },
                        "phone": {
                            "name": "phone",
                            "meta": {
                                "floe": {
                                    "classification": "pii",
                                    "pii_type": "phone",
                                    "sensitivity": "high",
                                }
                            },
                        },
                        "id": {
                            "name": "id",
                            "meta": {
                                "floe": {
                                    "classification": "identifier",
                                    "sensitivity": "medium",
                                }
                            },
                        },
                    },
                }
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert "users" in classifications
        assert len(classifications["users"]) == 3
        assert classifications["users"]["email"].pii_type == "email"
        assert classifications["users"]["phone"].pii_type == "phone"
        assert classifications["users"]["id"].classification == "identifier"

    def test_extract_classifications_multiple_models(self, tmp_path: Path) -> None:
        """Test extraction from multiple models."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.customers": {
                    "name": "customers",
                    "resource_type": "model",
                    "columns": {
                        "email": {
                            "name": "email",
                            "meta": {"floe": {"classification": "pii"}},
                        },
                    },
                },
                "model.test.orders": {
                    "name": "orders",
                    "resource_type": "model",
                    "columns": {
                        "total": {
                            "name": "total",
                            "meta": {"floe": {"classification": "financial"}},
                        },
                    },
                },
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert "customers" in classifications
        assert "orders" in classifications
        assert classifications["customers"]["email"].classification == "pii"
        assert classifications["orders"]["total"].classification == "financial"


class TestClassificationExtractionDefaults:
    """Tests for default values in classification extraction."""

    def test_extract_default_sensitivity(self, tmp_path: Path) -> None:
        """Test default sensitivity is 'medium' when not specified."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.products": {
                    "name": "products",
                    "resource_type": "model",
                    "columns": {
                        "id": {
                            "name": "id",
                            "meta": {
                                "floe": {
                                    "classification": "identifier",
                                    # sensitivity not specified
                                }
                            },
                        },
                    },
                }
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert classifications["products"]["id"].sensitivity == "medium"

    def test_extract_no_pii_type(self, tmp_path: Path) -> None:
        """Test pii_type is None when not specified."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.data": {
                    "name": "data",
                    "resource_type": "model",
                    "columns": {
                        "status": {
                            "name": "status",
                            "meta": {
                                "floe": {
                                    "classification": "internal",
                                }
                            },
                        },
                    },
                }
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert classifications["data"]["status"].pii_type is None


class TestClassificationExtractionFiltering:
    """Tests for filtering in classification extraction."""

    def test_skip_columns_without_floe_meta(self, tmp_path: Path) -> None:
        """Test columns without floe meta are skipped."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.staging": {
                    "name": "staging",
                    "resource_type": "model",
                    "columns": {
                        "col1": {
                            "name": "col1",
                            "meta": {},  # No floe meta
                        },
                        "col2": {
                            "name": "col2",
                            "meta": {
                                "owner": "analytics",  # Other meta, no floe
                            },
                        },
                        "col3": {
                            "name": "col3",
                            "meta": {
                                "floe": {"classification": "pii"},
                            },
                        },
                    },
                }
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert "staging" in classifications
        assert "col1" not in classifications["staging"]
        assert "col2" not in classifications["staging"]
        assert "col3" in classifications["staging"]

    def test_skip_non_model_nodes(self, tmp_path: Path) -> None:
        """Test non-model nodes are skipped."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.customers": {
                    "name": "customers",
                    "resource_type": "model",
                    "columns": {
                        "email": {
                            "name": "email",
                            "meta": {"floe": {"classification": "pii"}},
                        },
                    },
                },
                "seed.test.reference_data": {
                    "name": "reference_data",
                    "resource_type": "seed",  # Not a model
                    "columns": {
                        "code": {
                            "name": "code",
                            "meta": {"floe": {"classification": "public"}},
                        },
                    },
                },
                "snapshot.test.customers_snapshot": {
                    "name": "customers_snapshot",
                    "resource_type": "snapshot",  # Not a model
                    "columns": {},
                },
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        # Only model should be included
        assert "customers" in classifications
        assert "reference_data" not in classifications
        assert "customers_snapshot" not in classifications

    def test_skip_columns_without_classification(self, tmp_path: Path) -> None:
        """Test columns with floe meta but no classification are skipped."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.data": {
                    "name": "data",
                    "resource_type": "model",
                    "columns": {
                        "col1": {
                            "name": "col1",
                            "meta": {
                                "floe": {
                                    "sensitivity": "high",
                                    # No classification
                                }
                            },
                        },
                        "col2": {
                            "name": "col2",
                            "meta": {
                                "floe": {
                                    "classification": "pii",
                                }
                            },
                        },
                    },
                }
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert "col1" not in classifications["data"]
        assert "col2" in classifications["data"]


class TestClassificationExtractionErrorHandling:
    """Tests for error handling in classification extraction."""

    def test_missing_manifest_returns_empty(self, tmp_path: Path) -> None:
        """Test missing manifest returns empty dict (graceful degradation)."""
        from floe_core.compiler import extract_column_classifications

        # No target/manifest.json created
        classifications = extract_column_classifications(tmp_path, strict=False)

        assert classifications == {}

    def test_missing_manifest_strict_raises(self, tmp_path: Path) -> None:
        """Test missing manifest raises error in strict mode."""
        from floe_core.compiler import extract_column_classifications

        with pytest.raises(FileNotFoundError):
            extract_column_classifications(tmp_path, strict=True)

    def test_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        """Test invalid JSON returns empty dict (graceful degradation)."""
        from floe_core.compiler import extract_column_classifications

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text("{invalid json")

        classifications = extract_column_classifications(tmp_path, strict=False)

        assert classifications == {}

    def test_invalid_json_strict_raises(self, tmp_path: Path) -> None:
        """Test invalid JSON raises error in strict mode."""
        from floe_core.compiler import extract_column_classifications

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text("{invalid json")

        with pytest.raises((json.JSONDecodeError, ValueError)):
            extract_column_classifications(tmp_path, strict=True)

    def test_empty_manifest_returns_empty(self, tmp_path: Path) -> None:
        """Test empty manifest returns empty dict."""
        from floe_core.compiler import extract_column_classifications

        manifest: dict[str, Any] = {"nodes": {}, "sources": {}}

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert classifications == {}

    def test_models_without_columns(self, tmp_path: Path) -> None:
        """Test models without columns field."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.empty": {
                    "name": "empty",
                    "resource_type": "model",
                    # No columns field
                },
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert classifications == {}


class TestClassificationExtractionValidation:
    """Tests for classification validation."""

    def test_valid_sensitivity_levels(self, tmp_path: Path) -> None:
        """Test valid sensitivity levels are accepted."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.data": {
                    "name": "data",
                    "resource_type": "model",
                    "columns": {
                        "col_low": {
                            "name": "col_low",
                            "meta": {
                                "floe": {
                                    "classification": "public",
                                    "sensitivity": "low",
                                }
                            },
                        },
                        "col_medium": {
                            "name": "col_medium",
                            "meta": {
                                "floe": {
                                    "classification": "internal",
                                    "sensitivity": "medium",
                                }
                            },
                        },
                        "col_high": {
                            "name": "col_high",
                            "meta": {
                                "floe": {
                                    "classification": "pii",
                                    "sensitivity": "high",
                                }
                            },
                        },
                    },
                }
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert classifications["data"]["col_low"].sensitivity == "low"
        assert classifications["data"]["col_medium"].sensitivity == "medium"
        assert classifications["data"]["col_high"].sensitivity == "high"

    def test_custom_classification_types(self, tmp_path: Path) -> None:
        """Test custom classification types are allowed."""
        from floe_core.compiler import extract_column_classifications

        manifest = {
            "nodes": {
                "model.test.data": {
                    "name": "data",
                    "resource_type": "model",
                    "columns": {
                        "col": {
                            "name": "col",
                            "meta": {
                                "floe": {
                                    "classification": "custom_classification_type",
                                    "sensitivity": "medium",
                                }
                            },
                        },
                    },
                }
            },
            "sources": {},
        }

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        classifications = extract_column_classifications(tmp_path)

        assert classifications["data"]["col"].classification == "custom_classification_type"
