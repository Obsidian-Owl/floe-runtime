{{
  config(
    materialized='table',
    schema='gold',
    polaris_namespace='demo.gold',
    tags=['marts', 'gold', 'revenue_analytics']
  )
}}

-- Gold Mart: Revenue Analytics
-- Daily revenue aggregations by region and status
-- Optimized for Cube semantic layer queries

with customer_orders as (
    select * from {{ ref('mart_customer_orders') }}
),

-- Daily revenue by region and status
daily_revenue as (
    select
        cast(order_date as date) as revenue_date,
        order_region as region,
        order_status as status,
        count(distinct order_id) as order_count,
        count(distinct customer_id) as customer_count,
        sum(order_total) as total_revenue,
        avg(order_total) as avg_order_value,
        sum(items_in_order) as total_items_sold,
        sum(products_in_order) as total_products_sold
    from customer_orders
    group by 1, 2, 3
),

-- Final aggregations with time-series analytics
final as (
    select
        dr.revenue_date,
        dr.region,
        dr.status,
        dr.order_count,
        dr.customer_count,
        dr.total_revenue,
        dr.avg_order_value,
        dr.total_items_sold,
        dr.total_products_sold,

        -- Running totals (window functions)
        sum(dr.total_revenue) over (
            partition by dr.region
            order by dr.revenue_date
            rows between unbounded preceding and current row
        ) as cumulative_revenue_by_region,

        -- Week-over-week growth
        lag(dr.total_revenue, 7) over (
            partition by dr.region, dr.status
            order by dr.revenue_date
        ) as revenue_7d_ago,

        case
            when lag(dr.total_revenue, 7) over (
                partition by dr.region, dr.status
                order by dr.revenue_date
            ) > 0
            then (dr.total_revenue - lag(dr.total_revenue, 7) over (
                partition by dr.region, dr.status
                order by dr.revenue_date
            )) / lag(dr.total_revenue, 7) over (
                partition by dr.region, dr.status
                order by dr.revenue_date
            ) * 100
            else null
        end as wow_growth_pct

    from daily_revenue dr
)

select * from final
