{{
  config(
    materialized='view',
    schema='silver',
    tags=['staging', 'silver', 'customers']
  )
}}

-- Staging: Clean and standardize customer data from bronze layer
-- Transformations:
--   - Deduplicate by customer_id (keep latest by created_at)
--   - Standardize email to lowercase
--   - Cast timestamps
--   - Filter out invalid records

with source as (
    select * from {{ source('bronze', 'raw_customers') }}
),

deduped as (
    select
        customer_id,
        name,
        lower(trim(email)) as email,
        region,
        segment,
        created_at,
        row_number() over (partition by customer_id order by created_at desc) as rn
    from source
    where customer_id is not null
      and email is not null
      and name is not null
),

final as (
    select
        customer_id,
        name,
        email,
        region,
        segment,
        cast(created_at as timestamp) as created_at
    from deduped
    where rn = 1
)

select * from final
