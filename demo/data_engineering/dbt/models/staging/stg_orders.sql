{{
  config(
    materialized='view',
    schema='silver',
    tags=['staging', 'silver', 'orders']
  )
}}

-- Staging: Clean and standardize order data from bronze layer
-- Transformations:
--   - Deduplicate by order_id
--   - Normalize status values
--   - Ensure total_amount >= 0
--   - Cast timestamps

with source as (
    select * from {{ iceberg_source('demo', 'bronze_orders') }}
),

cleaned as (
    select
        order_id,
        customer_id,
        lower(trim(status)) as status,
        region,
        total_amount,
        created_at,
        row_number() over (partition by order_id order by created_at desc) as rn
    from source
    where order_id is not null
      and customer_id is not null
      and total_amount >= 0
),

final as (
    select
        order_id,
        customer_id,
        case
            when status in ('completed', 'complete') then 'completed'
            when status in ('pending', 'processing') then 'pending'
            when status in ('cancelled', 'canceled') then 'cancelled'
            when status in ('failed', 'error') then 'failed'
            else 'unknown'
        end as status,
        region,
        cast(total_amount as decimal(10,2)) as total_amount,
        cast(created_at as timestamp) as created_at
    from cleaned
    where rn = 1
)

select * from final
