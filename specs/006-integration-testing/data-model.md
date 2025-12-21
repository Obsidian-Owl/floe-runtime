# Data Model: Integration Testing Traceability

**Feature**: 006-integration-testing
**Date**: 2025-12-19
**Status**: Design

## Overview

This document defines the data model for the traceability system that maps functional requirements (FR-XXX) from feature specifications to their corresponding integration tests. The model enables automated coverage reporting, gap detection, and CI/CD integration.

## Core Entities

### 1. Requirement

Represents a functional requirement extracted from a specification file.

```python
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class RequirementCategory(str, Enum):
    """Categories for functional requirements."""
    TRACEABILITY = "traceability"
    EXECUTION = "execution"
    PACKAGE_COVERAGE = "package_coverage"
    INFRASTRUCTURE = "infrastructure"
    SHARED_FIXTURES = "shared_fixtures"
    PRODUCTION_CONFIG = "production_config"
    OBSERVABILITY = "observability"
    ROW_LEVEL_SECURITY = "row_level_security"
    STANDALONE_FIRST = "standalone_first"
    CONTRACT_BOUNDARY = "contract_boundary"


class Requirement(BaseModel):
    """A functional requirement from a specification.

    Attributes:
        id: Unique identifier (e.g., "FR-001")
        spec_file: Path to the specification file
        line_number: Line number in spec file where requirement is defined
        text: Full text of the requirement
        category: Category classification
        priority: Priority level (P1, P2, P3)
    """
    id: str = Field(..., pattern=r"^FR-\d{3}$")
    spec_file: str
    line_number: int
    text: str
    category: RequirementCategory
    priority: str = Field(default="P2", pattern=r"^P[1-3]$")
```

### 2. Test

Represents an integration test function that covers one or more requirements.

```python
from pydantic import BaseModel, Field


class TestMarker(str, Enum):
    """pytest markers for integration tests."""
    INTEGRATION = "integration"
    E2E = "e2e"
    SLOW = "slow"
    REQUIRES_DOCKER = "requires_docker"


class Test(BaseModel):
    """An integration test that covers requirements.

    Attributes:
        file_path: Path to the test file
        function_name: Test function name
        class_name: Test class name (if any)
        markers: List of pytest markers
        requirement_ids: List of FR-XXX IDs this test covers
        package: Package name (e.g., "floe-core")
    """
    file_path: str
    function_name: str
    class_name: str | None = None
    markers: list[TestMarker] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    package: str
```

### 3. TraceabilityMapping

Represents the relationship between requirements and tests.

```python
from enum import Enum
from pydantic import BaseModel, Field


class CoverageStatus(str, Enum):
    """Coverage status for a requirement."""
    COVERED = "covered"  # Has at least one passing test
    PARTIAL = "partial"  # Has tests but they're incomplete/failing
    UNCOVERED = "uncovered"  # No tests exist
    EXCLUDED = "excluded"  # Intentionally not tested (document reason)


class TraceabilityMapping(BaseModel):
    """Mapping between a requirement and its tests.

    Attributes:
        requirement_id: The requirement ID (FR-XXX)
        test_ids: List of test identifiers (file::class::function)
        coverage_status: Current coverage status
        notes: Optional notes about coverage
    """
    requirement_id: str
    test_ids: list[str] = Field(default_factory=list)
    coverage_status: CoverageStatus = CoverageStatus.UNCOVERED
    notes: str | None = None
```

### 4. TraceabilityMatrix

The complete traceability matrix for a feature.

```python
from datetime import datetime
from pydantic import BaseModel, Field


class TraceabilityMatrix(BaseModel):
    """Complete traceability matrix for a feature.

    Attributes:
        feature_id: Feature identifier (e.g., "006")
        feature_name: Human-readable feature name
        generated_at: Timestamp of generation
        spec_files: List of specification files analyzed
        requirements: All requirements extracted
        tests: All tests discovered
        mappings: Requirement-to-test mappings
    """
    feature_id: str
    feature_name: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    spec_files: list[str]
    requirements: list[Requirement]
    tests: list[Test]
    mappings: list[TraceabilityMapping]

    def get_coverage_percentage(self) -> float:
        """Calculate overall coverage percentage."""
        if not self.requirements:
            return 100.0
        covered = sum(
            1 for m in self.mappings
            if m.coverage_status in (CoverageStatus.COVERED, CoverageStatus.EXCLUDED)
        )
        return (covered / len(self.requirements)) * 100

    def get_gaps(self) -> list[Requirement]:
        """Get requirements without test coverage."""
        uncovered_ids = {
            m.requirement_id for m in self.mappings
            if m.coverage_status == CoverageStatus.UNCOVERED
        }
        return [r for r in self.requirements if r.id in uncovered_ids]
```

## Test Report Schema

For CI/CD integration, a simplified report format.

```python
from pydantic import BaseModel, Field


class TestResult(BaseModel):
    """Result of a single test execution."""
    test_id: str  # file::class::function
    status: str  # passed, failed, skipped, error
    duration_ms: int
    error_message: str | None = None


class PackageCoverage(BaseModel):
    """Coverage summary for a package."""
    package: str
    total_requirements: int
    covered: int
    partial: int
    uncovered: int
    coverage_percentage: float


class TraceabilityReport(BaseModel):
    """CI-compatible traceability report.

    Attributes:
        feature_id: Feature identifier
        generated_at: Timestamp
        total_requirements: Total FR-XXX count
        covered: Fully covered count
        partial: Partially covered count
        uncovered: Uncovered count
        excluded: Excluded count
        coverage_percentage: Overall percentage
        packages: Per-package breakdown
        test_results: Test execution results
        gaps: List of uncovered requirement IDs
    """
    feature_id: str
    generated_at: str
    total_requirements: int
    covered: int
    partial: int
    uncovered: int
    excluded: int
    coverage_percentage: float
    packages: list[PackageCoverage]
    test_results: list[TestResult]
    gaps: list[str]
```

## Pytest Markers Convention

Tests should use markers to declare requirement coverage:

```python
import pytest

# Single requirement
@pytest.mark.requirement("006-FR-001")
def test_traceability_matrix_generation():
    ...

# Multiple requirements
@pytest.mark.requirements(["FR-032", "FR-033"])
def test_compiled_artifacts_boundary():
    ...

# Integration test with requirement
@pytest.mark.integration
@pytest.mark.requirement("006-FR-012")
def test_polaris_catalog_connection():
    ...
```

## JSON Schema Exports

### traceability-matrix.schema.json

See `contracts/traceability-matrix.schema.json` for the full JSON Schema.

### test-report.schema.json

See `contracts/test-report.schema.json` for the CI report schema.

## Usage Examples

### Generating a Traceability Matrix

```python
from testing.traceability import generate_matrix

matrix = generate_matrix(
    spec_files=["specs/006-integration-testing/spec.md"],
    test_dirs=["packages/*/tests/integration/"]
)

print(f"Coverage: {matrix.get_coverage_percentage():.1f}%")
for gap in matrix.get_gaps():
    print(f"  - {gap.id}: {gap.text[:50]}...")
```

### Querying Coverage by Package

```python
from testing.traceability import generate_matrix

matrix = generate_matrix(...)

# Filter by package
polaris_tests = [t for t in matrix.tests if t.package == "floe-polaris"]
polaris_reqs = [
    r for r in matrix.requirements
    if "polaris" in r.text.lower() or "FR-012" == r.id
]
```

### CI Integration

```python
from testing.traceability import generate_report

report = generate_report(feature_id="006")

# Fail CI if coverage below threshold
if report.coverage_percentage < 80:
    print(f"Coverage {report.coverage_percentage:.1f}% below 80% threshold")
    print(f"Gaps: {report.gaps}")
    exit(1)
```

## Entity Relationships

```
┌─────────────────┐       ┌─────────────────┐
│   Requirement   │       │      Test       │
├─────────────────┤       ├─────────────────┤
│ id: FR-XXX      │◄──────│ requirement_ids │
│ spec_file       │       │ file_path       │
│ line_number     │       │ function_name   │
│ text            │       │ package         │
│ category        │       │ markers         │
│ priority        │       └─────────────────┘
└─────────────────┘              │
        │                        │
        │    ┌──────────────────┘
        ▼    ▼
┌─────────────────────┐
│ TraceabilityMapping │
├─────────────────────┤
│ requirement_id      │
│ test_ids            │
│ coverage_status     │
│ notes               │
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│ TraceabilityMatrix  │
├─────────────────────┤
│ feature_id          │
│ requirements[]      │
│ tests[]             │
│ mappings[]          │
└─────────────────────┘
```

## Migration Notes

The traceability system is new. No migration required.

To add traceability to existing tests:
1. Add `@pytest.mark.requirement("FR-XXX")` markers
2. Run `floe test --traceability` to generate initial matrix
3. Review gaps and add missing tests
