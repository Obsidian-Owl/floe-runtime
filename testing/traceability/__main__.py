"""CLI entry point for traceability reporting.

Allows running the traceability module as a command:
    python -m testing.traceability --feature-id 006 --spec-files specs/006/spec.md

Usage:
    python -m testing.traceability [OPTIONS]

Options:
    --feature-id        Feature identifier (required)
    --feature-name      Human-readable feature name (required)
    --spec-files        Comma-separated list of spec file paths
    --test-dirs         Comma-separated list of test directory paths
    --format            Output format: console (default) or json
    --threshold         Minimum coverage percentage (0-100), exit 1 if not met
    --help              Show this help message
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from testing.traceability.reporter import (
    format_console_report,
    format_json_report,
    generate_matrix,
)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="python -m testing.traceability",
        description="Generate traceability reports mapping requirements to tests.",
    )

    parser.add_argument(
        "--feature-id",
        required=True,
        help="Feature identifier (e.g., '006')",
    )

    parser.add_argument(
        "--feature-name",
        required=True,
        help="Human-readable feature name",
    )

    parser.add_argument(
        "--spec-files",
        default="",
        help="Comma-separated list of spec file paths",
    )

    parser.add_argument(
        "--test-dirs",
        default="",
        help="Comma-separated list of test directory paths",
    )

    parser.add_argument(
        "--format",
        choices=["console", "json"],
        default="console",
        help="Output format (default: console)",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Minimum coverage percentage (0-100), exit 1 if not met",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for CLI.

    Args:
        args: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parsed = parse_args(args)

    # Parse file paths
    spec_files: list[Path] = []
    if parsed.spec_files:
        spec_files = [Path(p.strip()) for p in parsed.spec_files.split(",")]

    test_dirs: list[Path] = []
    if parsed.test_dirs:
        test_dirs = [Path(p.strip()) for p in parsed.test_dirs.split(",")]

    # Generate matrix
    matrix = generate_matrix(
        feature_id=parsed.feature_id,
        feature_name=parsed.feature_name,
        spec_files=spec_files,
        test_dirs=test_dirs,
    )

    # Output report
    if parsed.format == "json":
        print(format_json_report(matrix))
    else:
        print(format_console_report(matrix))

    # Check threshold
    if parsed.threshold is not None:
        coverage = matrix.get_coverage_percentage()
        if coverage < parsed.threshold:
            print(
                f"\nCoverage {coverage:.1f}% is below threshold {parsed.threshold:.1f}%",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
