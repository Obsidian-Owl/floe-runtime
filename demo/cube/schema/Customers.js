/**
 * Cube Schema: Customers
 *
 * Provides semantic layer over mart_customer_segments dbt model.
 * Exposes customer segmentation and lifetime metrics via Cube APIs.
 *
 * Covers: 007-FR-029 (E2E validation tests)
 * Covers: 007-FR-032 (Cube pre-aggregation refresh)
 */

cube(`Customers`, {
  // Query the dbt mart model via Trino
  sql: `SELECT * FROM ${process.env.FLOE_DEMO_CATALOG || 'floe_demo'}.${process.env.FLOE_DEMO_SCHEMA || 'marts'}.mart_customer_segments`,

  // Pre-aggregations for segment analysis
  preAggregations: {
    // Segment rollup for common queries
    bySegment: {
      measures: [CUBE.count, CUBE.totalRevenue, CUBE.averageOrderValue],
      dimensions: [CUBE.segment, CUBE.churnRisk],
      external: false,
      refreshKey: {
        every: `1 hour`,
      },
    },
  },

  measures: {
    count: {
      type: `count`,
      description: `Total number of customers`,
    },
    totalRevenue: {
      sql: `total_revenue`,
      type: `sum`,
      format: `currency`,
      description: `Lifetime revenue from customers`,
    },
    averageOrderValue: {
      sql: `avg_order_value`,
      type: `avg`,
      format: `currency`,
      description: `Average order value per customer`,
    },
    totalOrders: {
      sql: `total_orders`,
      type: `sum`,
      description: `Total orders across all customers`,
    },
    averageDaysSinceOrder: {
      sql: `days_since_last_order`,
      type: `avg`,
      description: `Average days since last order`,
    },
  },

  dimensions: {
    customerId: {
      sql: `customer_id`,
      type: `number`,
      primaryKey: true,
      description: `Unique customer identifier`,
    },
    customerName: {
      sql: `customer_name`,
      type: `string`,
      description: `Customer full name`,
      meta: {
        classification: 'pii',
        pii_type: 'name',
      },
    },
    email: {
      sql: `email`,
      type: `string`,
      description: `Customer email address`,
      meta: {
        classification: 'pii',
        pii_type: 'email',
      },
    },
    segment: {
      sql: `customer_segment`,
      type: `string`,
      description: `Customer segment (vip, loyal, active, new, never_ordered)`,
    },
    churnRisk: {
      sql: `churn_risk`,
      type: `string`,
      description: `Churn risk level (high, medium, low, unknown)`,
    },
    createdAt: {
      sql: `customer_created_at`,
      type: `time`,
      description: `Customer account creation date`,
    },
    firstOrderDate: {
      sql: `first_order_date`,
      type: `time`,
      description: `Date of customer first order`,
    },
    lastOrderDate: {
      sql: `last_order_date`,
      type: `time`,
      description: `Date of customer most recent order`,
    },
  },
});
