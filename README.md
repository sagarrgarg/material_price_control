### Material Price Control

Material Valuation Control is an ERPNext module that prevents cost valuation errors by detecting and blocking unusual material valuation rates during purchase receipts, purchase invoices, and stock entries. It helps maintain accurate inventory valuation by comparing incoming rates against expected rates and alerting users to potential data entry mistakes or pricing anomalies.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app material_price_control
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/material_price_control
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
