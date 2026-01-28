// Copyright (c) 2026, Material Price Control and Contributors
// License: MIT

frappe.query_reports["Historical Anomaly Finder"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item"
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group"
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse"
		},
		{
			fieldname: "voucher_type",
			label: __("Voucher Type"),
			fieldtype: "Select",
			options: "\nPurchase Receipt\nPurchase Invoice\nStock Entry\nStock Reconciliation"
		},
		{
			fieldname: "show_only_anomalies",
			label: __("Show Only Anomalies"),
			fieldtype: "Check",
			default: 1
		}
	],
	
	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname === "severity") {
			if (data.severity === "Severe") {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else if (data.severity === "Warning") {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			} else if (data.severity === "No Rule") {
				value = `<span style="color: gray;">${value}</span>`;
			}
		}
		
		if (column.fieldname === "variance_pct" && data.variance_pct) {
			if (data.severity === "Severe") {
				value = `<span style="color: red;">${value}</span>`;
			} else if (data.severity === "Warning") {
				value = `<span style="color: orange;">${value}</span>`;
			}
		}
		
		return value;
	}
};
