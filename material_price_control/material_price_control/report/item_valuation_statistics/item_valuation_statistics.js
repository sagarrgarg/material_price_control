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
				data-ucl="${data.ucl || 0}"
				data-variance-pct="${data.variance_pct || 0}">
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
		const setMethodVariance = __("Variance % (from report)");
		const setMethodMinMax = __("Min/Max (from report)");

		const parseFloatOrNull = (value) => {
			const parsed = parseFloat(value);
			return Number.isFinite(parsed) ? parsed : null;
		};

		const formatPercent = (value) => {
			const parsed = parseFloat(value);
			return Number.isFinite(parsed) && parsed > 0 ? parsed.toFixed(2) : null;
		};
		
		const escapeHtml = (value) => frappe.utils.escape_html(value || "");

		const applySetMethodDefaults = (dialog, defaults) => {
			const method = dialog.get_value("set_method");
			const useVariance = method === setMethodVariance;

			if (useVariance) {
				dialog.set_df_property("allowed_variance_pct", "read_only", 0);
				dialog.set_df_property("min_rate", "read_only", 1);
				dialog.set_df_property("max_rate", "read_only", 1);
				dialog.set_value(
					"allowed_variance_pct",
					defaults.variancePct && defaults.variancePct > 0 ? defaults.variancePct : null
				);
				dialog.set_value("min_rate", null);
				dialog.set_value("max_rate", null);
			} else {
				dialog.set_df_property("allowed_variance_pct", "read_only", 1);
				dialog.set_df_property("min_rate", "read_only", 0);
				dialog.set_df_property("max_rate", "read_only", 0);
				dialog.set_value("allowed_variance_pct", null);
				dialog.set_value("min_rate", defaults.lcl > 0 ? defaults.lcl : null);
				dialog.set_value("max_rate", defaults.ucl > 0 ? defaults.ucl : null);
			}
		};

		const buildRuleArgs = (values, setMethod) => {
			const useVariance = setMethod === setMethodVariance;

			return {
				item_code: values.item_code,
				expected_rate: values.expected_rate,
				min_rate: useVariance ? null : (values.min_rate > 0 ? values.min_rate : null),
				max_rate: useVariance ? null : (values.max_rate > 0 ? values.max_rate : null),
				warehouse: values.warehouse || null,
				allowed_variance_pct:
					useVariance && values.allowed_variance_pct > 0 ? values.allowed_variance_pct : null,
			};
		};

		const showRuleDialog = ({ itemCode, mean, lcl, ucl, variancePct, warehouse, isUpdate }) => {
			const formattedVariance = formatPercent(variancePct);
			const varianceDescription = formattedVariance
				? __("Suggested: Variance % = {0}. Leave empty to use system default.", [formattedVariance])
				: __("Leave empty to use system default");

			const defaults = { lcl, ucl, variancePct };
			let dialog;

			dialog = new frappe.ui.Dialog({
				title: isUpdate ? __("Update Cost Valuation Rule") : __("Set Cost Valuation Rule"),
				fields: [
					{
						fieldtype: "Link",
						fieldname: "item_code",
						label: __("Item"),
						options: "Item",
						default: itemCode,
						read_only: 1,
					},
					{
						fieldtype: "Link",
						fieldname: "warehouse",
						label: __("Warehouse"),
						options: "Warehouse",
						default: warehouse,
						description: __("Leave empty for all warehouses"),
					},
					{
						fieldtype: "Section Break",
						label: __("Rate Settings"),
					},
					{
						fieldtype: "Select",
						fieldname: "set_method",
						label: __("Set Limits By"),
						options: `${setMethodVariance}\n${setMethodMinMax}`,
						default: setMethodVariance,
						reqd: 1,
						onchange: () => applySetMethodDefaults(dialog, defaults),
					},
					{
						fieldtype: "Currency",
						fieldname: "expected_rate",
						label: __("Expected Rate"),
						default: mean,
						reqd: 1,
						description: __("Suggested: Mean (μ) = {0}", [format_currency(mean)]),
					},
					{
						fieldtype: "Column Break",
					},
					{
						fieldtype: "Percent",
						fieldname: "allowed_variance_pct",
						label: __("Allowed Variance %"),
						description: varianceDescription,
					},
					{
						fieldtype: "Section Break",
						label: __("Hard Limits (Optional)"),
					},
					{
						fieldtype: "Currency",
						fieldname: "min_rate",
						label: __("Minimum Rate"),
						description: __("Suggested: LCL (μ-2σ) = {0}", [lcl > 0 ? format_currency(lcl) : "N/A"]),
					},
					{
						fieldtype: "Column Break",
					},
					{
						fieldtype: "Currency",
						fieldname: "max_rate",
						label: __("Maximum Rate"),
						description: __("Suggested: UCL (μ+2σ) = {0}", [ucl > 0 ? format_currency(ucl) : "N/A"]),
					},
				],
				primary_action_label: isUpdate ? __("Update Rule") : __("Create Rule"),
				primary_action: function(values) {
					if (!values.expected_rate || values.expected_rate <= 0) {
						frappe.msgprint(__("Expected Rate must be greater than 0"));
						return;
					}

					const setMethod = values.set_method || setMethodVariance;
					const args = buildRuleArgs(values, setMethod);

					dialog.hide();

					frappe.call({
						method: "material_price_control.material_price_control.guard.upsert_cost_valuation_rule",
						args: args,
						callback: function(r) {
							if (r.message) {
								const action = r.message.action === "created" ? __("Created") : __("Updated");
								frappe.show_alert({
									message: __("{0} rule {1} for {2}", [action, r.message.rule_name, itemCode]),
									indicator: "green",
								});
								// Refresh report to show updated rule info
								frappe.query_report.refresh();
							}
						},
					});
				},
			});

			dialog.show();
			applySetMethodDefaults(dialog, defaults);
		};

		const showBulkDialog = (rows) => {
			const warehouse = frappe.query_report.get_filter_value("warehouse") || null;
			const eligibleRows = rows.filter((row) => row.item_code && row.mean > 0);
			const skippedCount = rows.length - eligibleRows.length;
			const missingVarianceCount = eligibleRows.filter((row) => !(row.variance_pct > 0)).length;

			if (!eligibleRows.length) {
				frappe.msgprint(__("No eligible rows found to set rules"));
				return;
			}

			const summaryHtml = `
				<div>
					<div><strong>${__("Selected rows")}:</strong> ${rows.length}</div>
					<div><strong>${__("Eligible rows")}:</strong> ${eligibleRows.length}</div>
					${skippedCount ? `<div class="text-warning">${__("Skipped rows with no mean")}: ${skippedCount}</div>` : ""}
					<div class="text-muted mt-2">${__("Expected Rate will be set to Mean (μ) for each item.")}</div>
				</div>
			`;

			const dialog = new frappe.ui.Dialog({
				title: __("Bulk Set Cost Valuation Rules"),
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "summary",
						options: summaryHtml,
					},
					{
						fieldtype: "Link",
						fieldname: "warehouse",
						label: __("Warehouse"),
						options: "Warehouse",
						default: warehouse,
						description: __("Leave empty for all warehouses"),
					},
					{
						fieldtype: "Select",
						fieldname: "set_method",
						label: __("Set Limits By"),
						options: `${setMethodVariance}\n${setMethodMinMax}`,
						default: setMethodVariance,
						reqd: 1,
					},
				],
				primary_action_label: __("Apply Rules"),
				primary_action: function(values) {
					const setMethod = values.set_method || setMethodVariance;
					const useVariance = setMethod === setMethodVariance;
					const rules = eligibleRows.map((row) => ({
						item_code: row.item_code,
						expected_rate: row.mean,
						min_rate: useVariance ? null : (row.lcl > 0 ? row.lcl : null),
						max_rate: useVariance ? null : (row.ucl > 0 ? row.ucl : null),
						allowed_variance_pct: useVariance && row.variance_pct > 0 ? row.variance_pct : null,
					}));

					if (!rules.length) {
						frappe.msgprint(__("No eligible rows found to set rules"));
						return;
					}

					dialog.hide();

					frappe.call({
						method: "material_price_control.material_price_control.guard.bulk_upsert_cost_valuation_rules",
						args: {
							rules: rules,
							warehouse: values.warehouse || null,
						},
						callback: function(r) {
							const response = r.message || {};
							const successCount = response.success_count || 0;
							const errors = response.errors || [];
							const errorCount = errors.length;
							const varianceNote =
								useVariance && missingVarianceCount
									? __("Rows without variance % used default variance: {0}", [
											missingVarianceCount,
									  ])
									: null;

							let message = __("{0} rules applied", [successCount]);
							if (skippedCount) {
								message += `<br/>${__("Skipped rows with no mean: {0}", [skippedCount])}`;
							}
							if (varianceNote) {
								message += `<br/>${varianceNote}`;
							}
							if (errorCount) {
								const errorList = errors
									.slice(0, 5)
									.map((err) => `<li>${escapeHtml(err.item_code)}: ${escapeHtml(err.error)}</li>`)
									.join("");
								message += `<br/><br/>${__("Errors ({0})", [errorCount])}<ul>${errorList}</ul>`;
								if (errorCount > 5) {
									message += `<div class="text-muted">${__("Only first 5 errors shown")}</div>`;
								}
							}

							frappe.msgprint({
								title: __("Bulk Set Results"),
								message: message,
								indicator: errorCount ? "orange" : "green",
							});
							frappe.query_report.refresh();
						},
					});
				},
			});

			dialog.show();
		};

		report.page.add_inner_button(__("Bulk Set Rules"), function() {
			if (!report.datatable) {
				frappe.msgprint(__("Please run the report first"));
				return;
			}

			const indexes = report.datatable.rowmanager.getCheckedRows();
			const selectedRows = indexes
				.filter((i) => i !== undefined)
				.map((i) => report.data[i])
				.filter(Boolean);

			if (!selectedRows.length) {
				frappe.msgprint(__("Please select at least one row"));
				return;
			}

			showBulkDialog(selectedRows);
		});

		// Bind click handler for Set buttons using event delegation
		$(report.page.main).on("click", ".set-rule-btn", function(e) {
			e.preventDefault();
			e.stopPropagation();

			const $btn = $(this);
			const itemCode = $btn.data("item");
			const mean = parseFloatOrNull($btn.data("mean"));
			const lcl = parseFloatOrNull($btn.data("lcl"));
			const ucl = parseFloatOrNull($btn.data("ucl"));
			const variancePct = parseFloatOrNull($btn.data("variance-pct"));
			const warehouse = frappe.query_report.get_filter_value("warehouse") || null;
			const isUpdate = $btn.text().trim() === __("Update");

			if (!itemCode || !mean || mean <= 0) {
				frappe.msgprint(__("Invalid data for setting rule"));
				return;
			}

			showRuleDialog({
				itemCode,
				mean,
				lcl: lcl || 0,
				ucl: ucl || 0,
				variancePct,
				warehouse,
				isUpdate,
			});
		});
	},
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
};
