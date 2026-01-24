# Material Price Control

Prevent cost valuation errors in ERPNext by detecting and blocking unusual material rates during stock-in transactions.

## Problem

Wrong valuation rates (e.g., ₹10/pc entered as ₹120/pc) due to:
- Wrong UOM selection
- Incorrect quantity entry
- Data entry mistakes in manufacturing/purchase

## Solution

This app validates incoming rates against expected values and:
- **Warns** on minor deviations
- **Blocks** severe anomalies (configurable)
- **Logs** all detected anomalies for review

## Features

| Feature | Description |
|---------|-------------|
| **Real-time Validation** | Checks rates before document submission |
| **Flexible Rules** | Set expected rates per Item or Item Group |
| **Hard Limits** | Define absolute min/max rate boundaries |
| **Variance Thresholds** | Configure allowed % deviation |
| **Bypass Roles** | Allow authorized users to override blocks |
| **Control Chart** | Visual analysis with ECharts |
| **Historical Report** | Find past anomalies in stock ledger |

## Supported Transactions

- Purchase Receipt
- Purchase Invoice (with `Update Stock`)
- Stock Entry (incoming items)

## Installation

```bash
bench get-app https://github.com/your-org/material_price_control
bench --site your-site install-app material_price_control
bench --site your-site migrate
bench build --app material_price_control
```

## Configuration

### 1. Enable the Guard

Navigate to **Cost Valuation Settings**:

| Setting | Description |
|---------|-------------|
| Enabled | Turn on/off the guard |
| Default Variance % | Allowed deviation (default: 30%) |
| Severe Multiplier | Multiplier for severe threshold (default: 2x) |
| Block Severe | Prevent submission on severe anomalies |
| Block If No Rule | Require rules for all stock-in items |
| Bypass Roles | Roles that can override blocks |

### 2. Create Rules

Navigate to **Cost Valuation Rule**:

```
Rule For: Item or Item Group
Expected Rate: ₹10.00
Allowed Variance %: 20 (optional, overrides default)
Min Rate: ₹8.00 (optional, hard floor)
Max Rate: ₹15.00 (optional, hard ceiling)
```

## How It Works

```
Transaction Submit
       ↓
   Guard Hook (before_submit)
       ↓
   Get Rule (Item → Item Group → None)
       ↓
   Calculate Variance
       ↓
   ┌─────────────────────────────────┐
   │ Within limits? → Allow          │
   │ Warning level? → Log + Allow    │
   │ Severe level?  → Log + Block*   │
   └─────────────────────────────────┘
   * Unless user has bypass role
```

## Workspace

Access from sidebar: **Cost Valuation**

- **Settings** - Global configuration
- **Rules** - Expected rate definitions
- **Anomaly Log** - Detected anomalies
- **Control Chart** - Visual rate analysis
- **Historical Report** - Find past anomalies

## Error Message Example

When a transaction is blocked:

```
Cost Valuation Anomaly for Item M001

Incoming Rate:    ₹120.00
Expected Rate:    ₹10.00
Variance:         1100.0%
Allowed Variance: ≤ 30.0%
Severe Threshold: > 60.0%

Reason: Variance 1100.0% exceeds severe threshold 60.0%

Please correct the rate or contact a user with bypass permissions.
```

## API

```python
# Get chart data for an item
from material_price_control.material_price_control.guard import get_chart_data
data = get_chart_data(item_code="ITEM-001", from_date="2024-01-01", to_date="2024-12-31")

# Get items with most anomalies
from material_price_control.material_price_control.guard import get_items_with_anomalies
items = get_items_with_anomalies(limit=10)
```

## License

MIT
