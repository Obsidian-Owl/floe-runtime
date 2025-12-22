-- Intermediate model: Customer orders aggregated
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Gold layer)

{{
    config(
        materialized='table',
        tags=['intermediate', 'customers', 'orders']
    )
}}

with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

-- Calculate order-level metrics
order_metrics as (
    select
        order_id,
        count(*) as item_count,
        sum(line_total) as calculated_total
    from order_items
    group by order_id
),

-- Aggregate customer order history
customer_order_history as (
    select
        c.customer_id,
        c.email,
        c.name as customer_name,
        c.created_at as customer_created_at,

        -- Order counts
        count(distinct o.order_id) as total_orders,
        count(distinct case when o.status = 'completed' then o.order_id end) as completed_orders,
        count(distinct case when o.status = 'pending' then o.order_id end) as pending_orders,
        count(distinct case when o.status = 'cancelled' then o.order_id end) as cancelled_orders,

        -- Revenue metrics
        sum(case when o.status = 'completed' then o.total_amount else 0 end) as total_revenue,
        avg(case when o.status = 'completed' then o.total_amount end) as avg_order_value,

        -- Items metrics
        sum(om.item_count) as total_items_ordered,

        -- Dates
        min(o.order_date) as first_order_date,
        max(o.order_date) as last_order_date,

        -- Metadata
        current_timestamp as _loaded_at
    from customers c
    left join orders o on c.customer_id = o.customer_id
    left join order_metrics om on o.order_id = om.order_id
    group by
        c.customer_id,
        c.email,
        c.name,
        c.created_at
)

select * from customer_order_history
