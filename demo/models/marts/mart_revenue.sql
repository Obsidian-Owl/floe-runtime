-- Mart model: Revenue analytics
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Gold layer)

{{
    config(
        materialized='table',
        tags=['mart', 'revenue', 'analytics']
    )
}}

with orders as (
    select * from {{ ref('stg_orders') }}
),

order_items_enriched as (
    select * from {{ ref('int_order_items_enriched') }}
),

-- Daily revenue aggregation
daily_revenue as (
    select
        o.order_date,

        -- Order counts
        count(distinct o.order_id) as total_orders,
        count(distinct case when o.status = 'completed' then o.order_id end) as completed_orders,
        count(distinct case when o.status = 'pending' then o.order_id end) as pending_orders,
        count(distinct case when o.status = 'cancelled' then o.order_id end) as cancelled_orders,

        -- Revenue metrics
        sum(case when o.status = 'completed' then o.total_amount else 0 end) as gross_revenue,
        avg(case when o.status = 'completed' then o.total_amount end) as avg_order_value,

        -- Items sold
        sum(case when o.status = 'completed' then oie.quantity else 0 end) as total_units_sold,
        count(distinct case when o.status = 'completed' then oie.product_id end) as unique_products_sold,

        -- Unique customers
        count(distinct o.customer_id) as unique_customers,

        -- Metadata
        current_timestamp as _loaded_at
    from orders o
    left join order_items_enriched oie on o.order_id = oie.order_id
    group by o.order_date
)

select * from daily_revenue
order by order_date desc
