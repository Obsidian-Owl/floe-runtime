-- Intermediate model: Product performance metrics
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Gold layer)

{{
    config(
        materialized='table',
        tags=['intermediate', 'products']
    )
}}

with products as (
    select * from {{ ref('stg_products') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

-- Join order items with orders to get status
order_items_with_status as (
    select
        oi.*,
        o.status as order_status,
        o.order_date
    from order_items oi
    inner join orders o on oi.order_id = o.order_id
),

-- Calculate product performance metrics
product_performance as (
    select
        p.product_id,
        p.product_name,
        p.category,
        p.current_price,

        -- Sales volume
        count(distinct ois.order_id) as total_orders,
        sum(ois.quantity) as total_units_sold,

        -- Revenue metrics (completed orders only)
        sum(case when ois.order_status = 'completed' then ois.line_total else 0 end) as total_revenue,
        sum(case when ois.order_status = 'completed' then ois.quantity else 0 end) as completed_units,

        -- Average metrics
        avg(ois.unit_price) as avg_selling_price,
        avg(ois.quantity) as avg_quantity_per_order,

        -- Price analysis
        min(ois.unit_price) as min_selling_price,
        max(ois.unit_price) as max_selling_price,

        -- Time analysis
        min(ois.order_date) as first_sale_date,
        max(ois.order_date) as last_sale_date,

        -- Metadata
        current_timestamp as _loaded_at
    from products p
    left join order_items_with_status ois on p.product_id = ois.product_id
    group by
        p.product_id,
        p.product_name,
        p.category,
        p.current_price
)

select * from product_performance
