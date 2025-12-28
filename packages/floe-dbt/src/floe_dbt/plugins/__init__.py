"""dbt-duckdb plugins for floe-runtime.

This package provides platform-managed dbt-duckdb plugins for integration
with floe-runtime's catalog and storage abstractions.

Plugins:
    - polaris: dbt-duckdb plugin for Polaris/Iceberg external materializations

Example:
    >>> # In generated profiles.yml (via DbtProfilesGenerator)
    >>> # outputs:
    >>> #   dev:
    >>> #     type: duckdb
    >>> #     plugins:
    >>> #       - module: 'floe_dbt.plugins.polaris'
    >>> #         config:
    >>> #           catalog_uri: "{{ env_var('FLOE_CATALOG_URI') }}"
    >>> #           ...
"""
