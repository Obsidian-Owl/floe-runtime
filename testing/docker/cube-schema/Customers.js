/**
 * Sample Cube.js schema for Customers dimension
 *
 * Demonstrates dimension table modeling with PII classifications.
 * floe-cube will use dbt meta tags to identify PII fields.
 */

cube(`Customers`, {
  sql: `SELECT * FROM iceberg.default.customers`,

  joins: {
    Orders: {
      relationship: `one_to_many`,
      sql: `${CUBE}.id = ${Orders}.customer_id`,
    },
  },

  measures: {
    count: {
      type: `count`,
    },
  },

  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true,
    },
    name: {
      sql: `name`,
      type: `string`,
      // Note: In production, floe-cube would mark this based on dbt meta tags
      meta: {
        classification: 'pii',
        pii_type: 'name',
      },
    },
    email: {
      sql: `email`,
      type: `string`,
      // Note: PII field - would be masked or excluded based on governance rules
      meta: {
        classification: 'pii',
        pii_type: 'email',
      },
    },
    segment: {
      sql: `segment`,
      type: `string`,
    },
    createdAt: {
      sql: `created_at`,
      type: `time`,
    },
  },
});
