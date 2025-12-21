# Data Model: Deployment Automation

**Feature**: 007-deployment-automation
**Date**: 2025-12-21
**Source**: [spec.md](spec.md)

## Overview

This document defines the data models and entities for the Deployment Automation feature. These models represent configuration, validation, and runtime state for production deployments.

---

## 1. Configuration Entities

### 1.1 PreflightConfig

Configuration for pre-deployment validation checks.

```yaml
Entity: PreflightConfig
Description: Configuration for infrastructure validation before deployment
Attributes:
  - compute_type: enum[trino, snowflake, bigquery, duckdb]
      # The compute engine type to validate
  - compute_host: string (optional)
      # Hostname for the compute engine
  - compute_port: integer (optional)
      # Port for the compute engine
  - storage_type: enum[s3, gcs, adls]
      # Object storage provider
  - storage_bucket: string (optional)
      # Bucket name to validate access
  - catalog_uri: string (optional)
      # Polaris catalog REST API endpoint
  - postgres_host: string (optional)
      # PostgreSQL host for Dagster metadata
  - postgres_port: integer (default: 5432)
      # PostgreSQL port
  - postgres_database: string (optional)
      # PostgreSQL database name
Relationships:
  - References CompiledArtifacts for compute/storage configuration
```

### 1.2 PreflightResult

Result of a single preflight validation check.

```yaml
Entity: PreflightResult
Description: Result of an individual infrastructure check
Attributes:
  - service: string
      # Service being checked (e.g., "compute", "storage", "catalog", "postgres")
  - status: enum[ok, warning, error]
      # Check result status
  - message: string
      # Human-readable result message
  - duration_ms: integer
      # Time taken for the check in milliseconds
  - remediation: string (optional)
      # Suggested fix if status is error/warning
  - details: object (optional)
      # Additional diagnostic information
Relationships:
  - Part of PreflightReport (1:N)
```

### 1.3 PreflightReport

Aggregate report of all preflight checks.

```yaml
Entity: PreflightReport
Description: Complete report of all preflight validation checks
Attributes:
  - timestamp: datetime
      # When the report was generated
  - overall_status: enum[pass, fail]
      # Overall pass/fail status
  - checks: list[PreflightResult]
      # Individual check results
  - environment: string (optional)
      # Environment being validated (dev/staging/prod)
Relationships:
  - Contains multiple PreflightResult (1:N)
  - References PreflightConfig (N:1)
```

---

## 2. Helm Chart Entities

### 2.1 HelmValues

Helm chart configuration values.

```yaml
Entity: HelmValues
Description: Configuration values for floe-dagster/floe-cube Helm charts
Attributes:
  - image.repository: string
      # Container image repository
  - image.tag: string
      # Container image tag
  - image.pullPolicy: enum[Always, IfNotPresent, Never]
      # Kubernetes image pull policy
  - replicaCount: integer
      # Number of pod replicas
  - resources.requests.cpu: string
      # CPU request (e.g., "100m")
  - resources.requests.memory: string
      # Memory request (e.g., "256Mi")
  - resources.limits.cpu: string
      # CPU limit
  - resources.limits.memory: string
      # Memory limit
  - compiledArtifacts.configMapName: string
      # ConfigMap containing CompiledArtifacts
  - externalSecrets.enabled: boolean
      # Enable External Secrets integration
  - externalSecrets.secretStoreName: string (optional)
      # ClusterSecretStore name
Relationships:
  - Consumed by Helm chart templates
  - References CompiledArtifacts via ConfigMap
```

### 2.2 DemoConfig

Configuration for demo mode with synthetic data generation.

```yaml
Entity: DemoConfig
Description: Configuration for E2E demo with continuous data generation
Attributes:
  - enabled: boolean (default: false)
      # Enable demo mode
  - schedule.cron: string (default: "*/5 * * * *")
      # Cron expression for data generation schedule
  - schedule.batchSize: integer (default: 100)
      # Number of orders per batch
  - dataQuality.nullRate: float (default: 0.02)
      # Percentage of null values to inject (0.0-1.0)
  - dataQuality.duplicateRate: float (default: 0.01)
      # Percentage of duplicate records
  - dataQuality.lateArrivalRate: float (default: 0.05)
      # Percentage of late-arriving data
  - burstMode.enabled: boolean (default: false)
      # Enable burst mode for quick demos
  - burstMode.recordsPerSecond: integer (default: 1000)
      # Generation rate in burst mode
  - observability.marquezEnabled: boolean (default: true)
      # Expose Marquez UI for lineage
  - observability.jaegerEnabled: boolean (default: true)
      # Expose Jaeger UI for tracing
Relationships:
  - Extends HelmValues for demo profile
  - Controls DemoSchedule behavior
```

---

## 3. Synthetic Data Entities

### 3.1 Customer

E-commerce customer entity (existing in floe-synthetic).

```yaml
Entity: Customer
Description: Customer record for e-commerce demo
Attributes:
  - customer_id: string (UUID)
      # Unique customer identifier
  - email: string
      # Customer email address
  - name: string
      # Customer full name
  - region: enum[NA, EMEA, APAC, LATAM]
      # Geographic region
  - created_at: datetime
      # Account creation timestamp
  - updated_at: datetime
      # Last update timestamp
Relationships:
  - Has many Orders (1:N)
```

### 3.2 Product

E-commerce product entity (existing in floe-synthetic).

```yaml
Entity: Product
Description: Product record for e-commerce demo
Attributes:
  - product_id: string (UUID)
      # Unique product identifier
  - name: string
      # Product name
  - category: string
      # Product category
  - price: decimal
      # Unit price
  - created_at: datetime
      # Product creation timestamp
Relationships:
  - Referenced by OrderItem (N:1)
```

### 3.3 Order

E-commerce order entity (existing in floe-synthetic).

```yaml
Entity: Order
Description: Order record for e-commerce demo
Attributes:
  - order_id: string (UUID)
      # Unique order identifier
  - customer_id: string (UUID)
      # Reference to customer
  - status: enum[pending, processing, shipped, delivered, cancelled]
      # Order status
  - total_amount: decimal
      # Order total
  - order_date: datetime
      # When order was placed
  - shipped_date: datetime (optional)
      # When order was shipped
Relationships:
  - Belongs to Customer (N:1)
  - Has many OrderItems (1:N)
```

### 3.4 OrderItem (NEW)

Order line item entity (to be added to floe-synthetic).

```yaml
Entity: OrderItem
Description: Individual line item within an order (NEW for FR-027a)
Attributes:
  - order_item_id: string (UUID)
      # Unique line item identifier
  - order_id: string (UUID)
      # Reference to parent order
  - product_id: string (UUID)
      # Reference to product
  - quantity: integer
      # Quantity ordered
  - unit_price: decimal
      # Price at time of order
  - discount: decimal (default: 0.0)
      # Discount applied
  - subtotal: decimal
      # quantity * unit_price - discount
Relationships:
  - Belongs to Order (N:1)
  - References Product (N:1)
```

---

## 4. dbt Model Entities

### 4.1 Staging Models

Bronze/staging layer models for raw data ingestion.

```yaml
Models:
  - stg_customers
      Source: customers Iceberg table
      Purpose: Clean and type-cast raw customer data
  - stg_orders
      Source: orders Iceberg table
      Purpose: Clean and type-cast raw order data
  - stg_order_items
      Source: order_items Iceberg table
      Purpose: Clean and type-cast raw order item data
  - stg_products
      Source: products Iceberg table
      Purpose: Clean and type-cast raw product data
```

### 4.2 Intermediate Models

Silver/intermediate layer models for business logic.

```yaml
Models:
  - int_order_items_enriched
      Sources: stg_order_items, stg_products
      Purpose: Join order items with product details
  - int_customer_orders
      Sources: stg_customers, stg_orders
      Purpose: Aggregate order metrics per customer
  - int_product_performance
      Sources: stg_order_items, stg_products
      Purpose: Calculate product-level metrics
```

### 4.3 Mart Models

Gold/mart layer models for analytics consumption.

```yaml
Models:
  - mart_revenue
      Sources: int_order_items_enriched
      Purpose: Revenue metrics by time period and region
  - mart_customer_segments
      Sources: int_customer_orders
      Purpose: Customer segmentation (RFM analysis)
  - mart_product_analytics
      Sources: int_product_performance
      Purpose: Product performance dashboard
```

---

## 5. Cube Semantic Layer Entities

### 5.1 Orders Cube

```yaml
Cube: Orders
Description: Order-level semantic model
Dimensions:
  - status: Order status category
  - region: Customer region
  - order_date: Order date (day/week/month/year)
Measures:
  - count: Total order count
  - total_revenue: Sum of order totals
  - average_order_value: Revenue / count
Joins:
  - Customers (many-to-one)
  - OrderItems (one-to-many)
```

### 5.2 Customers Cube

```yaml
Cube: Customers
Description: Customer-level semantic model
Dimensions:
  - region: Geographic region
  - segment: Customer segment (from RFM)
  - created_at: Customer since (day/month/year)
Measures:
  - count: Total customer count
  - lifetime_value: Sum of all order totals
  - average_order_value: LTV / order count
```

### 5.3 Products Cube

```yaml
Cube: Products
Description: Product-level semantic model
Dimensions:
  - category: Product category
  - name: Product name
Measures:
  - units_sold: Sum of quantities
  - revenue: Sum of subtotals
  - average_price: Revenue / units_sold
```

---

## 6. Entity Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Data Model Relationships                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Configuration Domain                                                │
│  ┌──────────────────┐     ┌──────────────────┐                      │
│  │ PreflightConfig  │────▶│ PreflightReport  │                      │
│  └──────────────────┘     └────────┬─────────┘                      │
│                                    │ 1:N                            │
│                           ┌────────▼─────────┐                      │
│                           │ PreflightResult  │                      │
│                           └──────────────────┘                      │
│                                                                      │
│  Helm Domain                                                         │
│  ┌──────────────────┐     ┌──────────────────┐                      │
│  │   HelmValues     │◀────│   DemoConfig     │                      │
│  └──────────────────┘     └──────────────────┘                      │
│          │                                                           │
│          ▼ references                                                │
│  ┌──────────────────┐                                               │
│  │CompiledArtifacts │                                               │
│  └──────────────────┘                                               │
│                                                                      │
│  E-commerce Domain (Synthetic Data)                                  │
│  ┌──────────────────┐                                               │
│  │    Customer      │                                               │
│  └────────┬─────────┘                                               │
│           │ 1:N                                                      │
│  ┌────────▼─────────┐     ┌──────────────────┐                      │
│  │      Order       │────▶│    OrderItem     │◀────┐                │
│  └──────────────────┘ 1:N └──────────────────┘     │ N:1            │
│                                                     │                │
│                            ┌──────────────────┐     │                │
│                            │     Product      │─────┘                │
│                            └──────────────────┘                      │
│                                                                      │
│  dbt Medallion Layers                                                │
│  ┌────────────┐    ┌────────────────┐    ┌────────────────┐         │
│  │  Staging   │───▶│  Intermediate  │───▶│     Marts      │         │
│  │ stg_*      │    │    int_*       │    │    mart_*      │         │
│  └────────────┘    └────────────────┘    └────────────────┘         │
│                                                    │                 │
│                                                    ▼                 │
│                            ┌──────────────────────────────┐         │
│                            │     Cube Semantic Layer      │         │
│                            │ Orders | Customers | Products│         │
│                            └──────────────────────────────┘         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Data Quality Scenarios (FR-027b)

### 7.1 Null Injection

```yaml
Scenario: Null Values
Description: Inject configurable percentage of NULL values
Affected Fields:
  - Customer.email (tests null handling in staging)
  - Order.shipped_date (tests optional field handling)
  - OrderItem.discount (tests default value handling)
Configuration:
  - nullRate: 0.02 (2% of records)
dbt Handling:
  - COALESCE functions in staging models
  - is_valid flags in intermediate models
```

### 7.2 Duplicate Injection

```yaml
Scenario: Duplicate Records
Description: Generate duplicate records to test deduplication
Affected Entities:
  - Orders (same order_id, different timestamps)
  - OrderItems (same order_item_id)
Configuration:
  - duplicateRate: 0.01 (1% of records)
dbt Handling:
  - ROW_NUMBER() window functions
  - Deduplication in staging layer
```

### 7.3 Late-Arriving Data

```yaml
Scenario: Late-Arriving Records
Description: Generate records with timestamps in the past
Affected Entities:
  - Orders (order_date before previous batch)
  - OrderItems (records for old orders)
Configuration:
  - lateArrivalRate: 0.05 (5% of records)
  - maxLateDays: 7 (up to 7 days late)
dbt Handling:
  - Incremental models with merge strategy
  - Updated_at tracking
```

---

## Summary

| Domain | Entities | Status |
|--------|----------|--------|
| Configuration | PreflightConfig, PreflightResult, PreflightReport | New |
| Helm | HelmValues, DemoConfig | New |
| Synthetic Data | Customer, Product, Order | Existing |
| Synthetic Data | OrderItem | New (FR-027a) |
| dbt Models | stg_*, int_*, mart_* | New |
| Cube | Orders, Customers, Products | New |
| Data Quality | Null, Duplicate, Late-Arriving scenarios | New (FR-027b) |
