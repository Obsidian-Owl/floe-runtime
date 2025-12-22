-- Staging model for orders
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Silver layer)

{{
    config(
        materialized='view',
        tags=['staging', 'orders']
    )
}}

with source as (
    select * from {{ source('raw', 'orders') }}
),

staged as (
    select
        -- Primary key
        order_id,

        -- Foreign keys
        customer_id,

        -- Attributes
        status,
        total_amount,

        -- Timestamps
        order_date,

        -- Metadata
        current_timestamp as _loaded_at
    from source
)

select * from staged
