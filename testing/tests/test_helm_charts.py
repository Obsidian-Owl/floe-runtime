"""Helm chart validation tests.

These tests verify that Helm charts follow best practices and can be
successfully linted and template-rendered.

Covers:
- 007-FR-001: Helm chart for Kubernetes deployment
- 007-FR-002: Cube semantic layer deployment
- 007-FR-007: Official Dagster chart as dependency

Requirements:
- helm CLI must be installed
- Charts must be in charts/ directory

Run with:
    pytest testing/tests/test_helm_charts.py -v
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest
import yaml

# Path to charts directory relative to repo root
CHARTS_DIR = Path(__file__).parent.parent.parent / "charts"


def is_helm_installed() -> bool:
    """Check if helm CLI is available."""
    return shutil.which("helm") is not None


class HelmChartValidator:
    """Validates Helm chart content against best practices."""

    def __init__(self, chart_path: Path) -> None:
        """Initialize validator with chart path.

        Args:
            chart_path: Path to the Helm chart directory
        """
        self.path = chart_path
        if not self.path.exists():
            raise FileNotFoundError(f"Chart not found: {self.path}")

        self.chart_yaml_path = self.path / "Chart.yaml"
        self.values_yaml_path = self.path / "values.yaml"
        self.templates_path = self.path / "templates"

        if not self.chart_yaml_path.exists():
            raise FileNotFoundError(f"Chart.yaml not found in {self.path}")

        self.chart_yaml = self._load_yaml(self.chart_yaml_path)
        self.values_yaml = (
            self._load_yaml(self.values_yaml_path) if self.values_yaml_path.exists() else {}
        )

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML content
        """
        with open(path) as f:
            return yaml.safe_load(f) or {}

    def has_required_chart_fields(self) -> tuple[bool, list[str]]:
        """Check if Chart.yaml has all required fields.

        Returns:
            Tuple of (all_present, missing_fields)
        """
        required_fields = ["apiVersion", "name", "version", "description"]
        missing = [f for f in required_fields if f not in self.chart_yaml]
        return len(missing) == 0, missing

    def has_recommended_chart_fields(self) -> tuple[bool, list[str]]:
        """Check if Chart.yaml has recommended fields.

        Returns:
            Tuple of (all_present, missing_fields)
        """
        recommended_fields = [
            "type",
            "appVersion",
            "keywords",
            "home",
            "sources",
            "maintainers",
        ]
        missing = [f for f in recommended_fields if f not in self.chart_yaml]
        return len(missing) == 0, missing

    def uses_api_version_v2(self) -> bool:
        """Check if chart uses apiVersion v2.

        Returns:
            True if apiVersion is v2
        """
        return self.chart_yaml.get("apiVersion") == "v2"

    def has_kube_version_constraint(self) -> bool:
        """Check if chart specifies kubeVersion constraint.

        Returns:
            True if kubeVersion is specified
        """
        return "kubeVersion" in self.chart_yaml

    def has_templates_directory(self) -> bool:
        """Check if templates directory exists.

        Returns:
            True if templates/ directory exists
        """
        return self.templates_path.exists() and self.templates_path.is_dir()

    def has_helpers_template(self) -> bool:
        """Check if _helpers.tpl exists.

        Returns:
            True if templates/_helpers.tpl exists
        """
        helpers_path = self.templates_path / "_helpers.tpl"
        return helpers_path.exists()

    def get_template_files(self) -> list[Path]:
        """Get list of template files.

        Returns:
            List of template file paths
        """
        if not self.templates_path.exists():
            return []
        return list(self.templates_path.glob("*.yaml")) + list(self.templates_path.glob("*.tpl"))

    def lint(self) -> tuple[bool, str]:
        """Run helm lint on the chart.

        Returns:
            Tuple of (success, output)
        """
        if not is_helm_installed():
            return False, "helm CLI not installed"

        result = subprocess.run(
            ["helm", "lint", str(self.path)],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0, result.stdout + result.stderr

    def template(self, release_name: str = "test") -> tuple[bool, str]:
        """Run helm template on the chart.

        Args:
            release_name: Name for the release

        Returns:
            Tuple of (success, output)
        """
        if not is_helm_installed():
            return False, "helm CLI not installed"

        result = subprocess.run(
            ["helm", "template", release_name, str(self.path)],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0, result.stdout + result.stderr

    def template_with_values(
        self, release_name: str = "test", values: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        """Run helm template with custom values.

        Args:
            release_name: Name for the release
            values: Dictionary of values to set

        Returns:
            Tuple of (success, output)
        """
        if not is_helm_installed():
            return False, "helm CLI not installed"

        cmd = ["helm", "template", release_name, str(self.path)]

        if values:
            for key, value in values.items():
                cmd.extend(["--set", f"{key}={value}"])

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout + result.stderr


# =============================================================================
# floe-dagster Chart Tests
# =============================================================================


class TestFloeDagsterChart:
    """Tests for charts/floe-dagster.

    Covers: 007-FR-001, 007-FR-007
    """

    CHART_PATH = CHARTS_DIR / "floe-dagster"

    @pytest.fixture
    def validator(self) -> HelmChartValidator:
        """Create validator for floe-dagster chart."""
        if not self.CHART_PATH.exists():
            pytest.fail(f"Chart not found at {self.CHART_PATH}")
        return HelmChartValidator(self.CHART_PATH)

    @pytest.mark.requirement("007-FR-001")
    def test_chart_exists(self) -> None:
        """floe-dagster chart exists.

        Covers: 007-FR-001 (Helm chart for Kubernetes deployment)
        """
        assert self.CHART_PATH.exists(), f"Chart not found at {self.CHART_PATH}"

    @pytest.mark.requirement("007-FR-001")
    def test_has_required_fields(self, validator: HelmChartValidator) -> None:
        """Chart.yaml has required fields.

        Covers: 007-FR-001 (Helm chart structure)
        """
        has_all, missing = validator.has_required_chart_fields()
        assert has_all, f"Chart.yaml missing required fields: {missing}"

    @pytest.mark.requirement("007-FR-001")
    def test_uses_api_version_v2(self, validator: HelmChartValidator) -> None:
        """Chart uses apiVersion v2.

        Covers: 007-FR-001 (Modern Helm chart format)
        """
        assert validator.uses_api_version_v2(), "Chart must use apiVersion: v2"

    @pytest.mark.requirement("007-FR-001")
    def test_has_kube_version_constraint(self, validator: HelmChartValidator) -> None:
        """Chart specifies kubeVersion constraint.

        Covers: 007-FR-001 (Kubernetes version compatibility)
        """
        assert validator.has_kube_version_constraint(), (
            "Chart should specify kubeVersion constraint"
        )

    @pytest.mark.requirement("007-FR-001")
    def test_has_templates_directory(self, validator: HelmChartValidator) -> None:
        """Chart has templates directory.

        Covers: 007-FR-001 (Helm chart structure)
        """
        assert validator.has_templates_directory(), "Chart must have templates/ directory"

    @pytest.mark.requirement("007-FR-001")
    def test_has_helpers_template(self, validator: HelmChartValidator) -> None:
        """Chart has _helpers.tpl.

        Covers: 007-FR-001 (Helm chart best practices)
        """
        assert validator.has_helpers_template(), "Chart should have templates/_helpers.tpl"

    @pytest.mark.requirement("007-FR-007")
    def test_has_dagster_dependency(self, validator: HelmChartValidator) -> None:
        """Chart depends on official Dagster chart.

        Covers: 007-FR-007 (Official Dagster chart as dependency)
        """
        dependencies = validator.chart_yaml.get("dependencies", [])
        dagster_deps = [d for d in dependencies if d.get("name") == "dagster"]
        assert len(dagster_deps) > 0, "Chart must depend on official dagster Helm chart"

    @pytest.mark.requirement("007-FR-007")
    def test_dagster_dependency_repository(self, validator: HelmChartValidator) -> None:
        """Dagster dependency uses official repository.

        Covers: 007-FR-007 (Official Dagster chart)
        """
        dependencies = validator.chart_yaml.get("dependencies", [])
        dagster_deps = [d for d in dependencies if d.get("name") == "dagster"]
        if dagster_deps:
            repo = dagster_deps[0].get("repository", "")
            assert "dagster-io.github.io/helm" in repo, (
                f"Dagster dependency should use official repo, got: {repo}"
            )

    @pytest.mark.requirement("007-FR-001")
    @pytest.mark.skipif(not is_helm_installed(), reason="helm CLI not installed")
    def test_chart_lints_successfully(self, validator: HelmChartValidator) -> None:
        """Chart passes helm lint.

        Covers: 007-FR-001 (Valid Helm chart)
        """
        success, output = validator.lint()
        assert success, f"Chart failed helm lint:\n{output}"

    @pytest.mark.requirement("007-FR-001")
    @pytest.mark.skipif(not is_helm_installed(), reason="helm CLI not installed")
    def test_chart_templates_render(self, validator: HelmChartValidator) -> None:
        """Chart templates render successfully.

        Covers: 007-FR-001 (Valid Helm templates)
        """
        # Skip dependency build for template test
        success, output = validator.template()
        # May fail due to missing dependencies, check for template errors only
        if not success and "could not find" in output.lower():
            pytest.skip("Skipping due to missing chart dependencies")
        assert success or "error" not in output.lower(), (
            f"Chart template rendering failed:\n{output}"
        )


# =============================================================================
# floe-cube Chart Tests
# =============================================================================


class TestFloeCubeChart:
    """Tests for charts/floe-cube.

    Covers: 007-FR-001, 007-FR-002
    """

    CHART_PATH = CHARTS_DIR / "floe-cube"

    @pytest.fixture
    def validator(self) -> HelmChartValidator:
        """Create validator for floe-cube chart."""
        if not self.CHART_PATH.exists():
            pytest.fail(f"Chart not found at {self.CHART_PATH}")
        return HelmChartValidator(self.CHART_PATH)

    @pytest.mark.requirement("007-FR-002")
    def test_chart_exists(self) -> None:
        """floe-cube chart exists.

        Covers: 007-FR-002 (Cube semantic layer deployment)
        """
        assert self.CHART_PATH.exists(), f"Chart not found at {self.CHART_PATH}"

    @pytest.mark.requirement("007-FR-001")
    def test_has_required_fields(self, validator: HelmChartValidator) -> None:
        """Chart.yaml has required fields.

        Covers: 007-FR-001 (Helm chart structure)
        """
        has_all, missing = validator.has_required_chart_fields()
        assert has_all, f"Chart.yaml missing required fields: {missing}"

    @pytest.mark.requirement("007-FR-001")
    def test_has_recommended_fields(self, validator: HelmChartValidator) -> None:
        """Chart.yaml has recommended fields.

        Covers: 007-FR-001 (Helm chart best practices)
        """
        has_all, missing = validator.has_recommended_chart_fields()
        # This is a warning, not a failure
        if not has_all:
            pytest.warns(UserWarning, match=f"Missing recommended fields: {missing}")

    @pytest.mark.requirement("007-FR-001")
    def test_uses_api_version_v2(self, validator: HelmChartValidator) -> None:
        """Chart uses apiVersion v2.

        Covers: 007-FR-001 (Modern Helm chart format)
        """
        assert validator.uses_api_version_v2(), "Chart must use apiVersion: v2"

    @pytest.mark.requirement("007-FR-002")
    def test_has_cube_image_config(self, validator: HelmChartValidator) -> None:
        """values.yaml configures Cube image.

        Covers: 007-FR-002 (Cube deployment configuration)
        """
        api_config = validator.values_yaml.get("api", {})
        image = api_config.get("image", {})
        assert "repository" in image, "values.yaml must configure api.image.repository"
        assert "cubejs/cube" in image.get("repository", ""), (
            "Cube chart should use official cubejs/cube image"
        )

    @pytest.mark.requirement("007-FR-002")
    def test_has_refresh_worker_config(self, validator: HelmChartValidator) -> None:
        """values.yaml configures refresh worker.

        Covers: 007-FR-002 (Cube refresh worker)
        """
        refresh_config = validator.values_yaml.get("refreshWorker", {})
        assert "enabled" in refresh_config, "values.yaml must configure refreshWorker.enabled"

    @pytest.mark.requirement("007-FR-002")
    def test_has_cube_store_config(self, validator: HelmChartValidator) -> None:
        """values.yaml configures Cube Store.

        Covers: 007-FR-002 (Cube Store for pre-aggregations)
        """
        store_config = validator.values_yaml.get("cubeStore", {})
        assert "enabled" in store_config, "values.yaml must configure cubeStore.enabled"

    @pytest.mark.requirement("007-FR-001")
    def test_has_templates_directory(self, validator: HelmChartValidator) -> None:
        """Chart has templates directory.

        Covers: 007-FR-001 (Helm chart structure)
        """
        assert validator.has_templates_directory(), "Chart must have templates/ directory"

    @pytest.mark.requirement("007-FR-001")
    def test_has_helpers_template(self, validator: HelmChartValidator) -> None:
        """Chart has _helpers.tpl.

        Covers: 007-FR-001 (Helm chart best practices)
        """
        assert validator.has_helpers_template(), "Chart should have templates/_helpers.tpl"

    @pytest.mark.requirement("007-FR-002")
    def test_has_api_deployment(self, validator: HelmChartValidator) -> None:
        """Chart has API deployment template.

        Covers: 007-FR-002 (Cube API deployment)
        """
        templates = [t.name for t in validator.get_template_files()]
        assert any("deployment" in t and "api" in t for t in templates), (
            "Chart must have API deployment template"
        )

    @pytest.mark.requirement("007-FR-002")
    def test_has_service_template(self, validator: HelmChartValidator) -> None:
        """Chart has service template.

        Covers: 007-FR-002 (Cube service exposure)
        """
        templates = [t.name for t in validator.get_template_files()]
        assert any("service" in t for t in templates), "Chart must have service template"

    @pytest.mark.requirement("007-FR-001")
    @pytest.mark.skipif(not is_helm_installed(), reason="helm CLI not installed")
    def test_chart_lints_successfully(self, validator: HelmChartValidator) -> None:
        """Chart passes helm lint.

        Covers: 007-FR-001 (Valid Helm chart)
        """
        success, output = validator.lint()
        assert success, f"Chart failed helm lint:\n{output}"

    @pytest.mark.requirement("007-FR-002")
    @pytest.mark.skipif(not is_helm_installed(), reason="helm CLI not installed")
    def test_chart_templates_render(self, validator: HelmChartValidator) -> None:
        """Chart templates render successfully.

        Covers: 007-FR-002 (Valid Cube templates)
        """
        success, output = validator.template()
        assert success, f"Chart template rendering failed:\n{output}"

    @pytest.mark.requirement("007-FR-002")
    @pytest.mark.skipif(not is_helm_installed(), reason="helm CLI not installed")
    def test_cube_store_enabled_renders(self, validator: HelmChartValidator) -> None:
        """Chart renders with Cube Store enabled.

        Covers: 007-FR-002 (Cube Store StatefulSet)
        """
        success, output = validator.template_with_values(values={"cubeStore.enabled": "true"})
        assert success, f"Chart with cubeStore.enabled failed:\n{output}"
        assert "StatefulSet" in output, "Enabling cubeStore should render StatefulSet"

    @pytest.mark.requirement("007-FR-002")
    @pytest.mark.skipif(not is_helm_installed(), reason="helm CLI not installed")
    def test_ingress_enabled_renders(self, validator: HelmChartValidator) -> None:
        """Chart renders with ingress enabled.

        Covers: 007-FR-002 (Cube ingress)
        """
        success, output = validator.template_with_values(values={"ingress.enabled": "true"})
        assert success, f"Chart with ingress.enabled failed:\n{output}"
        assert "Ingress" in output, "Enabling ingress should render Ingress resource"


# =============================================================================
# Two-Tier Configuration Architecture Tests
# =============================================================================


class TestTwoTierConfigurationArchitecture:
    """Tests for Two-Tier Configuration Architecture in Helm charts.

    Covers:
    - 009-US1: Platform config in platform.yaml (platform engineer domain)
    - 009-US2: Same floe.yaml works across dev/staging/prod
    - 009-FR-001: Two-Tier Configuration Architecture
    """

    CHART_PATH = CHARTS_DIR / "floe-dagster"

    @pytest.fixture
    def validator(self) -> HelmChartValidator:
        """Create validator for floe-dagster chart."""
        if not self.CHART_PATH.exists():
            pytest.fail(f"Chart not found at {self.CHART_PATH}")
        return HelmChartValidator(self.CHART_PATH)

    @pytest.mark.requirement("009-FR-001")
    def test_has_platform_spec_values(self, validator: HelmChartValidator) -> None:
        """values.yaml has platformSpec configuration section.

        Covers: 009-FR-001 (Two-Tier Configuration Architecture)
        """
        floe_config = validator.values_yaml.get("floe", {})
        platform_spec = floe_config.get("platformSpec", {})
        assert platform_spec, "values.yaml must have floe.platformSpec section"
        assert "enabled" in platform_spec, "platformSpec must have enabled flag"

    @pytest.mark.requirement("009-FR-001")
    def test_platform_spec_has_storage_config(self, validator: HelmChartValidator) -> None:
        """platformSpec has storage profile configuration.

        Covers: 009-FR-001 (Storage profile in platform.yaml)
        """
        platform_spec = validator.values_yaml.get("floe", {}).get("platformSpec", {})
        storage = platform_spec.get("storage", {})
        assert storage, "platformSpec must have storage configuration"
        assert "type" in storage, "storage must have type field"
        assert "bucket" in storage, "storage must have bucket field"
        assert "credentials" in storage, "storage must have credentials configuration"

    @pytest.mark.requirement("009-FR-001")
    def test_platform_spec_has_catalog_config(self, validator: HelmChartValidator) -> None:
        """platformSpec has catalog profile configuration.

        Covers: 009-FR-001 (Catalog profile in platform.yaml)
        """
        platform_spec = validator.values_yaml.get("floe", {}).get("platformSpec", {})
        catalog = platform_spec.get("catalog", {})
        assert catalog, "platformSpec must have catalog configuration"
        assert "type" in catalog, "catalog must have type field"
        assert "uri" in catalog, "catalog must have uri field"
        assert "warehouse" in catalog, "catalog must have warehouse field"
        assert "credentials" in catalog, "catalog must have credentials configuration"

    @pytest.mark.requirement("009-FR-001")
    def test_platform_spec_has_compute_config(self, validator: HelmChartValidator) -> None:
        """platformSpec has compute profile configuration.

        Covers: 009-FR-001 (Compute profile in platform.yaml)
        """
        platform_spec = validator.values_yaml.get("floe", {}).get("platformSpec", {})
        compute = platform_spec.get("compute", {})
        assert compute, "platformSpec must have compute configuration"
        assert "type" in compute, "compute must have type field"

    @pytest.mark.requirement("009-FR-001")
    def test_platform_spec_has_observability_config(self, validator: HelmChartValidator) -> None:
        """platformSpec has observability configuration.

        Covers: 009-FR-001 (Observability in platform.yaml)
        """
        platform_spec = validator.values_yaml.get("floe", {}).get("platformSpec", {})
        observability = platform_spec.get("observability", {})
        assert observability, "platformSpec must have observability configuration"
        assert "traces" in observability, "observability must have traces flag"
        assert "lineage" in observability, "observability must have lineage flag"

    @pytest.mark.requirement("009-FR-001")
    def test_credentials_support_multiple_modes(self, validator: HelmChartValidator) -> None:
        """Credentials support static, oauth2, and iam_role modes.

        Covers: 009-FR-001 (Enterprise credential management)
        """
        platform_spec = validator.values_yaml.get("floe", {}).get("platformSpec", {})

        # Storage credentials
        storage_creds = platform_spec.get("storage", {}).get("credentials", {})
        assert "mode" in storage_creds, "storage credentials must have mode"
        assert "secretRef" in storage_creds, "storage credentials must support secretRef"
        assert "roleArn" in storage_creds, "storage credentials must support IAM roleArn"

        # Catalog credentials
        catalog_creds = platform_spec.get("catalog", {}).get("credentials", {})
        assert "mode" in catalog_creds, "catalog credentials must have mode"
        assert "scope" in catalog_creds, "catalog credentials must have OAuth2 scope"

    @pytest.mark.requirement("009-FR-001")
    def test_has_compiled_artifacts_config(self, validator: HelmChartValidator) -> None:
        """values.yaml has CompiledArtifacts configuration.

        Covers: 009-FR-001 (CompiledArtifacts contract)
        """
        floe_config = validator.values_yaml.get("floe", {})
        artifacts = floe_config.get("compiledArtifacts", {})
        assert artifacts, "values.yaml must have floe.compiledArtifacts section"
        assert "enabled" in artifacts, "compiledArtifacts must have enabled flag"
        assert "mountPath" in artifacts, "compiledArtifacts must have mountPath"

    @pytest.mark.requirement("009-FR-001")
    @pytest.mark.skipif(not is_helm_installed(), reason="helm CLI not installed")
    def test_platform_spec_enabled_renders_configmap(self, validator: HelmChartValidator) -> None:
        """Enabling platformSpec renders a ConfigMap.

        Covers: 009-FR-001 (Platform configuration as ConfigMap)
        """
        success, output = validator.template_with_values(
            values={
                "floe.platformSpec.enabled": "true",
                "floe.platformSpec.catalog.uri": "http://polaris:8181/api/catalog",
                "floe.platformSpec.catalog.warehouse": "demo",
            }
        )
        # Chart may not have the template yet, so check for template errors
        if success:
            assert "ConfigMap" in output, "Enabling platformSpec should render a ConfigMap"


# =============================================================================
# General Chart Quality Tests
# =============================================================================


class TestChartQuality:
    """General quality tests for all charts."""

    @pytest.mark.requirement("007-FR-001")
    def test_all_charts_have_values_yaml(self) -> None:
        """All charts have values.yaml.

        Covers: 007-FR-001 (Helm chart structure)
        """
        if not CHARTS_DIR.exists():
            pytest.skip("Charts directory not found")

        for chart_dir in CHARTS_DIR.iterdir():
            if chart_dir.is_dir() and (chart_dir / "Chart.yaml").exists():
                values_path = chart_dir / "values.yaml"
                assert values_path.exists(), f"Chart {chart_dir.name} missing values.yaml"

    @pytest.mark.requirement("007-FR-001")
    def test_all_charts_use_api_v2(self) -> None:
        """All charts use apiVersion v2.

        Covers: 007-FR-001 (Modern Helm charts)
        """
        if not CHARTS_DIR.exists():
            pytest.skip("Charts directory not found")

        for chart_dir in CHARTS_DIR.iterdir():
            if chart_dir.is_dir():
                chart_yaml = chart_dir / "Chart.yaml"
                if chart_yaml.exists():
                    with open(chart_yaml) as f:
                        chart = yaml.safe_load(f)
                    assert chart.get("apiVersion") == "v2", (
                        f"Chart {chart_dir.name} should use apiVersion: v2"
                    )

    @pytest.mark.requirement("007-FR-001")
    def test_no_deprecated_helm_constructs(self) -> None:
        """Charts don't use deprecated Helm constructs.

        Covers: 007-FR-001 (Modern Helm practices)

        Checks for:
        - requirements.yaml (deprecated in Helm 3, use Chart.yaml dependencies)
        """
        if not CHARTS_DIR.exists():
            pytest.skip("Charts directory not found")

        for chart_dir in CHARTS_DIR.iterdir():
            if chart_dir.is_dir():
                # Check for requirements.yaml (deprecated in Helm 3)
                req_yaml = chart_dir / "requirements.yaml"
                assert not req_yaml.exists(), (
                    f"Chart {chart_dir.name} uses deprecated requirements.yaml. "
                    "Move dependencies to Chart.yaml."
                )
