/**
 * Customers Cube schema for production-quality demo
 *
 * Demonstrates dimension table modeling with PII classifications.
 * floe-cube uses dbt meta tags to identify PII fields.
 *
 * Table schema (populated by demo pipeline):
 *   - customer_id: BIGINT (primary key)
 *   - name: VARCHAR (PII)
 *   - email: VARCHAR (PII)
 *   - region: VARCHAR ('north', 'south', 'east', 'west')
 *   - created_at: TIMESTAMP
 *
 * Covers: 007-FR-029 (E2E validation tests)
 * Covers: 007-FR-031 (Medallion architecture demo)
 */

cube(`Customers`, {
  // Query the bronze layer Iceberg table via Trino
  sql: `SELECT * FROM iceberg.default.bronze_customers`,

  // Pre-aggregations using internal storage (Trino)
  // See Orders.js for note on LocalStack S3 compatibility
  preAggregations: {
    // Customer counts by region - for dashboards
    customersByRegion: {
      measures: [CUBE.count],
      dimensions: [CUBE.region],
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
  },

  dimensions: {
    customerId: {
      sql: `customer_id`,
      type: `number`,
      primaryKey: true,
    },
    name: {
      sql: `name`,
      type: `string`,
      // PII field - marked for governance tracking
      meta: {
        classification: 'pii',
        pii_type: 'name',
      },
    },
    email: {
      sql: `email`,
      type: `string`,
      // PII field - marked for governance tracking
      meta: {
        classification: 'pii',
        pii_type: 'email',
      },
    },
    region: {
      sql: `region`,
      type: `string`,
    },
    createdAt: {
      sql: `created_at`,
      type: `time`,
    },
  },
});
