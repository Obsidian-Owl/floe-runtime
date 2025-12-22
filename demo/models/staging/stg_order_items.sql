-- Staging model for order items (line items)
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Silver layer)

{{
    config(
        materialized='view',
        tags=['staging', 'order_items']
    )
}}

with source as (
    select * from {{ source('raw', 'order_items') }}
),

staged as (
    select
        -- Primary key
        order_item_id,

        -- Foreign keys
        order_id,
        product_id,

        -- Metrics
        quantity,
        unit_price,

        -- Calculated fields
        quantity * unit_price as line_total,

        -- Metadata
        current_timestamp as _loaded_at
    from source
)

select * from staged
