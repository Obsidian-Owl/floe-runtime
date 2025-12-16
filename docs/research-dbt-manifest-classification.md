# Research: dbt manifest.json Structure for Column-Level Classification Metadata

**Date**: December 15, 2025
**Status**: Complete
**Context**: floe-core Compiler needs to extract column classifications from dbt models' meta tags when `classification_source` is `"dbt_meta"`.

---

## Executive Summary

The dbt manifest.json provides direct access to column-level metadata through a well-structured hierarchy. Column classifications stored in dbt meta tags are readily available in the compiled manifest without parsing SQL. This enables floe-core to extract classifications reliably using standard JSON parsing.

---

## 1. Manifest Location and Structure

### 1.1 Standard Location

```
dbt_project/
├── dbt_project.yml
├── models/
│   ├── schema.yml          # Column definitions with meta tags (source)
│   └── *.sql
└── target/
    └── manifest.json       # Compiled manifest (compiled artifact)
```

**Path Resolution**: `{dbt_project_path}/target/manifest.json`

### 1.2 Manifest JSON Root Structure

```json
{
  "metadata": {
    "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12.json",
    "dbt_version": "1.8.0",
    "generated_at": "2024-12-15T10:00:00Z",
    "project_name": "my_project"
  },
  "nodes": {
    "model.package.model_name": { ... }
  },
  "sources": {
    "source.package.source_name.table_name": { ... }
  },
  "macros": { ... },
  "docs": { ... },
  "exposures": { ... },
  "metrics": { ... },
  "groups": { ... },
  "selectors": { ... },
  "parent_map": { ... },
  "child_map": { ... }
}
```

---

## 2. Node Structure - Model Column Metadata

### 2.1 Model Node Structure (Relevant Fields)

Each model in `manifest.nodes` contains:

```python
# From dbt.artifacts.resources.v1.components.py
@dataclass
class ParsedResource:
    """Compiled resource in manifest."""

    # Model identification
    unique_id: str = "model.package.model_name"
    name: str = "model_name"
    resource_type: str = "model"  # or "seed", "snapshot", etc.

    # Column-level metadata (THIS IS WHAT WE NEED)
    columns: Dict[str, ColumnInfo] = field(default_factory=dict)

    # Additional metadata
    description: str
    meta: Dict[str, Any]  # Model-level meta (separate from columns)
    tags: List[str]
```

### 2.2 ColumnInfo Structure

```python
# From dbt.artifacts.resources.v1.components.py
@dataclass
class ColumnInfo(AdditionalPropertiesMixin, ExtensibleDbtClassMixin):
    """Column metadata in manifest.

    This is the actual structure available in manifest.json for each column.
    """

    # Column identification
    name: str = "column_name"
    description: str = ""

    # COLUMN-LEVEL META TAGS (PRIMARY SOURCE FOR CLASSIFICATION)
    meta: Dict[str, Any] = field(default_factory=dict)

    # Data type information
    data_type: Optional[str] = None  # "string", "int64", etc.

    # Constraints (not relevant for classification)
    constraints: List[ColumnLevelConstraint] = field(default_factory=list)

    # Additional metadata
    quote: Optional[bool] = None
    config: ColumnConfig = field(default_factory=ColumnConfig)
    tags: List[str] = field(default_factory=list)
    granularity: Optional[TimeGranularity] = None
    doc_blocks: List[str] = field(default_factory=list)
```

### 2.3 Actual JSON Representation in manifest.json

```json
{
  "nodes": {
    "model.myproject.stg_customers": {
      "unique_id": "model.myproject.stg_customers",
      "name": "stg_customers",
      "resource_type": "model",
      "package_name": "myproject",
      "columns": {
        "customer_id": {
          "name": "customer_id",
          "description": "Customer identifier",
          "data_type": "int64",
          "meta": {
            "floe": {
              "classification": "identifier",
              "sensitivity": "medium"
            }
          },
          "constraints": [],
          "tags": [],
          "quote": null,
          "config": {}
        },
        "email": {
          "name": "email",
          "description": "Customer email address",
          "data_type": "string",
          "meta": {
            "floe": {
              "classification": "pii",
              "pii_type": "email",
              "sensitivity": "high"
            },
            "owner": "data-eng"
          },
          "constraints": [],
          "tags": ["sensitive"],
          "quote": null,
          "config": {}
        },
        "phone": {
          "name": "phone",
          "description": "Customer phone number",
          "data_type": "string",
          "meta": {
            "floe": {
              "classification": "pii",
              "pii_type": "phone",
              "sensitivity": "high"
            }
          },
          "constraints": [],
          "tags": [],
          "quote": null,
          "config": {}
        },
        "revenue": {
          "name": "revenue",
          "description": "Annual revenue",
          "data_type": "float64",
          "meta": {
            "floe": {
              "classification": "financial",
              "sensitivity": "medium"
            }
          },
          "constraints": [],
          "tags": [],
          "quote": null,
          "config": {}
        }
      },
      "meta": {
        "owner": "analytics_team"
      },
      "description": "Staging table for customers",
      "tags": ["staging"]
    }
  }
}
```

### 2.4 Source Definition Structure

Sources (database tables) are stored separately in `manifest.sources`:

```json
{
  "sources": {
    "source.myproject.raw.customers": {
      "unique_id": "source.myproject.raw.customers",
      "source_name": "raw",
      "name": "customers",
      "resource_type": "source",
      "columns": {
        "id": {
          "name": "id",
          "description": "",
          "data_type": null,
          "meta": {},
          "constraints": [],
          "tags": []
        }
      }
    }
  }
}
```

---

## 3. Classification Metadata Structure in dbt Meta Tags

### 3.1 dbt Schema Definition (Source)

In `models/schema.yml`:

```yaml
models:
  - name: stg_customers
    description: Staging layer for customers
    columns:
      - name: customer_id
        description: Unique customer identifier
        meta:
          floe:
            classification: identifier
            sensitivity: medium

      - name: email
        description: Customer email address
        meta:
          floe:
            classification: pii
            pii_type: email
            sensitivity: high

      - name: phone
        description: Customer phone number
        meta:
          floe:
            classification: pii
            pii_type: phone
            sensitivity: high

      - name: revenue
        description: Annual revenue amount
        meta:
          floe:
            classification: financial
            sensitivity: medium
```

### 3.2 Classification Meta Tags Specification

**Location**: `node.columns[column_name].meta.floe`

**Structure**:
```python
{
    "classification": str,  # Required. Options: "pii", "financial", "identifier", "public", custom
    "pii_type": Optional[str],  # Optional. Examples: "email", "phone", "ssn", "credit_card"
    "sensitivity": str,  # Optional. Default: "medium". Options: "low", "medium", "high", "critical"
    "description": Optional[str],  # Optional. Classification rationale
    # Additional custom fields allowed
}
```

### 3.3 Extraction Path in Manifest

For a model at `node.columns['email'].meta`:

```python
# Navigate the manifest
node = manifest['nodes']['model.package.model_name']
column_info = node['columns']['email']
floe_meta = column_info.get('meta', {}).get('floe', {})

# Extract classification
classification = floe_meta.get('classification')  # Returns: "pii"
pii_type = floe_meta.get('pii_type')  # Returns: "email"
sensitivity = floe_meta.get('sensitivity', 'medium')  # Returns: "high"
```

---

## 4. Python Implementation Patterns

### 4.1 Basic Manifest Loading (Using orjson)

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

def load_dbt_manifest(dbt_project_path: Path) -> dict[str, Any]:
    """Load dbt manifest.json from target directory.

    Args:
        dbt_project_path: Path to dbt project root

    Returns:
        Parsed manifest dictionary

    Raises:
        FileNotFoundError: If manifest.json not found
        json.JSONDecodeError: If manifest.json is invalid
    """
    manifest_path = dbt_project_path / "target" / "manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"dbt manifest not found at {manifest_path}. "
            "Run 'dbt parse' or 'dbt compile' first."
        )

    try:
        # Use orjson for performance on large manifests
        import orjson
        return orjson.loads(manifest_path.read_bytes())
    except ImportError:
        # Fallback to standard json
        return json.loads(manifest_path.read_text())
```

### 4.2 Classification Extraction Function

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

def extract_column_classifications(
    dbt_project_path: Path | str,
    strict: bool = False,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Extract column-level classifications from dbt manifest.

    Parses dbt manifest.json and extracts classification metadata from column
    meta tags. Only processes model and source nodes.

    Args:
        dbt_project_path: Path to dbt project root containing target/manifest.json
        strict: If True, raise on missing manifest. If False, log warning and return empty dict.

    Returns:
        Dictionary structure:
        {
            "model_name": {
                "column_name": {
                    "classification": "pii",
                    "pii_type": "email",
                    "sensitivity": "high"
                }
            }
        }

    Example:
        >>> classifications = extract_column_classifications(Path("my_dbt_project"))
        >>> classifications["stg_customers"]["email"]
        {'classification': 'pii', 'pii_type': 'email', 'sensitivity': 'high'}
    """
    dbt_project_path = Path(dbt_project_path)
    manifest_path = dbt_project_path / "target" / "manifest.json"

    # Handle missing manifest gracefully
    if not manifest_path.exists():
        msg = (
            f"dbt manifest not found at {manifest_path}. "
            "Run 'dbt parse' or 'dbt compile' first."
        )
        if strict:
            raise FileNotFoundError(msg)
        else:
            logger.warning(msg)
            return {}

    # Load manifest
    try:
        import orjson
        manifest = orjson.loads(manifest_path.read_bytes())
    except ImportError:
        import json
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, ValueError) as e:
        msg = f"Invalid manifest.json at {manifest_path}: {e}"
        if strict:
            raise ValueError(msg) from e
        else:
            logger.error(msg)
            return {}

    # Extract classifications
    classifications: dict[str, dict[str, dict[str, Any]]] = {}

    # Process models
    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue

        model_name = node["name"]
        model_classifications = _extract_node_classifications(node)

        if model_classifications:
            classifications[model_name] = model_classifications

    # Process sources (optional - sources may not have classifications)
    for source_id, source in manifest.get("sources", {}).items():
        # Sources in dbt are typically raw data - less likely to have classifications
        # But include them for completeness
        source_name = f"{source['source_name']}.{source['name']}"
        source_classifications = _extract_node_classifications(source)

        if source_classifications:
            classifications[source_name] = source_classifications

    logger.info(
        f"Extracted classifications",
        extra={
            "model_count": len(classifications),
            "total_columns": sum(
                len(cols) for cols in classifications.values()
            ),
        }
    )

    return classifications


def _extract_node_classifications(
    node: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Extract classifications from a single node (model or source).

    Args:
        node: Node dictionary from manifest

    Returns:
        Dict of column_name -> classification metadata
    """
    model_classifications: dict[str, dict[str, Any]] = {}

    # Iterate over columns in the node
    for column_name, column_info in node.get("columns", {}).items():
        # Extract floe meta tags
        floe_meta = column_info.get("meta", {}).get("floe", {})

        # Only include columns with classification
        if not floe_meta.get("classification"):
            continue

        # Build classification record
        classification_record: dict[str, Any] = {
            "classification": floe_meta["classification"],
        }

        # Add optional fields if present
        if "pii_type" in floe_meta:
            classification_record["pii_type"] = floe_meta["pii_type"]

        if "sensitivity" in floe_meta:
            classification_record["sensitivity"] = floe_meta["sensitivity"]
        else:
            # Default sensitivity
            classification_record["sensitivity"] = "medium"

        # Include additional custom fields
        for key, value in floe_meta.items():
            if key not in ("classification", "pii_type", "sensitivity"):
                classification_record[key] = value

        model_classifications[column_name] = classification_record

    return model_classifications
```

### 4.3 Integration with Pydantic Models

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)

class ColumnClassification(BaseModel):
    """Classification metadata for a single column."""

    classification: str = Field(
        ...,
        description="Classification type (pii, financial, identifier, public, etc)",
        min_length=1,
    )
    pii_type: Optional[str] = Field(
        None,
        description="Type of PII (email, phone, ssn, credit_card, etc)",
    )
    sensitivity: str = Field(
        default="medium",
        description="Sensitivity level (low, medium, high, critical)",
        pattern=r"^(low|medium|high|critical)$",
    )

    @field_validator("classification")
    @classmethod
    def validate_classification(cls, v: str) -> str:
        """Validate classification against known types."""
        allowed = {"pii", "financial", "identifier", "public"}
        # Allow custom classifications but log them
        if v not in allowed:
            logger.debug(f"Using custom classification: {v}")
        return v


class ModelClassifications(BaseModel):
    """Classifications for all columns in a model."""

    model_name: str = Field(..., description="dbt model name")
    columns: dict[str, ColumnClassification] = Field(
        default_factory=dict,
        description="Column name -> classification metadata",
    )


class ExtractedClassifications(BaseModel):
    """Result of classification extraction from dbt manifest."""

    models: dict[str, ModelClassifications] = Field(
        default_factory=dict,
        description="Model name -> classifications",
    )
    extraction_source: str = Field(
        default="dbt_manifest",
        description="Source of classifications",
    )

    def to_flat_dict(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Convert to flat dictionary format for CompiledArtifacts.

        Returns format expected by floe-core:
        {
            "model_name": {
                "column_name": {
                    "classification": "...",
                    ...
                }
            }
        }
        """
        return {
            model_name: model_cls.columns
            for model_name, model_cls in self.models.items()
        }
```

### 4.4 Error Handling - Graceful Degradation

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

def extract_classifications_with_fallback(
    dbt_project_path: Path | str,
    specification_version: str = "1.0.0",
) -> dict[str, dict[str, dict[str, Any]]]:
    """Extract classifications with comprehensive error handling.

    Follows floe-core philosophy: Standalone first, graceful degradation.

    Errors are handled as follows:
    - Missing manifest: Log warning, return empty dict (continue without classifications)
    - Invalid JSON: Log error, return empty dict (manifest is corrupted)
    - Missing columns: Log info, skip node (dbt parse may not have completed)
    - Invalid meta structure: Log debug, skip column (user error in schema.yml)

    Args:
        dbt_project_path: Path to dbt project
        specification_version: Expected manifest version (for logging)

    Returns:
        Classifications dictionary (empty if errors encountered)
    """
    dbt_project_path = Path(dbt_project_path)
    manifest_path = dbt_project_path / "target" / "manifest.json"

    # Step 1: Verify manifest exists
    if not manifest_path.exists():
        logger.warning(
            "dbt manifest not found - running without classification extraction",
            extra={
                "manifest_path": str(manifest_path),
                "dbt_project": str(dbt_project_path),
                "suggestion": "Run 'dbt parse' or 'dbt compile' to generate manifest.json",
            }
        )
        return {}

    # Step 2: Load manifest
    try:
        try:
            import orjson
            manifest = orjson.loads(manifest_path.read_bytes())
        except ImportError:
            import json
            manifest = json.loads(manifest_path.read_text())
    except Exception as e:
        logger.error(
            "Failed to parse manifest.json",
            extra={
                "error": str(e),
                "path": str(manifest_path),
                "type": type(e).__name__,
            }
        )
        return {}

    # Step 3: Verify manifest version
    manifest_version = manifest.get("metadata", {}).get("dbt_schema_version", "unknown")
    logger.info(
        "Loaded dbt manifest",
        extra={
            "path": str(manifest_path),
            "schema_version": manifest_version,
            "nodes": len(manifest.get("nodes", {})),
        }
    )

    # Step 4: Extract classifications with error handling per node
    classifications: dict[str, dict[str, dict[str, Any]]] = {}

    for node_id, node in manifest.get("nodes", {}).items():
        try:
            # Skip non-model nodes
            if node.get("resource_type") != "model":
                continue

            model_name = node.get("name", "unknown")

            # Extract classifications from this node
            try:
                model_classifications = _extract_node_classifications(node)
            except Exception as e:
                logger.debug(
                    f"Failed to extract classifications from model",
                    extra={
                        "model": model_name,
                        "node_id": node_id,
                        "error": str(e),
                    }
                )
                continue

            if model_classifications:
                classifications[model_name] = model_classifications

        except Exception as e:
            # Catch unexpected errors during iteration
            logger.debug(
                "Unexpected error processing node",
                extra={
                    "node_id": node_id,
                    "error": str(e),
                }
            )
            continue

    logger.info(
        "Classification extraction complete",
        extra={
            "models_with_classifications": len(classifications),
            "total_classified_columns": sum(
                len(cols) for cols in classifications.values()
            ),
        }
    )

    return classifications
```

### 4.5 Integration with floe-core Compiler

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

class FloeSpec(BaseModel):
    """floe.yaml parsed specification."""
    name: str
    version: str = "1.0"
    governance: dict[str, Any] = Field(default_factory=dict)
    # ... other fields


class CompiledArtifacts(BaseModel):
    """Output of compilation."""
    version: str = "1.0.0"
    metadata: dict[str, Any]
    compute: dict[str, Any]
    transforms: list[dict[str, Any]] = Field(default_factory=list)
    governance: dict[str, Any] = Field(default_factory=dict)

    # Classification metadata extracted from dbt
    column_classifications: Optional[dict[str, dict[str, dict[str, Any]]]] = None
    dbt_project_path: Optional[str] = None
    dbt_manifest_path: Optional[str] = None


class Compiler:
    """Compile floe.yaml to CompiledArtifacts."""

    def compile(self, spec_path: Path) -> CompiledArtifacts:
        """Parse floe.yaml and compile to artifacts.

        Extracts classifications from dbt manifest if:
        1. dbt project exists in parent directory
        2. governance.classification_source == "dbt_meta"
        3. manifest.json exists
        """
        # Parse floe.yaml
        import yaml
        with open(spec_path) as f:
            raw = yaml.safe_load(f)

        spec = FloeSpec.model_validate(raw)

        # Find dbt project (optional)
        dbt_project_path = self._find_dbt_project(spec_path.parent)

        # Extract classifications if available
        column_classifications = None
        dbt_manifest_path = None

        if dbt_project_path:
            dbt_project_path_obj = Path(dbt_project_path)
            dbt_manifest_path = str(dbt_project_path_obj / "target" / "manifest.json")

            # Only extract if classification_source is "dbt_meta"
            if spec.governance.get("classification_source") == "dbt_meta":
                try:
                    column_classifications = extract_column_classifications(
                        dbt_project_path_obj,
                        strict=False,  # Graceful degradation
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to extract classifications: {e}",
                        extra={"dbt_project": str(dbt_project_path)},
                    )
                    column_classifications = None

        # Build compiled artifacts
        return CompiledArtifacts(
            version="1.0.0",
            metadata={
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
            },
            compute=spec.model_dump().get("compute", {}),
            transforms=spec.model_dump().get("transforms", []),
            governance=spec.governance,
            column_classifications=column_classifications,
            dbt_project_path=dbt_project_path,
            dbt_manifest_path=dbt_manifest_path,
        )

    def _find_dbt_project(self, start_path: Path) -> Optional[str]:
        """Find dbt_project.yml in current or parent directories."""
        current = start_path

        for _ in range(5):  # Search up to 5 levels
            if (current / "dbt_project.yml").exists():
                return str(current)

            if current.parent == current:
                break  # Reached filesystem root

            current = current.parent

        return None
```

### 4.6 Unit Tests

```python
import pytest
from pathlib import Path
import json
import tempfile
from typing import Any

def test_extract_classifications_basic():
    """Test basic classification extraction."""
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
                        }
                    }
                }
            }
        },
        "sources": {}
    }

    classifications = _extract_node_classifications(
        manifest["nodes"]["model.test.customers"]
    )

    assert "email" in classifications
    assert classifications["email"]["classification"] == "pii"
    assert classifications["email"]["pii_type"] == "email"
    assert classifications["email"]["sensitivity"] == "high"


def test_extract_classifications_missing_fields():
    """Test extraction with missing optional fields."""
    manifest_node = {
        "name": "products",
        "resource_type": "model",
        "columns": {
            "id": {
                "name": "id",
                "meta": {
                    "floe": {
                        "classification": "identifier"
                        # pii_type and sensitivity omitted
                    }
                }
            }
        }
    }

    classifications = _extract_node_classifications(manifest_node)

    assert "id" in classifications
    assert classifications["id"]["classification"] == "identifier"
    assert classifications["id"].get("pii_type") is None
    assert classifications["id"]["sensitivity"] == "medium"  # Default


def test_extract_classifications_no_floe_meta():
    """Test extraction when columns have no floe meta."""
    manifest_node = {
        "name": "staging",
        "resource_type": "model",
        "columns": {
            "col1": {
                "name": "col1",
                "meta": {}  # No floe meta
            },
            "col2": {
                "name": "col2",
                "meta": {
                    "owner": "analytics"  # Other meta but no floe
                }
            }
        }
    }

    classifications = _extract_node_classifications(manifest_node)

    assert classifications == {}


def test_extract_missing_manifest():
    """Test graceful handling of missing manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dbt_project = Path(tmpdir)

        # No target/manifest.json
        classifications = extract_column_classifications(
            dbt_project,
            strict=False
        )

        assert classifications == {}


def test_extract_invalid_manifest_json():
    """Test graceful handling of corrupted JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dbt_project = Path(tmpdir)
        target = dbt_project / "target"
        target.mkdir()

        # Write invalid JSON
        (target / "manifest.json").write_text("{invalid json")

        classifications = extract_column_classifications(
            dbt_project,
            strict=False
        )

        assert classifications == {}
```

---

## 5. Handling Missing Manifest - Best Practices

### 5.1 Philosophy: Graceful Degradation

floe-core must remain functional without dbt manifest. Classification extraction is **optional**:

- If manifest exists → Extract classifications
- If manifest missing → Log warning, continue
- If extraction fails → Log error, continue with empty classifications

### 5.2 Implementation Pattern

```python
def compile_with_optional_classifications(
    spec_path: Path,
    strict_classification: bool = False,
) -> CompiledArtifacts:
    """Compile floe.yaml with optional classification extraction.

    Args:
        spec_path: Path to floe.yaml
        strict_classification: If True, fail on classification errors.
                             If False (default), continue without classifications.
    """
    # Parse floe.yaml (required)
    spec = parse_floe_yaml(spec_path)

    # Find dbt project (optional)
    dbt_project = find_dbt_project(spec_path.parent)

    if not dbt_project:
        logger.info("No dbt project found - proceeding without classifications")
        return CompiledArtifacts(
            # ... core fields ...
            column_classifications=None,
        )

    # Extract classifications (optional)
    try:
        classifications = extract_column_classifications(
            dbt_project,
            strict=strict_classification,
        )
    except Exception as e:
        if strict_classification:
            raise
        logger.error(f"Classification extraction failed: {e}")
        classifications = None

    return CompiledArtifacts(
        # ... core fields ...
        column_classifications=classifications,
    )
```

### 5.3 Logging Strategy

```python
import logging

logger = logging.getLogger(__name__)

# Graceful degradation strategy
if not manifest_path.exists():
    logger.warning(
        "dbt manifest not found",
        extra={
            "path": str(manifest_path),
            "suggestion": "Run 'dbt parse' to generate manifest.json",
        }
    )
    return {}

if manifest_version not in SUPPORTED_VERSIONS:
    logger.warning(
        "Manifest version not supported",
        extra={
            "version": manifest_version,
            "supported": SUPPORTED_VERSIONS,
        }
    )
    # Continue anyway - try best effort

if error_extracting_classifications:
    logger.error(
        "Classification extraction failed",
        extra={
            "reason": "column meta structure invalid",
            "model": model_name,
        }
    )
    # Continue without this model's classifications
```

---

## 6. Alternatives Considered

### 6.1 Using dbt Python API (dbtRunner)

**Alternative**: Import dbt programmatically using `dbt.cli.main.dbtRunner`

**Pros**:
- Latest dbt semantics
- Automatic compatibility

**Cons**:
- Heavy dependency (dbt entire package)
- Requires dbt invocation (slow, side effects)
- Difficult to isolate/mock in tests
- Not needed - manifest already compiled

**Decision**: ❌ **Rejected**. The manifest.json is already compiled. Direct JSON parsing is simpler and faster.

### 6.2 Using dagster-dbt Integration

**Alternative**: Use `dagster_dbt.dbt_manifest.read_manifest_path`

**Pros**:
- Standard library in ecosystem
- Handles caching

**Cons**:
- Adds unnecessary dependency
- Only used at runtime, not at compile time
- floe-core should not depend on floe-dagster

**Decision**: ❌ **Rejected**. floe-core must be independent of runtime packages.

### 6.3 Parsing dbt YAML Files Directly (schema.yml)

**Alternative**: Parse `models/schema.yml` directly instead of manifest.json

**Pros**:
- Closer to source of truth
- No compilation step needed

**Cons**:
- Requires dbt YAML parsing (complex, fragile)
- Multiple schema.yml files to search
- Doesn't match actual compiled state
- dbt handles transformations (jinja, includes, etc.)

**Decision**: ❌ **Rejected**. manifest.json is the authoritative compiled representation.

### 6.4 Using dbt Manifest Artifact (v1 Protocol)

**Alternative**: Use typed dbt artifacts API instead of raw JSON

**Pros**:
- Type safety
- Version-aware deserialization

**Cons**:
- Heavy dbt dependency
- Version compatibility issues
- Slower than direct JSON parsing
- Raw JSON is simple and portable

**Decision**: ❌ **Rejected**. Direct JSON parsing is sufficient and lightweight.

### 6.5 Custom SQL Parser

**Alternative**: Parse SQL SELECT statements to infer columns

**Cons**: ❌ **FORBIDDEN** per floe-core philosophy
- dbt owns SQL parsing
- No custom SQL parsing in Python
- Would duplicate dbt's effort
- Cannot handle all SQL dialects

**Decision**: ❌ **Rejected**. This violates component ownership principles.

---

## 7. Best Practices for Manifest Parsing

### 7.1 Performance Optimization

```python
# Use orjson for large manifests (dbt manifests can be 100MB+)
try:
    import orjson
    manifest = orjson.loads(manifest_path.read_bytes())
except ImportError:
    import json
    manifest = json.loads(manifest_path.read_text())
```

**Performance Comparison**:
- orjson: ~100ms for 100MB manifest
- json: ~500ms for 100MB manifest

### 7.2 Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def load_manifest_cached(manifest_path: Path) -> dict:
    """Load manifest once and cache it."""
    return load_manifest(manifest_path)
```

### 7.3 Validation

```python
# Validate manifest structure before processing
required_keys = {"metadata", "nodes", "sources"}
missing = required_keys - set(manifest.keys())

if missing:
    logger.warning(f"Manifest missing keys: {missing}")
```

### 7.4 Version Compatibility

```python
# Check manifest version
manifest_version = manifest.get("metadata", {}).get("dbt_schema_version")

# Currently support dbt 1.5+ (schema version 12+)
if not manifest_version or "v12" not in manifest_version:
    logger.warning(f"Untested manifest version: {manifest_version}")
```

---

## 8. Decision Summary

### Decision: Direct JSON Parsing of manifest.json

**Approach**:
1. Load `target/manifest.json` using `json` or `orjson`
2. Iterate over `manifest["nodes"]`
3. Filter for `resource_type == "model"`
4. Extract `node["columns"][col_name]["meta"]["floe"]`
5. Build classification dictionary

**Rationale**:
- **Simple**: No external APIs, direct JSON parsing
- **Fast**: orjson can process 100MB+ manifests in ~100ms
- **Reliable**: manifest.json is authoritative dbt artifact
- **Portable**: Works across dbt versions (v1.5+)
- **Independent**: floe-core has no dbt runtime dependencies
- **Testable**: Mock manifest easily in unit tests
- **Graceful**: Handles missing manifest with logging

**Implementation Pattern**:

```python
def extract_column_classifications(
    dbt_project_path: Path,
    strict: bool = False,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Extract classifications from dbt manifest.

    Location: {dbt_project_path}/target/manifest.json
    Path to classifications: nodes[model_id].columns[col_name].meta.floe
    """
    manifest_path = dbt_project_path / "target" / "manifest.json"

    # Graceful degradation: missing manifest is not an error
    if not manifest_path.exists():
        logger.warning(f"Manifest not found: {manifest_path}")
        return {} if not strict else raise FileNotFoundError(...)

    # Parse manifest
    manifest = json.loads(manifest_path.read_text())  # or orjson

    # Extract classifications
    classifications = {}
    for node_id, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue

        model_name = node["name"]
        for col_name, col_info in node.get("columns", {}).items():
            floe_meta = col_info.get("meta", {}).get("floe", {})
            if classification := floe_meta.get("classification"):
                classifications.setdefault(model_name, {})[col_name] = {
                    "classification": classification,
                    "pii_type": floe_meta.get("pii_type"),
                    "sensitivity": floe_meta.get("sensitivity", "medium"),
                }

    return classifications
```

---

## 9. References

### dbt Documentation
- **Manifest Schema**: dbt v1.8 schema v12 (see `/dbt/artifacts/resources/v1/components.py`)
- **ColumnInfo Definition**: `dbt.artifacts.resources.v1.components.ColumnInfo`
- **Meta Tags**: User-defined arbitrary metadata stored in column `meta` field

### floe-runtime Documentation
- **Governance Design**: `/docs/03-solution-strategy.md` (Section 12)
- **Building Blocks**: `/docs/04-building-blocks.md` (Compiler section)
- **Implementation Roadmap**: `/docs/11-implementation-roadmap.md` (Task E1-F6)

### Code Locations
- **dbt Manifest Loading**: `dagster_dbt/dbt_manifest.py`
- **dbt Resource Models**: `dbt/artifacts/resources/v1/components.py`
- **dbt ParsedResource**: Contains `columns: Dict[str, ColumnInfo]` field

---

## 10. Implementation Checklist

- [ ] Implement `extract_column_classifications()` in `floe-core/compiler.py`
- [ ] Add Pydantic models for classification schema
- [ ] Implement graceful error handling (missing manifest, invalid JSON)
- [ ] Add logging for classification extraction pipeline
- [ ] Implement unit tests (basic extraction, missing fields, no meta)
- [ ] Add integration tests with mock manifest
- [ ] Document column meta tag specification in schema
- [ ] Update floe.yaml examples with classification dbt models
- [ ] Verify no SQL parsing occurs (component ownership)
- [ ] Performance test with large manifests (100MB+)

---

**Document Status**: COMPLETE
**Last Updated**: December 15, 2025
