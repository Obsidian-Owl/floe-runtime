/**
 * Sample Cube.js schema for E2E testing
 *
 * This schema demonstrates how Cube connects to Iceberg tables via Trino.
 * It provides a semantic layer over the raw Iceberg data.
 *
 * In production, floe-cube will generate these schemas from CompiledArtifacts.
 *
 * Table schema (created by cube-init):
 *   - id: BIGINT (primary key)
 *   - customer_id: BIGINT
 *   - status: VARCHAR ('pending', 'processing', 'completed', 'cancelled')
 *   - region: VARCHAR ('north', 'south', 'east', 'west')
 *   - amount: DECIMAL(10,2)
 *   - created_at: TIMESTAMP
 */

cube(`Orders`, {
  // Query the Iceberg table via Trino
  sql: `SELECT * FROM iceberg.default.orders`,

  // Pre-aggregations for performance
  // Using external: false stores in Trino/Iceberg instead of requiring GCS bucket
  // This enables pre-aggregation testing without cloud storage dependencies
  preAggregations: {
    // Base materialization of the source query (stored in Trino)
    base: {
      type: `originalSql`,
      external: false,
    },
    // Rollup pre-aggregation using the base (also stored in Trino)
    ordersByDay: {
      measures: [CUBE.count, CUBE.totalAmount],
      dimensions: [CUBE.status],
      timeDimension: CUBE.createdAt,
      granularity: `day`,
      external: false,
      useOriginalSqlPreAggregations: true,
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
    region: {
      sql: `region`,
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
