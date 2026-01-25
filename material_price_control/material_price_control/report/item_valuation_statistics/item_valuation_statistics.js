// Copyright (c) 2026, Material Price Control and Contributors
// License: MIT

frappe.query_reports["Item Valuation Statistics"] = {
	filters: [
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -6),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "variance_vs_mean" && data.variance_vs_mean) {
			const val = parseFloat(data.variance_vs_mean);
			if (Math.abs(val) > 20) {
				value = `<span class="text-danger">${value}</span>`;
			} else if (Math.abs(val) > 10) {
				value = `<span class="text-warning">${value}</span>`;
			}
		}

		if (column.fieldname === "data_points") {
			if (parseInt(data.data_points) === 0) {
				value = `<span class="text-muted">${value}</span>`;
			}
		}

		return value;
	}
};
