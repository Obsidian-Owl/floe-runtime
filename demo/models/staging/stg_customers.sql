-- Staging model for customers
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Silver layer)

{{
    config(
        materialized='view',
        tags=['staging', 'customers']
    )
}}

with source as (
    select * from {{ source('raw', 'customers') }}
),

staged as (
    select
        -- Primary key
        customer_id,

        -- Attributes
        email,
        name,

        -- Timestamps
        created_at,

        -- Metadata
        current_timestamp as _loaded_at
    from source
)

select * from staged
