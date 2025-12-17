"""OpenLineage facet models for column-level classification.

T059: [US3] Create ColumnClassification model
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnClassification(BaseModel):
    """Column-level classification from dbt meta.floe namespace.

    Represents data classification metadata for a single column,
    extracted from dbt model YAML configuration.

    Attributes:
        column_name: Name of the column
        classification: Classification type (pii, internal, public, confidential)
        pii_type: PII type if classification is pii (email, phone, ssn, etc.)
        sensitivity: Sensitivity level (high, medium, low)

    Example:
        >>> classification = ColumnClassification(
        ...     column_name="email",
        ...     classification="pii",
        ...     pii_type="email",
        ...     sensitivity="high",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    column_name: str = Field(description="Name of the column")
    classification: str = Field(
        description="Classification type (pii, internal, public, confidential)",
    )
    pii_type: str | None = Field(
        default=None,
        description="PII type if classification is pii (email, phone, ssn, etc.)",
    )
    sensitivity: str = Field(
        default="medium",
        description="Sensitivity level (high, medium, low)",
    )

    def to_openlineage_dict(self) -> dict[str, Any]:
        """Convert to OpenLineage-compatible dictionary.

        Returns:
            Dictionary with camelCase keys for OpenLineage compatibility.
        """
        result: dict[str, Any] = {
            "columnName": self.column_name,
            "classification": self.classification,
            "sensitivity": self.sensitivity,
        }

        if self.pii_type is not None:
            result["piiType"] = self.pii_type

        return result

    @classmethod
    def from_dbt_meta(cls, column_name: str, meta: dict[str, Any]) -> ColumnClassification | None:
        """Create ColumnClassification from dbt column meta.

        Extracts classification from the meta.floe namespace of a dbt
        column definition.

        Args:
            column_name: Name of the column.
            meta: Column meta dictionary from dbt manifest.

        Returns:
            ColumnClassification if classification found, None otherwise.

        Example:
            >>> meta = {
            ...     "floe": {
            ...         "classification": "pii",
            ...         "pii_type": "email",
            ...         "sensitivity": "high",
            ...     }
            ... }
            >>> ColumnClassification.from_dbt_meta("email", meta)
            ColumnClassification(column_name='email', classification='pii', ...)
        """
        floe_meta = meta.get("floe", {})

        if not floe_meta.get("classification"):
            return None

        return cls(
            column_name=column_name,
            classification=floe_meta["classification"],
            pii_type=floe_meta.get("pii_type"),
            sensitivity=floe_meta.get("sensitivity", "medium"),
        )


def build_classification_facet(
    classifications: list[ColumnClassification],
) -> dict[str, Any] | None:
    """Build OpenLineage column classification facet.

    Creates a custom facet containing column-level classification
    metadata for OpenLineage events.

    Args:
        classifications: List of column classifications.

    Returns:
        OpenLineage facet dictionary, or None if empty.

    Example:
        >>> classifications = [
        ...     ColumnClassification(column_name="email", classification="pii"),
        ... ]
        >>> facet = build_classification_facet(classifications)
        >>> facet["columnClassifications"]
        [{"columnName": "email", "classification": "pii", ...}]
    """
    if not classifications:
        return None

    return {
        "_producer": "floe-dagster",
        "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ColumnLineageDatasetFacet.json",
        "columnClassifications": [c.to_openlineage_dict() for c in classifications],
    }
