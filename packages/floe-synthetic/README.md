# floe-synthetic

Synthetic data generation for floe-runtime testing and demo environments.

## Features

- **Faker-based generators**: Realistic data generation with deterministic seeding
- **E-commerce schema**: Customers, Orders, Products
- **SaaS metrics schema**: Users, Events, Subscriptions
- **Weighted distributions**: Realistic categorical data patterns
- **Temporal distributions**: Time-series patterns with seasonality and trends
- **PyIceberg loader**: Direct writes to Iceberg tables
- **Dagster integration**: Scheduled data generation assets

## Installation

```bash
uv add floe-synthetic
```

For Dagster integration:

```bash
uv add "floe-synthetic[dagster]"
```

## Quick Start

### Generate E-commerce Data

```python
from floe_synthetic.generators.ecommerce import EcommerceGenerator

generator = EcommerceGenerator(seed=42)

# Generate customers
customers = generator.generate_customers(1000)

# Generate orders with weighted status distribution
orders = generator.generate_orders(5000)

# Generate products
products = generator.generate_products(100)
```

### Generate SaaS Metrics Data

```python
from floe_synthetic.generators.saas import SaaSGenerator

generator = SaaSGenerator(seed=42)

# Generate users with organizations
users = generator.generate_users(500, with_organizations=True)

# Generate events
events = generator.generate_events(10000)

# Generate subscriptions
subscriptions = generator.generate_subscriptions()
```

### Load to Iceberg

```python
from floe_synthetic.loaders.iceberg import IcebergLoader

loader = IcebergLoader(catalog_name="demo", catalog_uri="http://polaris:8181/api/catalog")

# Append data
result = loader.append("demo.orders", orders)
print(f"Loaded {result.rows_loaded} rows, snapshot: {result.snapshot_id}")
```

## Distributions

### Weighted Distributions

```python
from floe_synthetic.distributions.weighted import WeightedDistribution

status_dist = WeightedDistribution({
    "completed": 60,
    "processing": 20,
    "pending": 15,
    "cancelled": 5,
}, seed=42)

values = status_dist.sample(100)
```

### Temporal Distributions

```python
from floe_synthetic.distributions.temporal import TemporalDistribution
from datetime import datetime

dist = TemporalDistribution(
    daily_peak_hours=(10, 14, 18, 21),
    weekend_factor=0.3,
    trend_percent=0.02,
    seed=42,
)

# Generate timestamps with realistic patterns
timestamps = dist.generate_timestamps(
    count=1000,
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31),
)
```

## Development

```bash
# Run tests
uv run pytest tests/unit/ -v

# Type checking
uv run mypy --strict src/

# Linting
uv run ruff check src/
```

## License

Apache-2.0
