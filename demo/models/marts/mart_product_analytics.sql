-- Mart model: Product analytics
-- Covers: 007-FR-029 (E2E validation tests)
-- Covers: 007-FR-031 (Medallion architecture - Gold layer)

{{
    config(
        materialized='table',
        tags=['mart', 'products', 'analytics']
    )
}}

with product_performance as (
    select * from {{ ref('int_product_performance') }}
),

-- Rank products and add analytics
product_analytics as (
    select
        product_id,
        product_name,
        category,
        current_price,

        -- Sales metrics
        total_orders,
        total_units_sold,
        completed_units,
        total_revenue,

        -- Averages
        avg_selling_price,
        avg_quantity_per_order,

        -- Price range
        min_selling_price,
        max_selling_price,

        -- Price variance (discount/premium indicator)
        case
            when current_price > 0
            then round((avg_selling_price - current_price) / current_price * 100, 2)
            else 0
        end as price_variance_pct,

        -- Date metrics
        first_sale_date,
        last_sale_date,

        -- Product ranking by revenue
        row_number() over (order by total_revenue desc nulls last) as revenue_rank,
        row_number() over (order by total_units_sold desc nulls last) as units_rank,

        -- Category ranking
        row_number() over (
            partition by category
            order by total_revenue desc nulls last
        ) as category_revenue_rank,

        -- Performance tier
        case
            when total_revenue is null or total_revenue = 0 then 'no_sales'
            when percent_rank() over (order by total_revenue) >= 0.8 then 'top_performer'
            when percent_rank() over (order by total_revenue) >= 0.5 then 'good_performer'
            when percent_rank() over (order by total_revenue) >= 0.2 then 'average'
            else 'underperformer'
        end as performance_tier,

        -- Metadata
        current_timestamp as _loaded_at
    from product_performance
)

select * from product_analytics
