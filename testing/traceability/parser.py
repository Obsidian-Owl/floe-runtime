"""Parser for extracting functional requirements from spec.md files.

This module provides functionality to parse specification files and extract
functional requirements (FR-XXX) with their metadata including line numbers,
category inference, and requirement text.

Functions:
    parse_requirements: Extract all FR-XXX requirements from a spec file

Usage:
    from testing.traceability.parser import parse_requirements

    requirements = parse_requirements(Path("specs/006-integration-testing/spec.md"))
    for req in requirements:
        print(f"{req.id}: {req.text} (line {req.line_number})")

See Also:
    testing.traceability.models for Requirement model definition
    specs/006-integration-testing/spec.md for requirement format examples
"""

from __future__ import annotations

from pathlib import Path
import re

from testing.traceability.models import Requirement, RequirementCategory

# Pattern to match FR-XXX requirements in markdown
# Matches: - **FR-001**: Description text
# or: * **FR-002**: Description text
# Security: Safe from ReDoS - anchored with ^ and $, no nested quantifiers
REQUIREMENT_PATTERN = re.compile(
    r"^[-*]\s+\*\*(?P<id>FR-\d{3})\*\*:\s*(?P<text>.+)$"  # nosonar: S4784
)

# Mapping from section heading keywords to categories
CATEGORY_KEYWORDS: dict[str, RequirementCategory] = {
    "traceability": RequirementCategory.TRACEABILITY,
    "execution": RequirementCategory.EXECUTION,
    "package coverage": RequirementCategory.PACKAGE_COVERAGE,
    "infrastructure": RequirementCategory.INFRASTRUCTURE,
    "shared test fixtures": RequirementCategory.SHARED_FIXTURES,
    "shared fixtures": RequirementCategory.SHARED_FIXTURES,
    "production config": RequirementCategory.PRODUCTION_CONFIG,
    "observability": RequirementCategory.OBSERVABILITY,
    "row-level security": RequirementCategory.ROW_LEVEL_SECURITY,
    "row level security": RequirementCategory.ROW_LEVEL_SECURITY,
    "standalone": RequirementCategory.STANDALONE_FIRST,
    "graceful degradation": RequirementCategory.STANDALONE_FIRST,
    "contract boundary": RequirementCategory.CONTRACT_BOUNDARY,
}


def parse_requirements(spec_path: Path) -> list[Requirement]:
    """Parse a spec.md file and extract all functional requirements.

    Scans the specification file for FR-XXX patterns and extracts:
    - Requirement ID (FR-001, FR-002, etc.)
    - Requirement text (after the colon)
    - Line number in the file
    - Category (inferred from section headings)

    Args:
        spec_path: Path to the specification markdown file.

    Returns:
        List of Requirement objects extracted from the file.
        Returns empty list if no requirements are found.

    Raises:
        FileNotFoundError: If the spec file doesn't exist.

    Example:
        >>> from pathlib import Path
        >>> requirements = parse_requirements(Path("specs/006-integration-testing/spec.md"))
        >>> for req in requirements:
        ...     print(f"{req.id}: {req.category.value}")
        FR-001: traceability
        FR-002: traceability
        ...
    """
    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")

    requirements: list[Requirement] = []
    current_category = RequirementCategory.EXECUTION  # Default category

    with spec_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.rstrip()

            # Check for section headings to update category
            if line.startswith("#"):
                category = _infer_category_from_heading(line)
                if category is not None:
                    current_category = category
                continue

            # Check for requirement pattern
            match = REQUIREMENT_PATTERN.match(line)
            if match:
                req_id = match.group("id")
                req_text = match.group("text").strip()

                # Validate the requirement ID format (exactly 3 digits)
                # Security: Safe - simple bounded pattern
                if not re.match(r"^FR-\d{3}$", req_id):  # nosonar: S4784
                    continue

                requirement = Requirement(
                    id=req_id,
                    spec_file=str(spec_path),
                    line_number=line_number,
                    text=req_text,
                    category=current_category,
                )
                requirements.append(requirement)

    return requirements


def _infer_category_from_heading(heading: str) -> RequirementCategory | None:
    """Infer the requirement category from a markdown heading.

    Searches for category keywords in the heading text and returns
    the corresponding RequirementCategory enum value.

    Args:
        heading: Markdown heading line (starts with #).

    Returns:
        The inferred RequirementCategory, or None if no match found.
    """
    # Remove # characters and lowercase for matching
    heading_text = heading.lstrip("#").strip().lower()

    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in heading_text:
            return category

    return None


__all__ = [
    "parse_requirements",
]
