"""Scanner for discovering tests with requirement markers.

This module provides functionality to scan test directories and discover
tests that have @pytest.mark.requirement or @pytest.mark.requirements markers.

Functions:
    scan_tests: Scan directories for tests with requirement markers

Usage:
    from testing.traceability.scanner import scan_tests

    tests = scan_tests([Path("packages/floe-polaris/tests/integration/")])
    for test in tests:
        print(f"{test.function_name} covers {test.requirement_ids}")

See Also:
    testing.traceability.models for Test model definition
    testing.traceability.parser for requirement extraction
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
import re

from testing.traceability.models import Test, TestMarker

logger = logging.getLogger(__name__)


def scan_tests(test_dirs: list[Path]) -> list[Test]:
    """Scan directories for tests with requirement markers.

    Recursively scans directories for Python test files (test_*.py) and
    extracts test functions/methods decorated with @pytest.mark.requirement
    or @pytest.mark.requirements markers.

    Args:
        test_dirs: List of directory paths to scan.

    Returns:
        List of Test objects representing discovered tests.
        Returns empty list if no tests with requirement markers are found.

    Example:
        >>> from pathlib import Path
        >>> tests = scan_tests([Path("packages/floe-polaris/tests/integration/")])
        >>> for test in tests:
        ...     print(f"{test.function_name}: {test.requirement_ids}")
        test_create_namespace: ['FR-012']
    """
    tests: list[Test] = []

    for test_dir in test_dirs:
        if not test_dir.exists():
            logger.debug("Directory does not exist, skipping: %s", test_dir)
            continue

        # Find all test files recursively
        for test_file in test_dir.rglob("test_*.py"):
            file_tests = _scan_file(test_file)
            tests.extend(file_tests)

    return tests


def _scan_file(file_path: Path) -> list[Test]:
    """Scan a single test file for tests with requirement markers.

    Args:
        file_path: Path to the Python test file.

    Returns:
        List of Test objects found in the file.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        logger.warning("Syntax error in %s: %s", file_path, e)
        return []

    tests: list[Test] = []
    package = _infer_package(file_path)

    # Scan class methods
    tests.extend(_scan_class_methods(tree, file_path, package))

    # Scan module-level test functions
    tests.extend(_scan_module_functions(tree, file_path, package))

    return tests


def _scan_class_methods(tree: ast.Module, file_path: Path, package: str) -> list[Test]:
    """Extract tests from class methods in an AST tree."""
    tests: list[Test] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        class_name = node.name
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                test = _extract_test_from_function(item, file_path, package, class_name=class_name)
                if test is not None:
                    tests.append(test)
    return tests


def _scan_module_functions(tree: ast.Module, file_path: Path, package: str) -> list[Test]:
    """Extract tests from module-level functions in an AST tree."""
    tests: list[Test] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test = _extract_test_from_function(node, file_path, package, class_name=None)
            if test is not None:
                tests.append(test)
    return tests


def _extract_test_from_function(
    node: ast.FunctionDef,
    file_path: Path,
    package: str,
    class_name: str | None = None,
) -> Test | None:
    """Extract Test object from a function definition node.

    Args:
        node: AST node for the function definition.
        file_path: Path to the source file.
        package: Package name.
        class_name: Name of containing class, if any.

    Returns:
        Test object if function has requirement markers, None otherwise.
    """
    requirement_ids: list[str] = []
    markers: list[TestMarker] = []

    for decorator in node.decorator_list:
        req_ids, marker = _process_decorator(decorator)
        requirement_ids.extend(req_ids)
        if marker is not None:
            markers.append(marker)

    if not requirement_ids:
        return None

    return Test(
        file_path=str(file_path),
        function_name=node.name,
        class_name=class_name,
        markers=markers,
        requirement_ids=requirement_ids,
        package=package,
    )


def _process_decorator(decorator: ast.expr) -> tuple[list[str], TestMarker | None]:
    """Process a single decorator and extract requirement IDs and markers.

    Returns:
        Tuple of (requirement_ids, optional marker).
    """
    requirement_ids: list[str] = []
    marker: TestMarker | None = None

    if isinstance(decorator, ast.Call):
        requirement_ids, marker = _process_call_decorator(decorator)
    elif isinstance(decorator, ast.Attribute):
        marker = _marker_name_to_enum(decorator.attr)

    return requirement_ids, marker


def _process_call_decorator(decorator: ast.Call) -> tuple[list[str], TestMarker | None]:
    """Process a decorator call (e.g., @pytest.mark.requirement("FR-001"))."""
    requirement_ids: list[str] = []
    marker: TestMarker | None = None

    marker_name = _get_marker_name(decorator.func)
    if marker_name == "requirement":
        req_id = _extract_string_arg(decorator)
        if req_id:
            requirement_ids.append(req_id)
    elif marker_name == "requirements":
        requirement_ids.extend(_extract_list_arg(decorator))
    elif marker_name in ("integration", "e2e", "slow", "requires_docker"):
        marker = _marker_name_to_enum(marker_name)

    return requirement_ids, marker


def _get_marker_name(node: ast.expr) -> str | None:
    """Extract marker name from decorator expression.

    Handles patterns like:
    - pytest.mark.requirement
    - mark.requirement
    """
    if isinstance(node, ast.Attribute):
        # Check for pytest.mark.X pattern
        if node.attr in (
            "requirement",
            "requirements",
            "integration",
            "e2e",
            "slow",
            "requires_docker",
        ):
            return node.attr
        # Check for nested attribute (pytest.mark.X)
        if isinstance(node.value, ast.Attribute) and node.value.attr == "mark":
            return node.attr
    return None


def _extract_string_arg(call: ast.Call) -> str | None:
    """Extract string argument from a decorator call."""
    if call.args and isinstance(call.args[0], ast.Constant):
        value = call.args[0].value
        if isinstance(value, str):
            return value
    return None


def _extract_list_arg(call: ast.Call) -> list[str]:
    """Extract list of strings from a decorator call."""
    result: list[str] = []
    if call.args and isinstance(call.args[0], ast.List):
        for elt in call.args[0].elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                result.append(elt.value)
    return result


def _marker_name_to_enum(name: str) -> TestMarker | None:
    """Convert marker name string to TestMarker enum."""
    mapping = {
        "integration": TestMarker.INTEGRATION,
        "e2e": TestMarker.E2E,
        "slow": TestMarker.SLOW,
        "requires_docker": TestMarker.REQUIRES_DOCKER,
    }
    return mapping.get(name)


def _infer_package(file_path: Path) -> str:
    """Infer package name from file path.

    Looks for patterns like packages/<package-name>/tests/.

    Args:
        file_path: Path to the test file.

    Returns:
        Package name if found, "unknown" otherwise.
    """
    path_str = str(file_path)

    # Match packages/<package-name>/tests/ pattern
    match = re.search(r"packages/([^/]+)/tests/", path_str)
    if match:
        return match.group(1)

    return "unknown"


__all__ = [
    "scan_tests",
]
