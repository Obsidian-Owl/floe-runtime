"""Unit tests for ColumnClassification facet generation.

T054: [US3] Unit tests for ColumnClassification facet generation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestColumnClassification:
    """Tests for ColumnClassification model."""

    def test_create_minimal_classification(self) -> None:
        """Test creating classification with required fields only."""
        from floe_dagster.lineage.facets import ColumnClassification

        classification = ColumnClassification(
            column_name="email",
            classification="pii",
        )

        assert classification.column_name == "email"
        assert classification.classification == "pii"
        assert classification.pii_type is None
        assert classification.sensitivity == "medium"  # Default

    def test_create_full_classification(self) -> None:
        """Test creating classification with all fields."""
        from floe_dagster.lineage.facets import ColumnClassification

        classification = ColumnClassification(
            column_name="ssn",
            classification="pii",
            pii_type="ssn",
            sensitivity="high",
        )

        assert classification.column_name == "ssn"
        assert classification.classification == "pii"
        assert classification.pii_type == "ssn"
        assert classification.sensitivity == "high"

    def test_classification_types(self) -> None:
        """Test various classification types."""
        from floe_dagster.lineage.facets import ColumnClassification

        # PII
        pii = ColumnClassification(column_name="email", classification="pii")
        assert pii.classification == "pii"

        # Internal
        internal = ColumnClassification(column_name="internal_id", classification="internal")
        assert internal.classification == "internal"

        # Public
        public = ColumnClassification(column_name="product_name", classification="public")
        assert public.classification == "public"

        # Confidential
        confidential = ColumnClassification(column_name="salary", classification="confidential")
        assert confidential.classification == "confidential"

    def test_pii_types(self) -> None:
        """Test various PII types."""
        from floe_dagster.lineage.facets import ColumnClassification

        pii_types = ["email", "phone", "ssn", "name", "address", "dob", "ip_address"]

        for pii_type in pii_types:
            classification = ColumnClassification(
                column_name=f"{pii_type}_column",
                classification="pii",
                pii_type=pii_type,
            )
            assert classification.pii_type == pii_type

    def test_sensitivity_levels(self) -> None:
        """Test sensitivity levels."""
        from floe_dagster.lineage.facets import ColumnClassification

        for level in ["high", "medium", "low"]:
            classification = ColumnClassification(
                column_name="test",
                classification="pii",
                sensitivity=level,
            )
            assert classification.sensitivity == level

    def test_classification_is_frozen(self) -> None:
        """Test ColumnClassification is immutable."""
        from floe_dagster.lineage.facets import ColumnClassification

        classification = ColumnClassification(
            column_name="email",
            classification="pii",
        )

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            classification.classification = "public"  # type: ignore[misc]

    def test_classification_forbids_extra_fields(self) -> None:
        """Test extra fields are rejected."""
        from floe_dagster.lineage.facets import ColumnClassification

        with pytest.raises(ValidationError) as exc_info:
            ColumnClassification(
                column_name="email",
                classification="pii",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_classification_requires_column_name(self) -> None:
        """Test column_name is required."""
        from floe_dagster.lineage.facets import ColumnClassification

        with pytest.raises(ValidationError) as exc_info:
            ColumnClassification(classification="pii")  # type: ignore[call-arg]

        assert "column_name" in str(exc_info.value)

    def test_classification_requires_classification(self) -> None:
        """Test classification is required."""
        from floe_dagster.lineage.facets import ColumnClassification

        with pytest.raises(ValidationError) as exc_info:
            ColumnClassification(column_name="email")  # type: ignore[call-arg]

        assert "classification" in str(exc_info.value)

    def test_to_openlineage_dict(self) -> None:
        """Test conversion to OpenLineage facet format."""
        from floe_dagster.lineage.facets import ColumnClassification

        classification = ColumnClassification(
            column_name="email",
            classification="pii",
            pii_type="email",
            sensitivity="high",
        )

        openlineage_dict = classification.to_openlineage_dict()

        # OpenLineage uses camelCase
        assert openlineage_dict["columnName"] == "email"
        assert openlineage_dict["classification"] == "pii"
        assert openlineage_dict["piiType"] == "email"
        assert openlineage_dict["sensitivity"] == "high"

    def test_to_openlineage_dict_excludes_none_pii_type(self) -> None:
        """Test to_openlineage_dict excludes piiType when None."""
        from floe_dagster.lineage.facets import ColumnClassification

        classification = ColumnClassification(
            column_name="internal_id",
            classification="internal",
        )

        openlineage_dict = classification.to_openlineage_dict()

        assert "piiType" not in openlineage_dict

    def test_from_dbt_column_meta(self) -> None:
        """Test creating classification from dbt column meta.floe namespace."""
        from floe_dagster.lineage.facets import ColumnClassification

        column_meta = {
            "floe": {
                "classification": "pii",
                "pii_type": "email",
                "sensitivity": "high",
            }
        }

        classification = ColumnClassification.from_dbt_meta(
            column_name="email",
            meta=column_meta,
        )

        assert classification.column_name == "email"
        assert classification.classification == "pii"
        assert classification.pii_type == "email"
        assert classification.sensitivity == "high"

    def test_from_dbt_column_meta_partial(self) -> None:
        """Test creating classification with partial meta."""
        from floe_dagster.lineage.facets import ColumnClassification

        column_meta = {
            "floe": {
                "classification": "internal",
                # No pii_type, sensitivity uses default
            }
        }

        classification = ColumnClassification.from_dbt_meta(
            column_name="internal_id",
            meta=column_meta,
        )

        assert classification.classification == "internal"
        assert classification.pii_type is None
        assert classification.sensitivity == "medium"  # Default

    def test_from_dbt_column_meta_returns_none_without_classification(self) -> None:
        """Test returns None when no classification in meta."""
        from floe_dagster.lineage.facets import ColumnClassification

        column_meta: dict[str, object] = {}  # No floe namespace

        classification = ColumnClassification.from_dbt_meta(
            column_name="some_column",
            meta=column_meta,
        )

        assert classification is None

    def test_from_dbt_column_meta_returns_none_for_empty_floe(self) -> None:
        """Test returns None when floe namespace exists but no classification."""
        from floe_dagster.lineage.facets import ColumnClassification

        column_meta = {
            "floe": {
                "owner": "data-team",
                # No classification key
            }
        }

        classification = ColumnClassification.from_dbt_meta(
            column_name="some_column",
            meta=column_meta,
        )

        assert classification is None


class TestColumnClassificationFacetBuilder:
    """Tests for building column classification facets for OpenLineage."""

    def test_build_facet_from_classifications(self) -> None:
        """Test building OpenLineage facet from list of classifications."""
        from floe_dagster.lineage.facets import (
            ColumnClassification,
            build_classification_facet,
        )

        classifications = [
            ColumnClassification(
                column_name="email",
                classification="pii",
                pii_type="email",
                sensitivity="high",
            ),
            ColumnClassification(
                column_name="phone",
                classification="pii",
                pii_type="phone",
                sensitivity="medium",
            ),
        ]

        facet = build_classification_facet(classifications)

        assert "_producer" in facet
        assert "_schemaURL" in facet
        assert facet["_producer"] == "floe-dagster"
        assert "columnClassifications" in facet
        assert len(facet["columnClassifications"]) == 2

    def test_build_facet_empty_list(self) -> None:
        """Test building facet from empty list returns None."""
        from floe_dagster.lineage.facets import build_classification_facet

        facet = build_classification_facet([])

        assert facet is None

    def test_build_facet_includes_schema_url(self) -> None:
        """Test facet includes OpenLineage schema URL."""
        from floe_dagster.lineage.facets import (
            ColumnClassification,
            build_classification_facet,
        )

        classifications = [
            ColumnClassification(
                column_name="email",
                classification="pii",
            )
        ]

        facet = build_classification_facet(classifications)

        assert facet["_schemaURL"].startswith("https://")
        assert "openlineage" in facet["_schemaURL"]
