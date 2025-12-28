/**
 * Cube Schema: Products
 *
 * Provides semantic layer over mart_product_analytics dbt model.
 * Exposes product performance metrics and rankings via Cube APIs.
 *
 * Covers: 007-FR-029 (E2E validation tests)
 * Covers: 007-FR-032 (Cube pre-aggregation refresh)
 */

cube(`Products`, {
  // Query the dbt mart model via Trino
  sql: `SELECT * FROM ${process.env.FLOE_DEMO_CATALOG || 'floe_demo'}.${process.env.FLOE_DEMO_SCHEMA || 'marts'}.mart_product_analytics`,

  // Pre-aggregations for product analytics
  preAggregations: {
    // Category rollup for common queries
    byCategory: {
      measures: [CUBE.count, CUBE.totalRevenue, CUBE.totalUnitsSold],
      dimensions: [CUBE.category, CUBE.performanceTier],
      external: false,
      refreshKey: {
        every: `1 hour`,
      },
    },
  },

  measures: {
    count: {
      type: `count`,
      description: `Total number of products`,
    },
    totalRevenue: {
      sql: `total_revenue`,
      type: `sum`,
      format: `currency`,
      description: `Total revenue from product sales`,
    },
    totalUnitsSold: {
      sql: `total_units_sold`,
      type: `sum`,
      description: `Total units sold`,
    },
    totalOrders: {
      sql: `total_orders`,
      type: `sum`,
      description: `Total orders containing this product`,
    },
    averageSellingPrice: {
      sql: `avg_selling_price`,
      type: `avg`,
      format: `currency`,
      description: `Average selling price across all orders`,
    },
    averageQuantityPerOrder: {
      sql: `avg_quantity_per_order`,
      type: `avg`,
      description: `Average quantity per order`,
    },
  },

  dimensions: {
    productId: {
      sql: `product_id`,
      type: `number`,
      primaryKey: true,
      description: `Unique product identifier`,
    },
    productName: {
      sql: `product_name`,
      type: `string`,
      description: `Product display name`,
    },
    category: {
      sql: `category`,
      type: `string`,
      description: `Product category`,
    },
    currentPrice: {
      sql: `current_price`,
      type: `number`,
      format: `currency`,
      description: `Current product price`,
    },
    performanceTier: {
      sql: `performance_tier`,
      type: `string`,
      description: `Performance tier (top_performer, good_performer, average, underperformer, no_sales)`,
    },
    revenueRank: {
      sql: `revenue_rank`,
      type: `number`,
      description: `Product ranking by revenue (1 = highest)`,
    },
    categoryRevenueRank: {
      sql: `category_revenue_rank`,
      type: `number`,
      description: `Product ranking within category by revenue`,
    },
    priceVariance: {
      sql: `price_variance_pct`,
      type: `number`,
      description: `Percentage variance between average selling price and current price`,
    },
    firstSaleDate: {
      sql: `first_sale_date`,
      type: `time`,
      description: `Date of first product sale`,
    },
    lastSaleDate: {
      sql: `last_sale_date`,
      type: `time`,
      description: `Date of most recent product sale`,
    },
  },
});
