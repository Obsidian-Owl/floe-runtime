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
    help="Compute target [default: duckdb]",
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

        # Render floe.yaml
        floe_yaml_template = """\
# {{ name }} - Floe Pipeline Configuration
# yaml-language-server: $schema=./schemas/floe.schema.json

name: {{ name }}
version: "1.0.0"

compute:
  target: {{ target }}
{% if target == 'duckdb' %}
  properties:
    path: ":memory:"
    threads: 4
{% endif %}

transforms:
  - type: dbt
    path: ./dbt

governance:
  classification_source: dbt_meta
  default_classification: internal

observability:
  tracing_enabled: true
  metrics_enabled: true
"""

        floe_yaml_content = env.from_string(floe_yaml_template).render(
            name=name,
            target=target,
        )

        # Render README.md
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

Edit `floe.yaml` to configure your pipeline:
- **compute**: Target database ({{ target }})
- **transforms**: dbt models
- **governance**: Data classification
- **observability**: Tracing and metrics

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
