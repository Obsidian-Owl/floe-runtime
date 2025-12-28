{% materialization iceberg, adapter='duckdb' %}
  {#
    Custom Iceberg materialization for floe-runtime.

    Enforces catalog control plane architecture:
    • ALL writes go through Polaris catalog (never direct to S3)
    • Storage location resolved from platform.yaml
    • Access control enforced by catalog RBAC
    • All operations audited
    • Environment-portable (same model works local → staging → prod)

    Usage:
      {{ config(
        materialized='iceberg',
        schema='gold',
        tags=['marts']
      ) }}

    Forbidden:
      {{ config(
        materialized='external',     -- Bypasses catalog!
        location='s3://...'          -- Hardcoded infrastructure!
      ) }}

    Architecture:
      1. dbt executes model SQL in DuckDB
      2. Result written to DuckDB table
      3. dbt-duckdb calls plugin.store() automatically
      4. Plugin reads from DuckDB
      5. Plugin writes to Iceberg via Polaris catalog
      6. Catalog vends credentials for S3 write
      7. Catalog updates metadata atomically
  #}

  {%- set target_relation = this -%}
  {%- set existing_relation = load_cached_relation(this) -%}
  {%- set tmp_relation = make_temp_relation(this) -%}

  {{ run_hooks(pre_hooks) }}

  {# Execute the model SQL #}
  {%- call statement('main') -%}
    {{ create_table_as(False, tmp_relation, sql) }}
  {%- endcall -%}

  {#
    At this point, the Polaris plugin's store() method will be called
    automatically by dbt-duckdb. The plugin will:

    1. Read the DuckDB table created above
    2. Resolve storage location from platform.yaml storage_mapping
    3. Register table in Polaris catalog (demo.<schema>.<table>)
    4. Write data to Iceberg using catalog-vended credentials
    5. Update catalog metadata (snapshots, manifests, statistics)

    This ensures ALL writes go through the catalog control plane.
  #}

  {% set target_relation = this.incorporate(type='table') %}

  {% call noop_statement('main', status="CREATE") -%}
    -- Table created via Polaris catalog
  {%- endcall %}

  {{ run_hooks(post_hooks) }}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}
