"""Dockerfile validation tests.

These tests verify that production Dockerfiles follow security and best practices.

Covers:
- 007-FR-003: Production Dockerfiles with multi-stage builds
- 007-FR-004: Dockerfile security requirements (non-root user, no secrets)
- 007-FR-006: Dagster container multi-stage build

Requirements:
- Dockerfiles must exist in docker/ directory
- Tests validate structure before building

Run with:
    pytest testing/tests/test_dockerfiles.py -v
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

# Path to docker directory relative to repo root
DOCKER_DIR = Path(__file__).parent.parent.parent / "docker"


class DockerfileValidator:
    """Validates Dockerfile content against requirements."""

    def __init__(self, dockerfile_path: Path) -> None:
        """Initialize validator with Dockerfile path.

        Args:
            dockerfile_path: Path to the Dockerfile
        """
        self.path = dockerfile_path
        if not self.path.exists():
            raise FileNotFoundError(f"Dockerfile not found: {self.path}")
        self.content = self.path.read_text()
        self.lines = self.content.splitlines()

    def has_multi_stage_build(self) -> bool:
        """Check if Dockerfile uses multi-stage build pattern.

        Returns:
            True if Dockerfile has multiple FROM statements with AS clause
        """
        from_pattern = re.compile(r"^FROM\s+.+\s+AS\s+\w+", re.IGNORECASE)
        matches = [line for line in self.lines if from_pattern.match(line.strip())]
        return len(matches) >= 2

    def has_non_root_user(self) -> bool:
        """Check if Dockerfile creates and uses non-root user.

        Returns:
            True if USER statement switches to non-root user
        """
        user_pattern = re.compile(r"^USER\s+(?!root)(\w+)", re.IGNORECASE)
        return any(user_pattern.match(line.strip()) for line in self.lines)

    def has_useradd_for_user(self, username: str) -> bool:
        """Check if Dockerfile creates specified user.

        Args:
            username: Name of user to check for

        Returns:
            True if useradd or adduser creates the user
        """
        useradd_pattern = re.compile(rf"(useradd|adduser).+{username}", re.IGNORECASE)
        return any(useradd_pattern.search(line) for line in self.lines)

    def uses_slim_base(self) -> bool:
        """Check if Dockerfile uses slim Python base image.

        Returns:
            True if base image is python:X.XX-slim
        """
        slim_pattern = re.compile(r"^FROM\s+python:\d+\.\d+-slim", re.IGNORECASE)
        return any(slim_pattern.match(line.strip()) for line in self.lines)

    def has_no_secret_keywords(self) -> list[str]:
        """Check for hardcoded secrets or sensitive patterns.

        Returns:
            List of lines containing potential secrets (should be empty)
        """
        # Patterns that might indicate hardcoded secrets
        secret_patterns = [
            r"password\s*=\s*['\"]",
            r"api_key\s*=\s*['\"]",
            r"secret\s*=\s*['\"]",
            r"token\s*=\s*['\"]",
        ]
        combined_pattern = re.compile("|".join(secret_patterns), re.IGNORECASE)

        violations = []
        for i, line in enumerate(self.lines, 1):
            # Skip comments
            if line.strip().startswith("#"):
                continue
            if combined_pattern.search(line):
                violations.append(f"Line {i}: {line.strip()}")
        return violations

    def has_apt_cleanup(self) -> bool:
        """Check if apt-get commands include cleanup.

        Returns:
            True if apt-get install is followed by cleanup
        """
        content = self.content
        if "apt-get install" not in content:
            return True  # No apt-get install, no cleanup needed

        # Check for rm -rf /var/lib/apt/lists/* pattern
        return "rm -rf /var/lib/apt/lists/*" in content

    def copies_from_builder(self) -> bool:
        """Check if production stage copies from builder.

        Returns:
            True if COPY --from=builder pattern is used
        """
        return "--from=builder" in self.content or "--from=build" in self.content

    def has_workdir(self) -> bool:
        """Check if WORKDIR is set.

        Returns:
            True if WORKDIR instruction is present
        """
        return any(line.strip().upper().startswith("WORKDIR") for line in self.lines)


# =============================================================================
# Dagster Dockerfile Tests
# =============================================================================


class TestDagsterDockerfile:
    """Tests for docker/Dockerfile.dagster.

    Covers: 007-FR-003, 007-FR-004, 007-FR-006
    """

    DOCKERFILE_PATH = DOCKER_DIR / "Dockerfile.dagster"

    @pytest.fixture
    def validator(self) -> DockerfileValidator:
        """Create validator for Dagster Dockerfile."""
        if not self.DOCKERFILE_PATH.exists():
            pytest.fail(
                f"Dockerfile not found at {self.DOCKERFILE_PATH}. "
                "Create docker/Dockerfile.dagster first."
            )
        return DockerfileValidator(self.DOCKERFILE_PATH)

    @pytest.mark.requirement("007-FR-003")
    def test_dagster_dockerfile_exists(self) -> None:
        """Dockerfile.dagster exists in docker/ directory.

        Covers: 007-FR-003 (Production Dockerfiles)
        """
        if not self.DOCKERFILE_PATH.exists():
            pytest.fail(
                f"docker/Dockerfile.dagster not found at {self.DOCKERFILE_PATH}. "
                "This is a required production artifact. "
                "Create it following the multi-stage build pattern from research.md."
            )
        assert self.DOCKERFILE_PATH.exists()

    @pytest.mark.requirement("007-FR-006")
    def test_uses_multi_stage_build(self, validator: DockerfileValidator) -> None:
        """Dockerfile uses multi-stage build pattern.

        Covers: 007-FR-006 (Dagster container multi-stage build)
        """
        assert validator.has_multi_stage_build(), (
            "Dockerfile must use multi-stage build pattern with at least 2 stages. "
            "Example: 'FROM python:3.10-slim AS builder' and 'FROM python:3.10-slim AS production'"
        )

    @pytest.mark.requirement("007-FR-006")
    def test_uses_slim_base_image(self, validator: DockerfileValidator) -> None:
        """Dockerfile uses python:X.XX-slim base image.

        Covers: 007-FR-006 (Slim base for smaller image size)
        """
        assert validator.uses_slim_base(), (
            "Dockerfile must use python:X.XX-slim base image. "
            "This reduces image size from ~1GB to ~150MB."
        )

    @pytest.mark.requirement("007-FR-004")
    def test_creates_non_root_user(self, validator: DockerfileValidator) -> None:
        """Dockerfile creates non-root user for security.

        Covers: 007-FR-004 (Dockerfile security requirements)
        """
        assert validator.has_useradd_for_user("dagster"), (
            "Dockerfile must create 'dagster' user with useradd. "
            "Running as root is a security vulnerability."
        )

    @pytest.mark.requirement("007-FR-004")
    def test_switches_to_non_root_user(self, validator: DockerfileValidator) -> None:
        """Dockerfile switches to non-root user.

        Covers: 007-FR-004 (Non-root user requirement)
        """
        assert validator.has_non_root_user(), (
            "Dockerfile must use USER instruction to switch to non-root user. "
            "Add 'USER dagster' before ENTRYPOINT."
        )

    @pytest.mark.requirement("007-FR-004")
    def test_no_hardcoded_secrets(self, validator: DockerfileValidator) -> None:
        """Dockerfile contains no hardcoded secrets.

        Covers: 007-FR-004 (No secrets in build layers)
        """
        violations = validator.has_no_secret_keywords()
        assert len(violations) == 0, (
            "Dockerfile contains potential hardcoded secrets:\n"
            + "\n".join(violations)
            + "\nSecrets must be injected at runtime via environment variables."
        )

    @pytest.mark.requirement("007-FR-006")
    def test_copies_from_builder_stage(self, validator: DockerfileValidator) -> None:
        """Dockerfile copies artifacts from builder stage.

        Covers: 007-FR-006 (Multi-stage build efficiency)
        """
        assert validator.copies_from_builder(), (
            "Dockerfile must copy virtual environment from builder stage. "
            "Use 'COPY --from=builder /app/.venv /app/.venv'"
        )

    @pytest.mark.requirement("007-FR-003")
    def test_apt_cleanup_present(self, validator: DockerfileValidator) -> None:
        """Dockerfile cleans up apt cache.

        Covers: 007-FR-003 (Production Dockerfile best practices)
        """
        assert validator.has_apt_cleanup(), (
            "Dockerfile must clean up apt cache after install. "
            "Add '&& rm -rf /var/lib/apt/lists/*' after apt-get install."
        )

    @pytest.mark.requirement("007-FR-003")
    def test_has_workdir(self, validator: DockerfileValidator) -> None:
        """Dockerfile sets WORKDIR.

        Covers: 007-FR-003 (Production Dockerfile best practices)
        """
        assert validator.has_workdir(), (
            "Dockerfile must set WORKDIR instruction. Typically 'WORKDIR /app'"
        )


# =============================================================================
# Cube Dockerfile Tests (for T012)
# =============================================================================


class TestCubeDockerfile:
    """Tests for docker/Dockerfile.cube.

    Covers: 007-FR-003, 007-FR-004
    """

    DOCKERFILE_PATH = DOCKER_DIR / "Dockerfile.cube"

    @pytest.fixture
    def validator(self) -> DockerfileValidator:
        """Create validator for Cube Dockerfile."""
        if not self.DOCKERFILE_PATH.exists():
            pytest.fail(
                f"Dockerfile not found at {self.DOCKERFILE_PATH}. "
                "Create docker/Dockerfile.cube first."
            )
        return DockerfileValidator(self.DOCKERFILE_PATH)

    @pytest.mark.requirement("007-FR-003")
    def test_cube_dockerfile_exists(self) -> None:
        """Dockerfile.cube exists in docker/ directory.

        Covers: 007-FR-003 (Production Dockerfiles)
        """
        if not self.DOCKERFILE_PATH.exists():
            pytest.fail(
                f"docker/Dockerfile.cube not found at {self.DOCKERFILE_PATH}. "
                "This will be created in T012."
            )
        assert self.DOCKERFILE_PATH.exists()

    @pytest.mark.requirement("007-FR-003")
    def test_uses_multi_stage_build(self, validator: DockerfileValidator) -> None:
        """Cube Dockerfile uses multi-stage build pattern.

        Covers: 007-FR-003 (Production Dockerfiles)
        """
        assert validator.has_multi_stage_build(), "Dockerfile must use multi-stage build pattern."

    @pytest.mark.requirement("007-FR-004")
    def test_creates_non_root_user(self, validator: DockerfileValidator) -> None:
        """Cube Dockerfile creates non-root user.

        Covers: 007-FR-004 (Dockerfile security requirements)
        """
        assert validator.has_useradd_for_user("cube"), (
            "Dockerfile must create 'cube' user for security."
        )

    @pytest.mark.requirement("007-FR-004")
    def test_no_hardcoded_secrets(self, validator: DockerfileValidator) -> None:
        """Cube Dockerfile contains no hardcoded secrets.

        Covers: 007-FR-004 (No secrets in build layers)
        """
        violations = validator.has_no_secret_keywords()
        assert len(violations) == 0, (
            "Dockerfile contains potential hardcoded secrets:\n" + "\n".join(violations)
        )
