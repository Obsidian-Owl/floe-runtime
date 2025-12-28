{#
  Reference a TARGET table (pipeline output) via catalog.

  This macro generates catalog-qualified table references for TARGET tables
  (tables created/updated by this pipeline's dbt models).

  Runtime enforcement: The catalog (Polaris) enforces write permissions when
  DuckDB attempts to create/update the table. If the service account lacks
  NAMESPACE_CREATE/TABLE_WRITE_DATA permissions, the query will fail.

  Args:
    namespace: Target table namespace (e.g., 'demo', 'shared_gold')
    table_name: Target table name (e.g., 'mart_revenue')

  Returns:
    Catalog-qualified table reference (e.g., 'polaris_catalog.demo.mart_revenue')

  Example:
    {{
      config(
        materialized='external',
        location='s3://temp-dbt/gold/mart_revenue',
        format='parquet',
        polaris_namespace='demo',
        polaris_table='mart_revenue'
      )
    }}

    with source as (
        select * from {{ iceberg_source('demo', 'silver_customers') }}
    ),

    final as (
        select customer_id, sum(revenue) as total_revenue
        from source
        group by 1
    )

    select * from final
#}
{% macro iceberg_target(namespace, table_name) %}
  {{ return(resolve_table_reference(namespace, table_name)) }}
{% endmacro %}
