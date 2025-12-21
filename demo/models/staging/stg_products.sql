-- Staging model for products
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Silver layer)

{{
    config(
        materialized='view',
        tags=['staging', 'products']
    )
}}

with source as (
    select * from {{ source('raw', 'products') }}
),

staged as (
    select
        -- Primary key
        product_id,

        -- Attributes
        name as product_name,
        category,
        price as current_price,

        -- Metadata
        current_timestamp as _loaded_at
    from source
)

select * from staged
