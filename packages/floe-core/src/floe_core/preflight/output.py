"""Preflight check output formatters.

Rich table and JSON output for preflight check results.

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from floe_core.preflight.models import CheckResult, CheckStatus, PreflightResult


def _status_icon(status: CheckStatus) -> str:
    """Get icon for check status."""
    icons = {
        CheckStatus.PASSED: "✅",
        CheckStatus.FAILED: "❌",
        CheckStatus.WARNING: "⚠️",
        CheckStatus.SKIPPED: "⏭️",
        CheckStatus.ERROR: "💥",
    }
    return icons.get(status, "❓")


def _status_color(status: CheckStatus) -> str:
    """Get color for check status."""
    colors = {
        CheckStatus.PASSED: "green",
        CheckStatus.FAILED: "red",
        CheckStatus.WARNING: "yellow",
        CheckStatus.SKIPPED: "dim",
        CheckStatus.ERROR: "red bold",
    }
    return colors.get(status, "white")


def format_result_table(result: PreflightResult, console: Console | None = None) -> None:
    """Format preflight results as a Rich table.

    Args:
        result: PreflightResult to display
        console: Optional Rich console (creates one if not provided)

    Example:
        >>> result = PreflightResult(checks=[...])
        >>> format_result_table(result)
    """
    if console is None:
        console = Console()

    # Create header panel
    overall_icon = _status_icon(result.overall_status)
    overall_color = _status_color(result.overall_status)
    header_text = Text()
    header_text.append("FLOE PREFLIGHT CHECK REPORT\n\n", style="bold")
    header_text.append(f"Status: {overall_icon} ", style=overall_color)
    header_text.append(result.overall_status.value.upper(), style=f"bold {overall_color}")
    header_text.append(f"\nChecks: {result.passed_count} passed, {result.failed_count} failed")
    if result.total_duration_ms > 0:
        header_text.append(f"\nDuration: {result.total_duration_ms}ms")

    console.print(Panel(header_text, title="[bold]Preflight Results[/bold]"))

    # Create results table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Status", width=3, justify="center")
    table.add_column("Check", min_width=20)
    table.add_column("Message", min_width=30)
    table.add_column("Duration", justify="right", width=10)

    for check in result.checks:
        icon = _status_icon(check.status)
        color = _status_color(check.status)
        duration = f"{check.duration_ms}ms" if check.duration_ms > 0 else "-"

        table.add_row(
            icon,
            Text(check.name, style=color),
            Text(check.message or "-", style="dim" if not check.message else ""),
            duration,
        )

    console.print(table)

    # Show failed check details
    failed_checks = [c for c in result.checks if c.failed]
    if failed_checks:
        console.print()
        console.print("[bold red]Failed Check Details:[/bold red]")
        for check in failed_checks:
            console.print(f"  [red]• {check.name}[/red]: {check.message}")
            if check.details:
                for key, value in check.details.items():
                    console.print(f"    {key}: {value}", style="dim")


def format_result_json(result: PreflightResult, pretty: bool = True) -> str:
    """Format preflight results as JSON.

    Args:
        result: PreflightResult to format
        pretty: Whether to use indentation

    Returns:
        JSON string representation

    Example:
        >>> result = PreflightResult(checks=[...])
        >>> json_str = format_result_json(result)
    """
    data = _result_to_dict(result)
    if pretty:
        return json.dumps(data, indent=2, default=str)
    return json.dumps(data, default=str)


def _result_to_dict(result: PreflightResult) -> dict[str, Any]:
    """Convert PreflightResult to dictionary for JSON serialization."""
    return {
        "status": result.overall_status.value,
        "passed": result.passed,
        "summary": {
            "total": len(result.checks),
            "passed": result.passed_count,
            "failed": result.failed_count,
        },
        "duration_ms": result.total_duration_ms,
        "started_at": result.started_at.isoformat() if result.started_at else None,
        "finished_at": result.finished_at.isoformat() if result.finished_at else None,
        "checks": [_check_to_dict(check) for check in result.checks],
    }


def _check_to_dict(check: CheckResult) -> dict[str, Any]:
    """Convert CheckResult to dictionary for JSON serialization."""
    return {
        "name": check.name,
        "status": check.status.value,
        "passed": check.passed,
        "message": check.message,
        "details": check.details,
        "duration_ms": check.duration_ms,
        "timestamp": check.timestamp.isoformat() if check.timestamp else None,
    }


def print_result(
    result: PreflightResult,
    output_format: str = "table",
    console: Console | None = None,
) -> None:
    """Print preflight results in specified format.

    Args:
        result: PreflightResult to display
        output_format: Output format ("table" or "json")
        console: Optional Rich console

    Example:
        >>> result = PreflightResult(checks=[...])
        >>> print_result(result, output_format="json")
    """
    if console is None:
        console = Console()

    if output_format == "json":
        # Print raw JSON without Rich formatting to ensure parseable output
        json_str = format_result_json(result, pretty=True)
        # Write directly to the console's file to avoid any formatting
        if console.file is not None:
            console.file.write(json_str + "\n")
        else:
            print(json_str)
    else:
        format_result_table(result, console)
