/**
 * Cube Schema: Orders
 *
 * Provides semantic layer over mart_revenue dbt model.
 * Exposes order metrics and revenue analytics via Cube APIs.
 *
 * Covers: 007-FR-029 (E2E validation tests)
 * Covers: 007-FR-032 (Cube pre-aggregation refresh)
 */

cube(`Orders`, {
  // Query the dbt mart model via Trino
  sql: `SELECT * FROM ${process.env.FLOE_DEMO_CATALOG || 'floe_demo'}.${process.env.FLOE_DEMO_SCHEMA || 'marts'}.mart_revenue`,

  // Pre-aggregations for performance
  // Using external: false stores in source database for testing
  preAggregations: {
    // Daily rollup for common queries
    ordersByDay: {
      measures: [CUBE.count, CUBE.totalAmount, CUBE.averageOrderValue],
      dimensions: [CUBE.orderDate],
      timeDimension: CUBE.orderDate,
      granularity: `day`,
      external: false,
      refreshKey: {
        every: `1 hour`,
      },
    },
  },

  measures: {
    count: {
      sql: `total_orders`,
      type: `sum`,
      description: `Total number of orders`,
    },
    completedCount: {
      sql: `completed_orders`,
      type: `sum`,
      description: `Number of completed orders`,
    },
    totalAmount: {
      sql: `gross_revenue`,
      type: `sum`,
      format: `currency`,
      description: `Total revenue from completed orders`,
    },
    averageOrderValue: {
      sql: `avg_order_value`,
      type: `avg`,
      format: `currency`,
      description: `Average order value`,
    },
    totalUnitsSold: {
      sql: `total_units_sold`,
      type: `sum`,
      description: `Total product units sold`,
    },
    uniqueProducts: {
      sql: `unique_products_sold`,
      type: `max`,
      description: `Count of unique products sold`,
    },
    uniqueCustomers: {
      sql: `unique_customers`,
      type: `max`,
      description: `Count of unique customers`,
    },
  },

  dimensions: {
    orderDate: {
      sql: `order_date`,
      type: `time`,
      primaryKey: true,
      description: `Date of orders`,
    },
  },
});
