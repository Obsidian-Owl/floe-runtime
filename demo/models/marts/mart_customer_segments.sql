-- Mart model: Customer segmentation
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Gold layer)

{{
    config(
        materialized='table',
        tags=['mart', 'customers', 'segmentation']
    )
}}

with customer_orders as (
    select * from {{ ref('int_customer_orders') }}
),

-- Define customer segments based on behavior
customer_segments as (
    select
        customer_id,
        email,
        customer_name,
        customer_created_at,

        -- Order metrics
        total_orders,
        completed_orders,
        pending_orders,
        cancelled_orders,
        total_revenue,
        avg_order_value,
        total_items_ordered,

        -- Date metrics
        first_order_date,
        last_order_date,

        -- Days since last order (null-safe)
        case
            when last_order_date is not null
            then current_date - last_order_date
            else null
        end as days_since_last_order,

        -- Customer lifetime (days)
        case
            when first_order_date is not null and last_order_date is not null
            then last_order_date - first_order_date
            else 0
        end as customer_lifetime_days,

        -- RFM-inspired segmentation
        case
            when total_orders = 0 or total_orders is null then 'never_ordered'
            when total_revenue >= 1000 and completed_orders >= 5 then 'vip'
            when total_revenue >= 500 or completed_orders >= 3 then 'loyal'
            when completed_orders >= 1 then 'active'
            else 'new'
        end as customer_segment,

        -- Churn risk (based on recency)
        case
            when last_order_date is null then 'unknown'
            when current_date - last_order_date > 90 then 'high'
            when current_date - last_order_date > 30 then 'medium'
            else 'low'
        end as churn_risk,

        -- Metadata
        current_timestamp as _loaded_at
    from customer_orders
)

select * from customer_segments
