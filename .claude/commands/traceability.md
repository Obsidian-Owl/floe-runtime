# /traceability

Generate a traceability report showing requirement-to-test coverage across all features.

## Usage

```bash
/traceability                  # Multi-feature report (all features 001-006)
/traceability --feature 006    # Single feature report
/traceability --format json    # JSON output for CI
/traceability --threshold 100  # Exit 1 if coverage < 100%
```

## What This Does

1. Scans all spec files (`specs/*/spec.md`) for FR-XXX requirements
2. Scans all test files for `@pytest.mark.requirement()` markers
3. Generates coverage matrix showing:
   - Which requirements are covered by tests
   - Which requirements have no test coverage (gaps)
   - Per-feature breakdown (001-006)

## Implementation

Run the traceability reporter based on the arguments provided:

```bash
# Multi-feature report (default)
python -m testing.traceability --all

# Single feature with threshold
python -m testing.traceability --feature-id $FEATURE_ID --threshold 100

# JSON output for CI integration
python -m testing.traceability --all --format json --threshold 100
```

## Output Format

### Console Output (Default)

```
Multi-Feature Traceability Report
======================================================================
Generated: 2025-12-20 14:30:00 UTC

Feature Name                      Reqs Cover   Pct  Markers
----------------------------------------------------------------------
001    Core Foundation              28    28 100.0%       45
002    CLI Interface                15    15 100.0%       22
003    Orchestration Layer          24    24 100.0%       38
004    Storage Catalog              38    38 100.0%       62
005    Consumption Layer            36    36 100.0%       48
006    Integration Testing          35    35 100.0%       55
----------------------------------------------------------------------
TOTAL                              176   176 100.0%      270

No coverage gaps - all requirements covered!
```

### JSON Output (--format json)

```json
{
  "generated_at": "2025-12-20T14:30:00Z",
  "total_requirements": 176,
  "total_covered": 176,
  "total_coverage_percentage": 100.0,
  "features": [...],
  "gaps_by_feature": {}
}
```

## Success Criteria

- **100% coverage required** on all features (001-006)
- All requirements use feature-scoped format: `{feature}-FR-{id}`
- Tests can have N markers from any number of features (many-to-many)

## Requirement ID Format

Use feature-scoped format: `{feature}-FR-{id}`

| Example | Meaning |
|---------|---------|
| `006-FR-012` | Feature 006 (Integration Testing), Requirement FR-012 |
| `004-FR-001` | Feature 004 (Storage Catalog), Requirement FR-001 |
| `001-FR-005` | Feature 001 (Core Foundation), Requirement FR-005 |

## Multi-Marker Pattern

A single test can satisfy requirements from multiple features:

```python
@pytest.mark.requirement("006-FR-012")  # Meta: floe-polaris tests exist
@pytest.mark.requirement("004-FR-001")  # Functional: Polaris REST connection
@pytest.mark.requirement("004-FR-002")  # Functional: OAuth2 authentication
def test_polaris_catalog_connection():
    """Test that covers multiple requirements from multiple features."""
    pass
```

## Gap Resolution

If the traceability report shows gaps:

1. Review the uncovered requirements in the spec file
2. Identify which tests should cover the requirement
3. Add `@pytest.mark.requirement()` markers to existing tests, OR
4. Write new tests if no existing test covers the requirement
5. Re-run the report until 100% coverage achieved

## Related Commands

- `/validate` - Run all quality checks (includes traceability)
- `/speckit.implement` - Implement tasks (requires traceability verification)
- `/speckit.checklist` - Generate checklist (includes traceability items)

## CI Integration

Add to CI pipeline:

```yaml
- name: Verify Requirement Traceability
  run: python -m testing.traceability --all --threshold 100
```

This ensures all features have 100% requirement coverage before merge.
