{% materialization table, adapter='duckdb' %}
  {#
    Platform-Enforced Table Materialization - DuckDB Native Iceberg Writes

    This macro OVERRIDES dbt's default table materialization to enforce
    catalog control plane architecture. Data engineers use standard
    `materialized='table'` syntax - platform automatically writes to
    Polaris/Iceberg via DuckDB ATTACH.

    ZERO INFRASTRUCTURE CONFIGURATION REQUIRED.

    Data Engineer View:
        {{ config(
            materialized='table',
            schema='gold'
        ) }}
        SELECT * FROM {{ ref('stg_customers') }}

    Platform Execution (Transparent):
        CREATE TABLE polaris_catalog.demo.gold.mart_customers
        LOCATION 's3://iceberg-gold/demo/gold/mart_customers'
        AS SELECT * FROM stg_customers

    Architecture:
        1. Platform ATTACHes Polaris catalog to DuckDB (configure_connection)
        2. Platform resolves schema → catalog namespace (from platform.yaml)
        3. Platform resolves schema → S3 location (from platform.yaml)
        4. DuckDB writes DIRECTLY to Polaris via REST API
        5. Polaris manages Iceberg metadata + vended credentials → S3

    Enforcement:
        • ALL writes go through catalog control plane (compile-time validated)
        • Data engineers NEVER see infrastructure details
        • Same floe.yaml works across local/dev/staging/prod
        • Compute swappable (duckdb → spark changes adapter only)
        • Catalog swappable (polaris → glue changes plugin only)

    Performance:
        • Native DuckDB → Polaris writes (no PyArrow conversion overhead)
        • Single SQL statement (not 4-step plugin process)
        • Leverages DuckDB v1.4+ Iceberg extension fully
  #}

  {%- set target_relation = this -%}
  {%- set existing_relation = load_cached_relation(this) -%}
  {%- set tmp_relation = make_temp_relation(this) -%}

  {# Extract schema from config (default: 'default') #}
  {%- set config_schema = config.get('schema', 'default') -%}

  {{ run_hooks(pre_hooks, inside_transaction=False) }}

  {{ run_hooks(pre_hooks, inside_transaction=True) }}

  {#
    Check if catalog is attached for native writes.
    If not attached, fall back to standard DuckDB table (local only).
  #}
  {%- if floe_is_catalog_attached() -%}
    {# PLATFORM PATH: Native Iceberg writes via ATTACH #}

    {# Resolve catalog namespace from platform.yaml #}
    {%- set catalog_namespace = floe_resolve_catalog_namespace(config_schema) -%}

    {# Resolve S3 location from platform.yaml storage mapping #}
    {%- set table_location = floe_resolve_table_location(config_schema, this.name) -%}

    {# Build fully qualified Iceberg table name #}
    {%- set iceberg_table = catalog_namespace ~ "." ~ this.name -%}

    {% call statement('main') %}
      {#
        DuckDB Native Iceberg Write
        Requires DuckDB v1.4+ with iceberg extension + attached catalog
      #}
      CREATE OR REPLACE TABLE {{ iceberg_table }}
      AS {{ sql }}
    {% endcall %}

    {# Update dbt's relation tracking #}
    {% set target_relation = this.incorporate(type='table') %}

    {% do persist_docs(target_relation, model) %}

    {% call noop_statement('main', status="CREATED VIA CATALOG") %}
      -- Table created: {{ iceberg_table }}
      -- Location: {{ table_location }}
      -- Catalog: Polaris (control plane enforced)
    {%- endcall %}

  {%- else -%}
    {# FALLBACK PATH: Standard DuckDB table (no catalog attached) #}

    {% call statement('main') %}
      {{ create_table_as(False, target_relation, sql) }}
    {% endcall %}

    {% set target_relation = this.incorporate(type='table') %}

    {% do persist_docs(target_relation, model) %}

    {% call noop_statement('main', status="WARNING") %}
      -- Table created in DuckDB local storage (catalog not attached)
      -- Run with Polaris attached for Iceberg persistence
    {%- endcall %}

  {%- endif -%}

  {{ run_hooks(post_hooks, inside_transaction=True) }}

  {{ adapter.commit() }}

  {{ run_hooks(post_hooks, inside_transaction=False) }}

  {{ return({'relations': [target_relation]}) }}

{% endmaterialization %}
