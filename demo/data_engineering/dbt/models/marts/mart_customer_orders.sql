{{
  config(
    materialized='table',
    schema='gold',
    polaris_namespace='demo.gold',
    tags=['marts', 'gold', 'customer_analytics']
  )
}}

-- Gold Mart: Customer Order Analytics
-- Aggregates customer order behavior for BI tools
-- Joins: customers + orders + order_items + products

with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

-- Aggregate order items per order
order_aggregates as (
    select
        oi.order_id,
        count(distinct oi.product_id) as product_count,
        sum(oi.quantity) as total_items,
        sum(oi.line_total) as calculated_total
    from order_items oi
    group by oi.order_id
),

-- Join all entities
final as (
    select
        -- Customer dimensions
        c.customer_id,
        c.name as customer_name,
        c.email as customer_email,
        c.region as customer_region,

        -- Order dimensions
        o.order_id,
        o.status as order_status,
        o.region as order_region,
        o.created_at as order_date,

        -- Order metrics
        o.total_amount as order_total,
        coalesce(oa.product_count, 0) as products_in_order,
        coalesce(oa.total_items, 0) as items_in_order,
        coalesce(oa.calculated_total, 0) as calculated_order_total,

        -- Data quality flag
        case
            when abs(o.total_amount - coalesce(oa.calculated_total, 0)) > 0.01
            then true
            else false
        end as has_amount_mismatch

    from customers c
    inner join orders o on c.customer_id = o.customer_id
    left join order_aggregates oa on o.order_id = oa.order_id
)

select * from final
