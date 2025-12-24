# Phase 4 Completion Guide

**Status**: DbtResource wired, demo assets need update
**Estimated Time**: 30-45 minutes

---

## What's Complete

✅ **DbtResource Implementation** (`packages/floe-dagster/src/floe_dagster/resources/dbt.py`):
- `create_dbt_cli_resource()` with smart defaults
- Supports artifacts dict, explicit paths, and environment variables
- Defaults to `demo/dbt` for demo project

✅ **FloeDefinitions Integration** (`packages/floe-dagster/src/floe_dagster/definitions.py`):
- Auto-creates `dbt` resource and injects into Definitions
- Graceful degradation if dbt not available
- Logging for observability

✅ **dbt Project** (`demo/dbt/`):
- 4 staging models (Silver layer)
- 3 mart models (Gold layer)
- 20+ data quality tests
- Complete schema documentation

---

## Remaining Tasks

### 1. Update Demo Assets (demo/orchestration/definitions.py)

**Replace placeholder**:
```python
@floe_asset(
    group_name="transform",
    description="Run dbt transformations (staging → intermediate → marts)",
    outputs=["demo.dbt_transformations"],
    inputs=[
        TABLE_BRONZE_CUSTOMERS,
        TABLE_BRONZE_ORDERS,
        TABLE_BRONZE_PRODUCTS,
        TABLE_BRONZE_ORDER_ITEMS,
    ],
    compute_kind="dbt",
    deps=["bronze_customers", "bronze_orders", "bronze_products", "bronze_order_items"],
)
def dbt_transformations(context: AssetExecutionContext) -> Dict[str, str]:
    """Execute dbt transformations (placeholder for full dbt integration)."""
    context.log.info("Bronze layer tables ready for dbt transformations")
    return {"status": "placeholder", "message": "Bronze layer ready for dbt transformations"}
```

**With real execution**:
```python
from dagster_dbt import DbtCliResource

@floe_asset(
    group_name="silver",
    description="Run dbt staging models (Bronze → Silver)",
    inputs=[
        TABLE_BRONZE_CUSTOMERS,
        TABLE_BRONZE_ORDERS,
        TABLE_BRONZE_PRODUCTS,
        TABLE_BRONZE_ORDER_ITEMS,
    ],
    outputs=[
        "demo.silver_customers",
        "demo.silver_orders",
        "demo.silver_products",
        "demo.silver_order_items",
    ],
    compute_kind="dbt",
    deps=["bronze_customers", "bronze_orders", "bronze_products", "bronze_order_items"],
)
def silver_staging(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
) -> Dict[str, Any]:
    """Run dbt staging models to create Silver layer."""
    context.log.info("Running dbt staging models...")

    # Run dbt models in staging folder
    dbt_run = dbt.cli(["run", "--select", "staging.*"], context=context)

    return {
        "models_run": len(dbt_run.result.results),
        "success": dbt_run.success,
        "run_results": dbt_run.result.to_dict(),
    }


@floe_asset(
    group_name="gold",
    description="Run dbt marts (Silver → Gold)",
    inputs=[
        "demo.silver_customers",
        "demo.silver_orders",
        "demo.silver_products",
        "demo.silver_order_items",
    ],
    outputs=[
        "demo.gold_customer_orders",
        "demo.gold_revenue",
        "demo.gold_product_performance",
    ],
    compute_kind="dbt",
    deps=["silver_staging"],
)
def gold_marts(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
) -> Dict[str, Any]:
    """Run dbt marts to create Gold layer."""
    context.log.info("Running dbt marts...")

    # Run dbt models in marts folder
    dbt_run = dbt.cli(["run", "--select", "marts.*"], context=context)

    return {
        "models_run": len(dbt_run.result.results),
        "success": dbt_run.success,
        "run_results": dbt_run.result.to_dict(),
    }
```

**Update defs export**:
```python
defs = FloeDefinitions.from_compiled_artifacts(
    assets=[
        bronze_customers,
        bronze_products,
        bronze_orders,
        bronze_order_items,
        silver_staging,      # NEW
        gold_marts,          # NEW
    ],
    jobs=[demo_bronze_job, demo_pipeline_job],
    schedules=[bronze_refresh_schedule, transform_pipeline_schedule],
    sensors=[file_arrival_sensor],
    namespace="demo",
)
```

---

### 2. Update Cube Schema (charts/floe-cube/values-local.yaml)

**Current** (queries Bronze - WRONG):
```javascript
cube(`Orders`, {
  sql: `SELECT * FROM read_parquet('s3://iceberg-bronze/demo/bronze_orders/data/*.parquet')`,
  // ...
});
```

**Needed** (query Gold marts - CORRECT):
```javascript
cube(`CustomerOrders`, {
  description: "Customer order analytics from Gold layer mart",
  sql: `
    SELECT * FROM read_parquet('s3://iceberg-gold/demo/gold_customer_orders/data/*.parquet')
  `,

  measures: {
    totalOrders: {
      sql: `order_id`,
      type: `countDistinct`,
      description: "Total number of unique orders"
    },
    totalRevenue: {
      sql: `order_total`,
      type: `sum`,
      description: "Total revenue from all orders"
    },
    avgOrderValue: {
      sql: `order_total`,
      type: `avg`,
      description: "Average order value"
    },
    completedOrders: {
      sql: `CASE WHEN order_status = 'completed' THEN order_id END`,
      type: `countDistinct`,
      description: "Number of completed orders"
    },
  },

  dimensions: {
    orderId: {
      sql: `order_id`,
      type: `string`,
      primaryKey: true
    },
    customerId: {
      sql: `customer_id`,
      type: `string`
    },
    customerName: {
      sql: `customer_name`,
      type: `string`
    },
    customerEmail: {
      sql: `customer_email`,
      type: `string`
    },
    customerSegment: {
      sql: `customer_segment`,
      type: `string`
    },
    orderStatus: {
      sql: `order_status`,
      type: `string`
    },
    orderDate: {
      sql: `order_date`,
      type: `time`
    },
    orderRegion: {
      sql: `order_region`,
      type: `string`
    },
  },

  preAggregations: {
    ordersByDay: {
      measures: [CUBE.totalOrders, CUBE.totalRevenue],
      dimensions: [CUBE.orderStatus, CUBE.customerSegment],
      timeDimension: CUBE.orderDate,
      granularity: `day`,
      external: true
    }
  }
});

cube(`Revenue`, {
  description: "Daily revenue analytics from Gold layer",
  sql: `
    SELECT * FROM read_parquet('s3://iceberg-gold/demo/gold_revenue/data/*.parquet')
  `,

  measures: {
    orderCount: {
      sql: `order_count`,
      type: `sum`
    },
    totalRevenue: {
      sql: `total_revenue`,
      type: `sum`
    },
    avgOrderValue: {
      sql: `avg_order_value`,
      type: `avg`
    },
  },

  dimensions: {
    revenueDate: {
      sql: `revenue_date`,
      type: `time`,
      primaryKey: true
    },
    region: {
      sql: `region`,
      type: `string`
    },
    status: {
      sql: `status`,
      type: `string`
    },
    segment: {
      sql: `segment`,
      type: `string`
    },
  }
});

cube(`ProductPerformance`, {
  description: "Product sales analytics from Gold layer",
  sql: `
    SELECT * FROM read_parquet('s3://iceberg-gold/demo/gold_product_performance/data/*.parquet')
  `,

  measures: {
    totalUnitsSold: {
      sql: `total_units_sold`,
      type: `sum`
    },
    totalRevenue: {
      sql: `total_revenue`,
      type: `sum`
    },
    avgSellingPrice: {
      sql: `avg_selling_price`,
      type: `avg`
    },
  },

  dimensions: {
    productId: {
      sql: `product_id`,
      type: `string`,
      primaryKey: true
    },
    productName: {
      sql: `product_name`,
      type: `string`
    },
    category: {
      sql: `category`,
      type: `string`
    },
  }
});
```

---

### 3. Update DuckDB S3 Configuration for Multi-Bucket

Cube needs access to all three buckets (bronze/silver/gold). The current endpoint configuration supports this because all buckets are in the same LocalStack instance.

**Verify** in `charts/floe-cube/values-local.yaml`:
```yaml
api:
  extraEnv:
    - name: CUBEJS_DB_DUCKDB_S3_ENDPOINT
      value: "floe-infra-localstack:4566"  # All buckets accessible
    - name: CUBEJS_DB_DUCKDB_S3_URL_STYLE
      value: "path"  # Required for LocalStack
```

No changes needed - DuckDB can access all buckets through single endpoint.

---

### 4. Deploy and Test

```bash
# Redeploy Dagster with dbt integration
make undeploy-local
make deploy-local-full

# Wait for all pods ready
kubectl get pods -n floe -w

# Check dbt resource available in Dagster
kubectl logs -l component=dagster-webserver -n floe | grep -i dbt

# Trigger bronze + silver + gold pipeline
# (via Dagster UI: Materialize all assets)

# Verify Gold tables created
kubectl exec deploy/floe-infra-localstack -n floe -- \
  awslocal s3 ls s3://iceberg-gold/demo/ --recursive | grep parquet

# Test Cube queries against Gold
curl -s http://localhost:30400/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["CustomerOrders.totalRevenue"],
      "dimensions": ["CustomerOrders.orderStatus"]
    }
  }' | jq
```

---

### 5. E2E Validation Checklist

- [ ] Bronze assets write to `s3://iceberg-bronze/demo/bronze_*/`
- [ ] Silver models (dbt staging) create views
- [ ] Gold marts (dbt marts) write to `s3://iceberg-gold/demo/gold_*/`
- [ ] Cube queries Gold marts successfully
- [ ] Pre-aggregations build in `s3://cube-preaggs/`
- [ ] Jaeger shows traces for all layers
- [ ] Marquez shows lineage Bronze → Silver → Gold
- [ ] dbt tests pass (uniqueness, referential integrity)

---

## Success Criteria

| Metric | Target | How to Verify |
|--------|--------|---------------|
| **Bronze Tables** | 4 tables in bronze bucket | `awslocal s3 ls s3://iceberg-bronze/demo/` |
| **Silver Models** | 4 views created | Check Dagster logs for dbt staging run |
| **Gold Marts** | 3 tables in gold bucket | `awslocal s3 ls s3://iceberg-gold/demo/` |
| **Cube Schema** | 3 cubes (CustomerOrders, Revenue, ProductPerformance) | `curl http://localhost:30400/cubejs-api/v1/meta` |
| **dbt Tests** | All pass | Dagster asset materialization logs |
| **Query Performance** | <200ms for simple aggregations | Test Cube REST API |

---

## Quick Commands Reference

```bash
# Deploy
make deploy-local-full

# Check status
make demo-status

# Clean up completed runs
make demo-cleanup

# Check Bronze data
kubectl exec deploy/floe-infra-localstack -n floe -- \
  awslocal s3 ls s3://iceberg-bronze/demo/bronze_customers/data/

# Check Gold data
kubectl exec deploy/floe-infra-localstack -n floe -- \
  awslocal s3 ls s3://iceberg-gold/demo/gold_customer_orders/data/

# Test Cube meta
curl -s http://localhost:30400/cubejs-api/v1/meta | jq '.cubes[].name'

# Test Cube query
curl -s http://localhost:30400/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{"query": {"measures": ["CustomerOrders.totalRevenue"]}}' | jq

# Check dbt logs in Dagster
kubectl logs -l app.kubernetes.io/component=user-deployments -n floe | grep -i dbt
```

---

## Troubleshooting

### dbt Not Found

**Symptom**: `DbtCliResource not found` in logs

**Fix**: Ensure `dagster-dbt` is installed in demo container image

**Check**:
```bash
kubectl exec deploy/floe-dagster-dagster-user-deployments-floe-demo -n floe -- \
  python -c "from dagster_dbt import DbtCliResource; print('OK')"
```

### Gold Tables Not Created

**Symptom**: No files in `s3://iceberg-gold/`

**Cause**: dbt models didn't run or failed

**Fix**: Check Dagster asset logs for dbt errors
```bash
kubectl logs -l app.kubernetes.io/component=user-deployments -n floe --tail=100 | grep -i error
```

### Cube Can't Read Gold

**Symptom**: Cube errors about missing files

**Cause**: DuckDB S3 configuration or Gold tables don't exist yet

**Fix**:
1. Verify Gold tables exist (see above)
2. Check Cube logs: `kubectl logs -l app.kubernetes.io/component=api -n floe`
3. Verify S3 endpoint: `kubectl exec deploy/floe-cube-api -n floe -- env | grep S3`

---

## Next Steps After Completion

1. ✅ **Update Documentation**: Add E2E walkthrough to demo-quickstart.md
2. ✅ **Create Query Examples**: Document Cube API queries in docs/demo-queries.md
3. ✅ **Performance Tuning**: Optimize dbt models and Cube pre-aggregations
4. ✅ **Add More Marts**: Expand Gold layer with additional analytics
5. ✅ **Implement SCD Type 2**: Add historical tracking for customer segments

---

## Files to Modify

1. `demo/orchestration/definitions.py` - Replace placeholder, add silver/gold assets
2. `charts/floe-cube/values-local.yaml` - Update schema to query Gold
3. (Optional) `demo/orchestration/constants.py` - Add Silver/Gold table constants

That's it! The infrastructure and dbt models are ready. Just need to wire the execution.
