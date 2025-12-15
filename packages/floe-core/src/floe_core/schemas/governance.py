"""Governance configuration models for floe-runtime.

T026: [US1] Implement GovernanceConfig with classification_source
T027: [US1] Implement ColumnClassification model

This module defines configuration models for data governance.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ColumnClassification(BaseModel):
    """Classification metadata for a single column.

    Used to track PII and sensitivity levels extracted from
    dbt model meta tags.

    Attributes:
        classification: Classification type (e.g., "pii", "confidential").
        pii_type: Specific PII type (e.g., "email", "phone").
        sensitivity: Sensitivity level (low, medium, high).

    Example:
        >>> classification = ColumnClassification(
        ...     classification="pii",
        ...     pii_type="email",
        ...     sensitivity="high"
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    classification: str
    pii_type: str | None = None
    sensitivity: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Sensitivity level",
    )


class GovernanceConfig(BaseModel):
    """Configuration for data governance.

    Attributes:
        classification_source: Source for column classifications.
            'dbt_meta' extracts from dbt model meta tags.
            'external' uses external classification service.
        policies: Policy definitions (masking rules, etc.)
        emit_lineage: Emit OpenLineage events for governance tracking.

    Example:
        >>> config = GovernanceConfig(
        ...     classification_source="dbt_meta",
        ...     emit_lineage=True
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    classification_source: Literal["dbt_meta", "external"] = Field(
        default="dbt_meta",
        description="Source for column classifications",
    )
    policies: dict[str, Any] = Field(
        default_factory=dict,
        description="Policy definitions",
    )
    emit_lineage: bool = Field(
        default=True,
        description="Emit OpenLineage events",
    )
