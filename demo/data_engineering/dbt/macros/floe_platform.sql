{% macro floe_resolve_catalog_namespace(schema_name) %}
  {#
    Platform macro: Resolve logical schema to catalog namespace.

    Maps data engineer's logical schema (bronze/silver/gold) to physical
    catalog namespace path. Configuration injected by DbtProfilesGenerator
    from platform.yaml.

    Args:
        schema_name: Logical schema from model config (e.g., 'gold')

    Returns:
        Catalog namespace path (e.g., 'polaris_catalog.demo.gold')

    Example:
        {{ floe_resolve_catalog_namespace('gold') }}
        → 'polaris_catalog.demo.gold'

    Architecture:
        platform.yaml → DbtProfilesGenerator → profiles.yml (dbt vars)
                     → this macro → catalog namespace
  #}
  {% set catalog_mappings = var('floe_catalog_mappings', {}) %}
  {% set catalog_namespace = catalog_mappings.get(schema_name) %}

  {% if not catalog_namespace %}
    {{ exceptions.raise_compiler_error(
        "No catalog mapping for schema '" ~ schema_name ~ "'. " ~
        "Available schemas: " ~ catalog_mappings.keys() | join(", ") ~ ". " ~
        "Check platform.yaml configuration."
    ) }}
  {% endif %}

  {{ return(catalog_namespace) }}
{% endmacro %}


{% macro floe_resolve_table_location(schema_name, table_name) %}
  {#
    Platform macro: Resolve table S3 location from storage mapping.

    Maps schema to S3 bucket/path using platform.yaml storage profiles.
    Ensures data engineers NEVER hardcode infrastructure.

    Args:
        schema_name: Logical schema (e.g., 'gold')
        table_name: Table name (e.g., 'mart_customers')

    Returns:
        S3 location path (e.g., 's3://iceberg-gold/demo/gold/mart_customers')

    Example:
        {{ floe_resolve_table_location('gold', 'mart_revenue') }}
        → 's3://iceberg-gold/demo/gold/mart_revenue'

    Architecture:
        platform.yaml:storage:gold:bucket → DbtProfilesGenerator
                     → profiles.yml (dbt vars) → this macro → S3 location
  #}
  {% set storage_mappings = var('floe_storage_mappings', {}) %}
  {% set storage_config = storage_mappings.get(schema_name) %}

  {% if not storage_config %}
    {{ exceptions.raise_compiler_error(
        "No storage mapping for schema '" ~ schema_name ~ "'. " ~
        "Available schemas: " ~ storage_mappings.keys() | join(", ") ~ ". " ~
        "Check platform.yaml storage configuration."
    ) }}
  {% endif %}

  {% set bucket = storage_config.get('bucket', 'iceberg-data') %}
  {% set location = "s3://" ~ bucket ~ "/demo/" ~ schema_name ~ "/" ~ table_name %}

  {{ return(location) }}
{% endmacro %}


{% macro floe_is_catalog_attached() %}
  {#
    Platform macro: Check if Polaris catalog is attached to DuckDB.

    Returns:
        Boolean indicating if catalog is available for native writes

    Used by materialization to determine if native writes are possible.
  #}
  {% set catalog_mappings = var('floe_catalog_mappings', {}) %}
  {{ return(catalog_mappings | length > 0) }}
{% endmacro %}
