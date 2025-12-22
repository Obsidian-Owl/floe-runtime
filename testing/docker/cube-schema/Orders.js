/**
 * Orders Cube schema for production-quality demo
 *
 * This schema demonstrates how Cube connects to Iceberg tables via Trino
 * with external pre-aggregations stored in Cube Store + LocalStack S3.
 *
 * The demo uses production-like architecture:
 * - Cube Store cluster (router + workers) for pre-aggregation compute
 * - S3-compatible storage (LocalStack) for pre-aggregation data
 * - External pre-aggregations for realistic query performance
 *
 * Table schema (populated by demo pipeline):
 *   - id: BIGINT (primary key)
 *   - customer_id: BIGINT
 *   - status: VARCHAR ('pending', 'processing', 'shipped', 'delivered', 'cancelled')
 *   - region: VARCHAR
 *   - amount: DOUBLE
 *   - created_at: TIMESTAMP
 *
 * Covers: 007-FR-029 (E2E validation tests)
 * Covers: 007-FR-031 (Medallion architecture demo)
 */

cube(`Orders`, {
  // Query the bronze layer Iceberg table via Trino
  sql: `SELECT * FROM iceberg.default.bronze_orders`,

  // Pre-aggregations using internal storage (Trino)
  // Note: External pre-aggregations (Cube Store + S3) are production-recommended but
  // require real AWS S3 or compatible storage. LocalStack has XML response compatibility
  // issues with Cube Store's Rust AWS SDK. See: https://github.com/localstack/localstack/issues/7541
  preAggregations: {
    // Daily order rollup - stored in Trino
    ordersByDay: {
      measures: [CUBE.count, CUBE.totalAmount, CUBE.averageAmount],
      dimensions: [CUBE.status],
      timeDimension: CUBE.createdAt,
      granularity: `day`,
      external: false,  // Internal storage via Trino (LocalStack S3 not compatible)
      refreshKey: {
        every: `1 hour`,
      },
    },
    // Weekly summary for trend analysis
    ordersByWeek: {
      measures: [CUBE.count, CUBE.totalAmount],
      dimensions: [CUBE.status],
      timeDimension: CUBE.createdAt,
      granularity: `week`,
      external: false,  // Internal storage via Trino
      refreshKey: {
        every: `6 hours`,
      },
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
    minAmount: {
      sql: `amount`,
      type: `min`,
    },
    maxAmount: {
      sql: `amount`,
      type: `max`,
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
