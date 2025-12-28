{#
  Reference a SOURCE table (upstream dependency) via catalog.

  This macro generates catalog-qualified table references for SOURCE tables
  (tables created by upstream pipelines that this pipeline reads from).

  Runtime enforcement: The catalog (Polaris) enforces read permissions when
  DuckDB executes the query. If the service account lacks TABLE_READ_DATA
  permission, the query will fail with a permissions error.

  Args:
    namespace: Source table namespace (e.g., 'demo', 'shared_bronze')
    table_name: Source table name (e.g., 'bronze_customers')

  Returns:
    Catalog-qualified table reference (e.g., 'polaris_catalog.demo.bronze_customers')

  Example:
    with source as (
        select * from {{ iceberg_source('demo', 'bronze_customers') }}
    ),
#}
{% macro iceberg_source(namespace, table_name) %}
  {{ return(resolve_table_reference(namespace, table_name)) }}
{% endmacro %}
