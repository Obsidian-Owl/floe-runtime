"""Demo pipeline constants.

Data Engineer configuration constants - pure business logic,
no infrastructure details.

Table name constants follow the medallion architecture:
- Raw: Pre-staged by ELT/seed job (demo.raw_*)
- Bronze: Loaded from raw by Dagster assets (demo.bronze_*)
- Silver: Transformed by dbt (demo.silver_*)
- Gold: Aggregated by dbt (demo.gold_*)
"""

from __future__ import annotations

# =============================================================================
# Table Name Constants (S1192: avoid duplicate string literals)
# =============================================================================

# Raw layer tables (pre-staged by ELT/seed job)
TABLE_RAW_CUSTOMERS = "demo.raw_customers"
TABLE_RAW_PRODUCTS = "demo.raw_products"
TABLE_RAW_ORDERS = "demo.raw_orders"
TABLE_RAW_ORDER_ITEMS = "demo.raw_order_items"

# Bronze layer tables (loaded from raw by Dagster assets)
TABLE_BRONZE_CUSTOMERS = "demo.bronze_customers"
TABLE_BRONZE_PRODUCTS = "demo.bronze_products"
TABLE_BRONZE_ORDERS = "demo.bronze_orders"
TABLE_BRONZE_ORDER_ITEMS = "demo.bronze_order_items"

# Silver layer tables (dbt transformations)
TABLE_SILVER_CUSTOMERS = "demo.silver_customers"
TABLE_SILVER_ORDERS = "demo.silver_orders"

# Gold layer tables (dbt marts)
TABLE_GOLD_CUSTOMER_ORDERS = "demo.gold_customer_orders"
