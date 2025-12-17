/**
 * Sample Cube.js schema for E2E testing
 *
 * This schema demonstrates how Cube connects to Iceberg tables via Trino.
 * It provides a semantic layer over the raw Iceberg data.
 *
 * In production, floe-cube will generate these schemas from CompiledArtifacts.
 */

cube(`Orders`, {
  // Query the Iceberg table via Trino
  sql: `SELECT * FROM iceberg.default.orders`,

  // Pre-aggregations for performance (stored in MinIO)
  preAggregations: {
    ordersByDay: {
      measures: [CUBE.count, CUBE.totalAmount],
      dimensions: [CUBE.status],
      timeDimension: CUBE.createdAt,
      granularity: `day`,
    },
  },

  measures: {
    count: {
      type: `count`,
    },
    totalAmount: {
      sql: `amount`,
      type: `sum`,
    },
    averageAmount: {
      sql: `amount`,
      type: `avg`,
    },
  },

  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true,
    },
    status: {
      sql: `status`,
      type: `string`,
    },
    createdAt: {
      sql: `created_at`,
      type: `time`,
    },
    customerId: {
      sql: `customer_id`,
      type: `number`,
    },
  },
});
