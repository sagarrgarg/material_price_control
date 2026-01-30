# Material Price Control

Prevent cost valuation errors in ERPNext by detecting and blocking unusual material rates during stock-in transactions.

[![CI](https://github.com/your-org/material_price_control/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/material_price_control/actions/workflows/ci.yml)
[![Linters](https://github.com/your-org/material_price_control/actions/workflows/linters.yml/badge.svg)](https://github.com/your-org/material_price_control/actions/workflows/linters.yml)

## Compatibility

| Frappe Version | ERPNext Version | Python | Status |
|----------------|-----------------|--------|--------|
| v14.x | v14.x | 3.10 | Supported |
| v15.x | v15.x | 3.10+ | Supported |
| v16.x | v16.x | 3.11+ | Supported |

## Problem

Wrong valuation rates (e.g., ₹10/pc entered as ₹120/pc) due to:
- Wrong UOM selection
- Incorrect quantity entry
- Data entry mistakes in manufacturing/purchase

These errors corrupt inventory valuation and are difficult to trace later.

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
| **Warehouse-specific Rules** | Different rates for different warehouses |
| **Date-range Rules** | Temporary rules with validity periods |
| **Hard Limits** | Define absolute min/max rate boundaries |
| **Variance Thresholds** | Configure allowed % deviation |
| **Internal Supplier Filter** | Optionally skip validation for internal transfers |
| **Bypass Roles** | Allow authorized users to override blocks |
| **Control Chart** | Visual analysis with ECharts |
| **Item Statistics Report** | Historical mean, std dev, UCL/LCL analysis |
| **Bulk Rule Creation** | Set rules for multiple items at once |

## Supported Transactions

- Purchase Receipt
- Purchase Invoice (with `Update Stock`)
- Stock Entry (incoming items)

---

## Installation

### Option 1: Frappe Cloud (Recommended)

1. Go to your Frappe Cloud dashboard
2. Navigate to **Sites** → Select your site → **Apps**
3. Click **Install App**
4. Search for "Material Price Control" in the marketplace
5. Click **Install**

The app will be automatically installed and migrated.

### Option 2: Manual Installation (Self-hosted)

#### Prerequisites

- Frappe Bench installed and configured
- ERPNext v14, v15, or v16 installed
- Python 3.10+ (3.11+ for v16)

#### Steps

```bash
# Navigate to your bench directory
cd ~/frappe-bench

# Get the app
bench get-app https://github.com/your-org/material_price_control

# Install on your site
bench --site your-site.localhost install-app material_price_control

# Run migrations
bench --site your-site.localhost migrate

# Build assets
bench build --app material_price_control

# Restart bench (production)
sudo supervisorctl restart all
```

#### For Development

```bash
# Get app in development mode
bench get-app https://github.com/your-org/material_price_control --branch develop

# Install with development dependencies
bench setup requirements --dev

# Start development server
bench start
```

---

## Configuration

### 1. Enable the Guard

Navigate to **Cost Valuation Settings** (`/app/cost-valuation-settings`):

| Setting | Description |
|---------|-------------|
| Enabled | Turn on/off the guard |
| Include Internal Suppliers | Validate internal supplier transactions |
| Default Variance % | Allowed deviation (default: 30%) |
| Severe Multiplier | Multiplier for severe threshold (default: 2x) |
| Block Severe | Prevent submission on severe anomalies |
| Block If No Rule | Require rules for all stock-in items |
| Bypass Roles | Roles that can override blocks |

### 2. Create Rules

Navigate to **Cost Valuation Rule** (`/app/cost-valuation-rule/new`):

```
Rule For: Item or Item Group
Item Code: ITEM-001
Expected Rate: ₹10.00
Allowed Variance %: 20 (optional, overrides default)
Min Rate: ₹8.00 (optional, hard floor)
Max Rate: ₹15.00 (optional, hard ceiling)
Warehouse: (optional, for warehouse-specific rules)
From Date / To Date: (optional, for temporary rules)
```

### 3. Bulk Rule Creation (from Statistics Report)

1. Go to **Item Valuation Statistics** report
2. Select items using checkboxes
3. Click **Bulk Set Rules**
4. Choose "Variance %" or "Min/Max" limit method
5. Apply rules to all selected items

---

## Usage

### How It Works

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

### Workspace

Access from sidebar: **Cost Valuation**

| Shortcut | Description |
|----------|-------------|
| Settings | Global configuration |
| Rules | Expected rate definitions |
| Open Anomalies | Detected anomalies requiring review |
| Control Chart | Visual rate analysis (ECharts) |
| Item Statistics | Historical statistics report |
| Historical Finder | Find past anomalies in stock ledger |

### Error Message Example

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

---

## API Reference

### Get Chart Data

```python
from material_price_control.material_price_control.guard import get_chart_data

data = get_chart_data(
    item_code="ITEM-001",
    from_date="2024-01-01",
    to_date="2024-12-31",
    include_internal_suppliers=0
)
# Returns: {data_points, statistics, rule}
```

### Get Item Statistics

```python
from material_price_control.material_price_control.guard import get_item_statistics

stats = get_item_statistics(
    item_code="ITEM-001",
    warehouse="Stores - ABC",
    from_date="2024-01-01",
    to_date="2024-12-31"
)
# Returns: {item_code, item_name, statistics: {mean, std_dev, ucl, lcl, count}}
```

### Create/Update Rule

```python
from material_price_control.material_price_control.guard import upsert_cost_valuation_rule

result = upsert_cost_valuation_rule(
    item_code="ITEM-001",
    expected_rate=100.0,
    min_rate=80.0,
    max_rate=120.0,
    warehouse=None,
    allowed_variance_pct=25.0
)
# Returns: {rule_name, action: "created" | "updated"}
```

### Bulk Create Rules

```python
from material_price_control.material_price_control.guard import bulk_upsert_cost_valuation_rules

result = bulk_upsert_cost_valuation_rules(
    rules=[
        {"item_code": "ITEM-001", "expected_rate": 100.0},
        {"item_code": "ITEM-002", "expected_rate": 200.0},
    ],
    warehouse=None
)
# Returns: {success_count, results, errors}
```

---

## Upgrading

### From v14 to v15/v16

The app is forward-compatible. After upgrading Frappe/ERPNext:

```bash
bench --site your-site migrate
bench build --app material_price_control
```

---

## Troubleshooting

### Tests failing locally

If tests fail due to custom mandatory fields on standard doctypes (e.g., Supplier), this is expected. The CI runs on a clean environment without customizations.

### Rules not being applied

1. Check that the rule is **Enabled**
2. Verify the **From Date / To Date** range includes the posting date
3. Check **Warehouse** matches (or is blank for all warehouses)
4. Ensure **Cost Valuation Settings** is enabled

### Internal supplier transactions being validated

Set **Include Internal Suppliers** to unchecked in Cost Valuation Settings to skip validation for suppliers marked as `is_internal_supplier`.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linters: `pre-commit run --all-files`
5. Submit a pull request

---

## License

MIT License - see [LICENSE](license.txt) for details.

---

## Support

- GitHub Issues: [Report a bug](https://github.com/your-org/material_price_control/issues)
- Documentation: [Wiki](https://github.com/your-org/material_price_control/wiki)
