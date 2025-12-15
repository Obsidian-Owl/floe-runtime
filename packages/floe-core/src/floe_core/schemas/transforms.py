"""Transform configuration models for floe-runtime.

T022: [US1] Implement TransformConfig with type discriminator

This module defines TransformConfig for specifying transformation
steps in the pipeline.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransformConfig(BaseModel):
    """Configuration for a transformation step.

    Currently supports 'dbt' type. Future versions will add
    'python' and 'flink' via discriminated unions.

    Attributes:
        type: Transform type discriminator. Currently only 'dbt' supported.
        path: Path to transform source (relative to floe.yaml).
        target: Optional target override for dbt.

    Example:
        >>> config = TransformConfig(type="dbt", path="./dbt", target="prod")
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["dbt"] = Field(
        ...,
        description="Transform type (currently only 'dbt' supported)",
    )
    path: str = Field(
        ...,
        description="Path to transform source relative to floe.yaml",
    )
    target: str | None = Field(
        default=None,
        description="Optional target override",
    )
