{{
  config(
    materialized='view',
    schema='silver',
    tags=['staging', 'silver', 'products']
  )
}}

-- Staging: Clean and standardize product data from bronze layer
-- Transformations:
--   - Deduplicate by product_id
--   - Standardize category names
--   - Ensure price >= 0

with source as (
    select * from {{ source('bronze', 'bronze_products') }}
),

cleaned as (
    select
        product_id,
        name,
        lower(trim(category)) as category,
        price,
        created_at,
        row_number() over (partition by product_id order by created_at desc) as rn
    from source
    where product_id is not null
      and name is not null
      and price >= 0
),

final as (
    select
        product_id,
        trim(name) as name,
        case
            when category = 'electronics' then 'Electronics'
            when category = 'clothing' then 'Clothing'
            when category = 'home' then 'Home & Garden'
            when category = 'sports' then 'Sports & Outdoors'
            when category = 'books' then 'Books'
            else 'Other'
        end as category,
        cast(price as decimal(10,2)) as price,
        cast(created_at as timestamp) as created_at
    from cleaned
    where rn = 1
)

select * from final
