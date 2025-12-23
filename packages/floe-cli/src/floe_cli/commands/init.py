"""floe init command - Scaffold a new project.

T031-T036: Implement init command with template rendering
"""

from __future__ import annotations

from pathlib import Path

import click

from floe_cli.output import error, success, warning


@click.command()
@click.option(
    "-n",
    "--name",
    "name",
    type=str,
    default=None,
    help="Project name [default: current directory name]",
)
@click.option(
    "-t",
    "--target",
    "target",
    type=click.Choice(
        ["duckdb", "snowflake", "bigquery", "redshift", "databricks", "postgres", "spark"]
    ),
    default="duckdb",
    help="Informational: suggested compute type (Two-Tier uses profiles)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing files",
)
def init(name: str | None, target: str, force: bool) -> None:
    """Scaffold a new floe project.

    Creates a new project with a floe.yaml configuration file
    and README documentation.

    Examples:

        floe init

        floe init --name my-pipeline

        floe init --target snowflake

        floe init --force
    """
    # Default name to current directory name
    if name is None:
        name = Path.cwd().name

    # Check for existing floe.yaml
    floe_yaml_path = Path("floe.yaml")
    if floe_yaml_path.exists() and not force:
        error("floe.yaml already exists.")
        error("Use --force to overwrite.")
        raise SystemExit(1)

    try:
        # Import Jinja2 for templating
        from jinja2.sandbox import SandboxedEnvironment

        # Validate project name (basic alphanumeric check)
        if not name.replace("-", "").replace("_", "").isalnum():
            error(f"Invalid project name: {name}")
            error("Project name must be alphanumeric (hyphens and underscores allowed).")
            raise SystemExit(1)

        # Create template environment
        env = SandboxedEnvironment(
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Render floe.yaml (Two-Tier Architecture)
        # In Two-Tier Architecture:
        # - storage/catalog/compute are logical profile references
        # - Actual infrastructure is defined in platform.yaml
        floe_yaml_template = """\
# {{ name }} - Floe Pipeline Configuration
# yaml-language-server: $schema=./schemas/floe.schema.json
#
# Two-Tier Architecture: This file defines WHAT your pipeline does.
# Infrastructure details (endpoints, credentials) go in platform.yaml.

name: {{ name }}
version: "1.0.0"

# Logical profile references (resolved from platform.yaml at runtime)
storage: default
catalog: default
compute: default

transforms:
  - type: dbt
    path: ./dbt

governance:
  classification_source: dbt_meta
  emit_lineage: true

observability:
  traces: true
  metrics: true
  lineage: true
"""

        floe_yaml_content = env.from_string(floe_yaml_template).render(
            name=name,
            target=target,
        )

        # Render README.md (Two-Tier Architecture)
        readme_template = """\
# {{ name }}

A data pipeline built with [Floe Runtime](https://github.com/your-org/floe-runtime).

## Getting Started

1. Validate your configuration:
   ```bash
   floe validate
   ```

2. Compile to artifacts:
   ```bash
   floe compile
   ```

3. Run the pipeline:
   ```bash
   floe run
   ```

## Configuration

This project uses the **Two-Tier Architecture**:

- **floe.yaml**: Defines WHAT your pipeline does (transforms, governance)
- **platform.yaml**: Defines WHERE it runs (endpoints, credentials)

Edit `floe.yaml` to configure your pipeline logic:
- **transforms**: dbt models
- **governance**: Data classification
- **observability**: Tracing and metrics

Your platform engineer provides `platform.yaml` with infrastructure details.

## Learn More

- [Floe Documentation](https://github.com/your-org/floe-runtime)
- [dbt Documentation](https://docs.getdbt.com/)
"""

        readme_content = env.from_string(readme_template).render(
            name=name,
            target=target,
        )

        # Write files
        floe_yaml_path.write_text(floe_yaml_content)

        readme_path = Path("README.md")
        if not readme_path.exists() or force:
            readme_path.write_text(readme_content)

        if force and floe_yaml_path.exists():
            warning("Overwrote existing floe.yaml")

        success(f"Created project: {name}")

    except PermissionError:
        error("Cannot write to current directory.")
        raise SystemExit(2) from None

    except Exception as e:
        error(f"Failed to create project: {e}")
        raise SystemExit(1) from None
