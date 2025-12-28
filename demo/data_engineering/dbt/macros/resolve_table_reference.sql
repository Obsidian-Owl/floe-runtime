{#
  Resolve catalog-qualified table reference for DuckDB + Iceberg.

  Generates engine-specific syntax for accessing Iceberg tables via catalog.
  For DuckDB with attached Iceberg catalog, uses three-part naming:
    catalog_alias.namespace.table_name

  This macro assumes the catalog has been attached with alias 'polaris_catalog'
  via DuckDB's ATTACH statement (configured in profiles.yml or entrypoint.sh).

  Args:
    namespace: Table namespace (e.g., 'demo', 'shared_bronze')
    table_name: Table name (e.g., 'bronze_customers', 'mart_revenue')

  Returns:
    Fully-qualified table reference (e.g., 'polaris_catalog.demo.bronze_customers')

  Future: This macro will be extended to support other engines:
    - Snowflake: database.schema.table (with catalog integration)
    - Trino: catalog.schema.table (via connector config)
    - BigQuery: project.dataset.table (via external connections)
#}
{% macro resolve_table_reference(namespace, table_name) %}
  {%- set catalog_alias = env_var('FLOE_CATALOG_ALIAS', 'polaris_catalog') -%}
  {{ return(catalog_alias ~ '.' ~ namespace ~ '.' ~ table_name) }}
{% endmacro %}
