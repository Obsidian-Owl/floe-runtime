-- Intermediate model: Order items enriched with product details
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Gold layer)

{{
    config(
        materialized='table',
        tags=['intermediate', 'orders']
    )
}}

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

enriched as (
    select
        oi.order_item_id,
        oi.order_id,
        oi.product_id,

        -- Product details
        p.product_name,
        p.category as product_category,
        p.current_price,

        -- Order item metrics
        oi.quantity,
        oi.unit_price,
        oi.line_total,

        -- Calculate margin (if current price differs from order price)
        oi.unit_price - p.current_price as price_difference,

        -- Metadata
        oi._loaded_at
    from order_items oi
    left join products p on oi.product_id = p.product_id
)

select * from enriched
