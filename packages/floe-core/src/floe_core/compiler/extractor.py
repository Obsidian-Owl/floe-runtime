"""Classification extraction from dbt manifest.

T043: [US2] Implement classification extractor from dbt manifest

This module extracts column-level classification metadata from dbt
manifest.json files. Classifications are stored in dbt model meta tags
under the 'floe' namespace.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from floe_core.schemas import ColumnClassification

logger = logging.getLogger(__name__)


def extract_column_classifications(
    dbt_project_path: Path | str,
    strict: bool = False,
) -> dict[str, dict[str, ColumnClassification]]:
    """Extract column-level classifications from dbt manifest.

    Parses dbt manifest.json and extracts classification metadata from column
    meta tags. Only processes model nodes.

    Args:
        dbt_project_path: Path to dbt project root containing target/manifest.json.
        strict: If True, raise on missing/invalid manifest. If False, log warning
            and return empty dict (graceful degradation).

    Returns:
        Dictionary structure:
        {
            "model_name": {
                "column_name": ColumnClassification(
                    classification="pii",
                    pii_type="email",
                    sensitivity="high"
                )
            }
        }

    Raises:
        FileNotFoundError: If manifest not found and strict=True.
        ValueError: If manifest JSON is invalid and strict=True.

    Example:
        >>> classifications = extract_column_classifications(Path("my_dbt_project"))
        >>> classifications["stg_customers"]["email"]
        ColumnClassification(classification='pii', pii_type='email', sensitivity='high')
    """
    dbt_project_path = Path(dbt_project_path)
    manifest_path = dbt_project_path / "target" / "manifest.json"

    # Handle missing manifest gracefully
    if not manifest_path.exists():
        msg = f"dbt manifest not found at {manifest_path}. Run 'dbt parse' or 'dbt compile' first."
        if strict:
            raise FileNotFoundError(msg)
        logger.warning(msg)
        return {}

    # Load manifest
    try:
        manifest = _load_manifest(manifest_path)
    except (json.JSONDecodeError, ValueError) as e:
        msg = f"Invalid manifest.json at {manifest_path}: {e}"
        if strict:
            raise ValueError(msg) from e
        logger.error(msg)
        return {}

    # Extract classifications
    classifications: dict[str, dict[str, ColumnClassification]] = {}

    # Process models
    for _node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue

        model_name = node.get("name", "unknown")
        model_classifications = _extract_node_classifications(node)

        if model_classifications:
            classifications[model_name] = model_classifications

    logger.info(
        "Classification extraction complete",
        extra={
            "models_with_classifications": len(classifications),
            "total_classified_columns": sum(len(cols) for cols in classifications.values()),
        },
    )

    return classifications


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load dbt manifest.json file.

    Attempts to use orjson for performance, falls back to standard json.

    Args:
        manifest_path: Path to manifest.json file.

    Returns:
        Parsed manifest dictionary.

    Raises:
        json.JSONDecodeError: If JSON is invalid.
    """
    try:
        import orjson

        result: dict[str, Any] = orjson.loads(manifest_path.read_bytes())
        return result
    except ImportError:
        loaded: dict[str, Any] = json.loads(manifest_path.read_text())
        return loaded


def _extract_node_classifications(
    node: dict[str, Any],
) -> dict[str, ColumnClassification]:
    """Extract classifications from a single node (model).

    Args:
        node: Node dictionary from manifest.

    Returns:
        Dict of column_name -> ColumnClassification.
    """
    model_classifications: dict[str, ColumnClassification] = {}

    # Iterate over columns in the node
    for column_name, column_info in node.get("columns", {}).items():
        # Extract floe meta tags
        floe_meta = column_info.get("meta", {}).get("floe", {})

        # Only include columns with classification
        if not floe_meta.get("classification"):
            continue

        # Build classification record
        classification = ColumnClassification(
            classification=floe_meta["classification"],
            pii_type=floe_meta.get("pii_type"),
            sensitivity=floe_meta.get("sensitivity", "medium"),
        )

        model_classifications[column_name] = classification

    return model_classifications
