"""floe platform command - Manage platform configuration.

T058: Implement floe platform list-profiles
"""

from __future__ import annotations

import click

from floe_cli.output import error, info, success


@click.group()
def platform() -> None:
    """Manage platform configuration.

    Commands for inspecting and validating platform.yaml configuration.

    **Commands:**

    - `floe platform list-profiles` - List available profiles
    - `floe platform validate` - Validate platform configuration
    """
    pass


@platform.command("list-profiles")
@click.option(
    "-p",
    "--platform-file",
    "platform_file",
    type=click.Path(exists=True),
    default=None,
    help="Path to platform.yaml [default: auto-discover]",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON",
)
def list_profiles(platform_file: str | None, as_json: bool) -> None:
    """List available profiles from platform.yaml.

    Displays all storage, catalog, and compute profiles defined
    in platform configuration.

    Examples:

        floe platform list-profiles

        floe platform list-profiles --platform-file /path/to/platform.yaml

        floe platform list-profiles --json
    """
    try:
        # Import here to avoid heavy imports at CLI startup
        from floe_core.compiler import PlatformResolver

        # Load platform configuration
        if platform_file:
            from pathlib import Path

            platform_spec = PlatformResolver.load_from_file(Path(platform_file))
        else:
            platform_spec = PlatformResolver.load_default()

        if as_json:
            import json

            profiles = {
                "storage": list(platform_spec.storage.keys()),
                "catalogs": list(platform_spec.catalogs.keys()),
                "compute": list(platform_spec.compute.keys()),
            }
            click.echo(json.dumps(profiles, indent=2))
        else:
            info("Available profiles:")
            click.echo()

            # Storage profiles
            click.echo("  Storage:")
            if platform_spec.storage:
                for name in sorted(platform_spec.storage.keys()):
                    profile = platform_spec.storage[name]
                    click.echo(f"    - {name} ({profile.type.value})")
            else:
                click.echo("    (none)")

            click.echo()

            # Catalog profiles
            click.echo("  Catalogs:")
            if platform_spec.catalogs:
                for name in sorted(platform_spec.catalogs.keys()):
                    profile = platform_spec.catalogs[name]
                    click.echo(f"    - {name} ({profile.uri})")
            else:
                click.echo("    (none)")

            click.echo()

            # Compute profiles
            click.echo("  Compute:")
            if platform_spec.compute:
                for name in sorted(platform_spec.compute.keys()):
                    profile = platform_spec.compute[name]
                    click.echo(f"    - {name} ({profile.type.value})")
            else:
                click.echo("    (none)")

        success("Profile listing complete")

    except FileNotFoundError:
        error("No platform configuration found")
        info("Create platform.yaml or set FLOE_PLATFORM_FILE environment variable")
        raise SystemExit(2) from None

    except Exception as e:
        error(f"Failed to list profiles: {e}")
        raise SystemExit(1) from None


@platform.command("validate")
@click.option(
    "-p",
    "--platform-file",
    "platform_file",
    type=click.Path(exists=True),
    default=None,
    help="Path to platform.yaml [default: auto-discover]",
)
def validate_platform(platform_file: str | None) -> None:
    """Validate platform configuration.

    Validates the platform.yaml file for correct syntax and schema.

    Examples:

        floe platform validate

        floe platform validate --platform-file /path/to/platform.yaml
    """
    try:
        # Import here to avoid heavy imports at CLI startup
        from floe_core.compiler import PlatformResolver

        # Load and validate platform configuration
        if platform_file:
            from pathlib import Path

            platform_spec = PlatformResolver.load_from_file(Path(platform_file))
            info(f"Validated: {platform_file}")
        else:
            platform_spec = PlatformResolver.load_default()
            info("Validated platform configuration")

        # Report summary
        click.echo()
        click.echo(f"  Storage profiles: {len(platform_spec.storage)}")
        click.echo(f"  Catalog profiles: {len(platform_spec.catalogs)}")
        click.echo(f"  Compute profiles: {len(platform_spec.compute)}")

        success("Platform configuration is valid")

    except FileNotFoundError:
        error("No platform configuration found")
        info("Create platform.yaml or set FLOE_PLATFORM_FILE environment variable")
        raise SystemExit(2) from None

    except Exception as e:
        error(f"Validation failed: {e}")
        raise SystemExit(1) from None
