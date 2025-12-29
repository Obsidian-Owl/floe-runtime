{{
  config(
    materialized='view',
    schema='silver',
    tags=['staging', 'silver', 'order_items']
  )
}}

-- Staging: Clean and standardize order items from bronze layer
-- Transformations:
--   - Deduplicate
--   - Ensure quantity > 0 and price >= 0
--   - Calculate line_total

with source as (
    select * from {{ source('bronze', 'raw_order_items') }}
),

cleaned as (
    select
        order_item_id,
        order_id,
        product_id,
        quantity,
        price,
        created_at,
        row_number() over (partition by order_item_id order by created_at desc) as rn
    from source
    where order_item_id is not null
      and order_id is not null
      and product_id is not null
      and quantity > 0
      and price >= 0
),

final as (
    select
        order_item_id,
        order_id,
        product_id,
        cast(quantity as integer) as quantity,
        cast(price as decimal(10,2)) as price,
        cast(quantity * price as decimal(10,2)) as line_total,
        cast(created_at as timestamp) as created_at
    from cleaned
    where rn = 1
)

select * from final
