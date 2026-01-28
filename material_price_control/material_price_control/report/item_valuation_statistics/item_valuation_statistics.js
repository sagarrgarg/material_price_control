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

		if (column.fieldname === "set_rule" && data.item_code && data.mean > 0) {
			// Render Set button for rows with valid statistics
			const btnClass = data.rule_name ? "btn-default" : "btn-primary";
			const btnText = data.rule_name ? __("Update") : __("Set");
			value = `<button class="btn btn-xs ${btnClass} set-rule-btn" 
				data-item="${data.item_code}"
				data-mean="${data.mean || 0}"
				data-lcl="${data.lcl || 0}"
				data-ucl="${data.ucl || 0}">
				${btnText}
			</button>`;
		} else if (column.fieldname === "set_rule") {
			value = `<span class="text-muted">-</span>`;
		}

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
	},

	onload: function(report) {
		// Bind click handler for Set buttons using event delegation
		$(report.page.main).on("click", ".set-rule-btn", function(e) {
			e.preventDefault();
			e.stopPropagation();
			
			const $btn = $(this);
			const itemCode = $btn.data("item");
			const mean = parseFloat($btn.data("mean"));
			const lcl = parseFloat($btn.data("lcl"));
			const ucl = parseFloat($btn.data("ucl"));
			const warehouse = frappe.query_report.get_filter_value("warehouse") || null;
			const isUpdate = $btn.text().trim() === __("Update");
			
			if (!itemCode || mean <= 0) {
				frappe.msgprint(__("Invalid data for setting rule"));
				return;
			}
			
			// Show dialog with prefilled values
			const dialog = new frappe.ui.Dialog({
				title: isUpdate ? __("Update Cost Valuation Rule") : __("Set Cost Valuation Rule"),
				fields: [
					{
						fieldtype: "Link",
						fieldname: "item_code",
						label: __("Item"),
						options: "Item",
						default: itemCode,
						read_only: 1
					},
					{
						fieldtype: "Link",
						fieldname: "warehouse",
						label: __("Warehouse"),
						options: "Warehouse",
						default: warehouse,
						description: __("Leave empty for all warehouses")
					},
					{
						fieldtype: "Section Break",
						label: __("Rate Settings")
					},
					{
						fieldtype: "Currency",
						fieldname: "expected_rate",
						label: __("Expected Rate"),
						default: mean,
						reqd: 1,
						description: __("Suggested: Mean (μ) = {0}", [format_currency(mean)])
					},
					{
						fieldtype: "Column Break"
					},
					{
						fieldtype: "Percent",
						fieldname: "allowed_variance_pct",
						label: __("Allowed Variance %"),
						description: __("Leave empty to use system default")
					},
					{
						fieldtype: "Section Break",
						label: __("Hard Limits (Optional)")
					},
					{
						fieldtype: "Currency",
						fieldname: "min_rate",
						label: __("Minimum Rate"),
						default: lcl > 0 ? lcl : null,
						description: __("Suggested: LCL (μ-2σ) = {0}", [lcl > 0 ? format_currency(lcl) : "N/A"])
					},
					{
						fieldtype: "Column Break"
					},
					{
						fieldtype: "Currency",
						fieldname: "max_rate",
						label: __("Maximum Rate"),
						default: ucl > 0 ? ucl : null,
						description: __("Suggested: UCL (μ+2σ) = {0}", [ucl > 0 ? format_currency(ucl) : "N/A"])
					}
				],
				primary_action_label: isUpdate ? __("Update Rule") : __("Create Rule"),
				primary_action: function(values) {
					if (!values.expected_rate || values.expected_rate <= 0) {
						frappe.msgprint(__("Expected Rate must be greater than 0"));
						return;
					}
					
					dialog.hide();
					
					frappe.call({
						method: "material_price_control.material_price_control.guard.upsert_cost_valuation_rule",
						args: {
							item_code: values.item_code,
							expected_rate: values.expected_rate,
							min_rate: values.min_rate > 0 ? values.min_rate : null,
							max_rate: values.max_rate > 0 ? values.max_rate : null,
							warehouse: values.warehouse || null,
							allowed_variance_pct: values.allowed_variance_pct > 0 ? values.allowed_variance_pct : null
						},
						callback: function(r) {
							if (r.message) {
								const action = r.message.action === "created" ? __("Created") : __("Updated");
								frappe.show_alert({
									message: __("{0} rule {1} for {2}", [action, r.message.rule_name, itemCode]),
									indicator: "green"
								});
								// Refresh report to show updated rule info
								frappe.query_report.refresh();
							}
						}
					});
				}
			});
			
			dialog.show();
		});
	}
};
