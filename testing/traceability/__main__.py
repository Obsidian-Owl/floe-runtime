"""CLI entry point for traceability reporting.

Allows running the traceability module as a command:
    python -m testing.traceability --all  # Multi-feature report
    python -m testing.traceability --feature-id 006  # Single feature

Usage:
    python -m testing.traceability [OPTIONS]

Options:
    --all               Generate report for all features (001-006+)
    --feature-id        Feature identifier (required if not --all)
    --feature-name      Human-readable feature name (optional with --feature-id)
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
    FEATURE_NAMES,
    format_console_report,
    format_json_report,
    format_multi_feature_console,
    format_multi_feature_json,
    generate_matrix,
    generate_multi_feature_report,
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

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--all",
        action="store_true",
        help="Generate report for all features (001-006+)",
    )
    mode_group.add_argument(
        "--feature-id",
        help="Feature identifier (e.g., '006')",
    )

    parser.add_argument(
        "--feature-name",
        help="Human-readable feature name (optional, auto-detected from feature-id)",
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

    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory (auto-detected if not specified)",
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

    # Multi-feature mode
    if parsed.all:
        return _run_multi_feature_report(parsed)

    # Single feature mode requires feature-id
    if not parsed.feature_id:
        print(
            "Error: Either --all or --feature-id is required",
            file=sys.stderr,
        )
        return 1

    return _run_single_feature_report(parsed)


def _run_multi_feature_report(parsed: argparse.Namespace) -> int:
    """Run multi-feature report mode.

    Args:
        parsed: Parsed command line arguments.

    Returns:
        Exit code.
    """
    report = generate_multi_feature_report(project_root=parsed.project_root)

    # Output report
    if parsed.format == "json":
        print(format_multi_feature_json(report))
    else:
        print(format_multi_feature_console(report))

    # Check threshold
    if parsed.threshold is not None:
        coverage = report.total_coverage_percentage
        if coverage < parsed.threshold:
            print(
                f"\nCoverage {coverage:.1f}% is below threshold {parsed.threshold:.1f}%",
                file=sys.stderr,
            )
            return 1

    return 0


def _run_single_feature_report(parsed: argparse.Namespace) -> int:
    """Run single feature report mode.

    Args:
        parsed: Parsed command line arguments.

    Returns:
        Exit code.
    """
    # Auto-detect feature name if not provided
    feature_name = parsed.feature_name
    if not feature_name:
        feature_name = FEATURE_NAMES.get(parsed.feature_id, f"Feature {parsed.feature_id}")

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
        feature_name=feature_name,
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
