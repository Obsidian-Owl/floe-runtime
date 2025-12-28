{{
  config(
    materialized='table',
    schema='gold',
    tags=['marts', 'gold', 'product_analytics']
  )
}}

-- Gold Mart: Product Performance Analytics
-- Platform-managed: Writes to polaris_catalog.demo.gold.mart_product_performance
-- Location resolved from platform.yaml storage.gold profile
-- Product sales metrics aggregated by category and time period

with products as (
    select * from {{ ref('stg_products') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

-- Product sales with order context
product_sales as (
    select
        p.product_id,
        p.name as product_name,
        p.category,
        p.price as list_price,
        oi.order_id,
        oi.quantity,
        oi.price as sold_price,
        oi.line_total,
        o.status as order_status,
        o.created_at as sale_date
    from products p
    inner join order_items oi on p.product_id = oi.product_id
    inner join orders o on oi.order_id = o.order_id
),

-- Aggregate by product
final as (
    select
        product_id,
        product_name,
        category,
        list_price,

        -- Sales metrics
        count(distinct order_id) as orders_with_product,
        sum(quantity) as total_units_sold,
        sum(line_total) as total_revenue,
        avg(sold_price) as avg_selling_price,

        -- Performance indicators
        count(distinct case when order_status = 'completed' then order_id end) as completed_orders,
        sum(case when order_status = 'completed' then line_total else 0 end) as completed_revenue,

        -- Pricing analysis
        min(sold_price) as min_sold_price,
        max(sold_price) as max_sold_price,
        avg(case when sold_price < list_price then list_price - sold_price else 0 end) as avg_discount,

        -- Time dimensions
        min(sale_date) as first_sale_date,
        max(sale_date) as last_sale_date,

        -- Category rank
        row_number() over (partition by category order by sum(line_total) desc) as revenue_rank_in_category

    from product_sales
    group by 1, 2, 3, 4
)

select * from final
