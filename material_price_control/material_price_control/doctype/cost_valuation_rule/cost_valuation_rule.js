// Copyright (c) 2026, Material Price Control and Contributors
// License: MIT

frappe.ui.form.on("Cost Valuation Rule", {
	refresh: function(frm) {
		// Show statistics section at the end
		frm.trigger("show_statistics_section");
		
		// Fetch statistics if item_code is set
		if (frm.doc.rule_for === "Item" && frm.doc.item_code) {
			frm.trigger("fetch_item_statistics");
		}
	},

	rule_for: function(frm) {
		// Clear fields when rule_for changes
		if (frm.doc.rule_for === "Item") {
			frm.set_value("item_group", null);
		} else {
			frm.set_value("item_code", null);
			frm.trigger("clear_statistics");
		}
	},

	item_code: function(frm) {
		if (frm.doc.item_code) {
			frm.trigger("fetch_item_statistics");
		} else {
			frm.trigger("clear_statistics");
		}
	},

	warehouse: function(frm) {
		if (frm.doc.item_code) {
			frm.trigger("fetch_item_statistics");
		}
	},

	show_statistics_section: function(frm) {
		if (frm.stats_section_added) return;
		frm.stats_section_added = true;
		
		// Default dates: last 6 months
		const defaultToDate = frappe.datetime.get_today();
		const defaultFromDate = frappe.datetime.add_months(defaultToDate, -6);
		
		const html = `
			<div class="mpc-stats-section frappe-card p-3 mt-4" style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius);">
				<div class="mpc-stats-header mb-3">
					<div class="d-flex justify-content-between align-items-center mb-2">
						<div style="font-weight: 600; font-size: 14px; color: var(--heading-color);">
							<i class="fa fa-line-chart text-primary"></i> Historical Statistics
						</div>
						<div class="d-flex align-items-center" style="gap: 10px;">
							<div class="mpc-stats-from-date"></div>
							<span class="text-muted">to</span>
							<div class="mpc-stats-to-date"></div>
							<button class="btn btn-xs btn-default mpc-refresh-stats-btn" title="Refresh Statistics">
								<i class="fa fa-refresh"></i>
							</button>
						</div>
					</div>
					<p class="text-muted small mb-0" style="line-height: 1.4;">
						This section shows the historical buying patterns for this item based on past transactions.
						Use these statistics to set appropriate expected rates and variance thresholds.
					</p>
				</div>
				<div class="mpc-stats-content">
					<div class="text-muted">Select an item to view historical statistics</div>
				</div>
				
				<!-- Explanation Section -->
				<div class="mpc-stats-help mt-3 pt-3" style="border-top: 1px solid var(--border-color);">
					<div class="d-flex align-items-center mb-2" style="cursor: pointer;" onclick="$(this).next('.mpc-help-content').slideToggle(200); $(this).find('.fa-chevron-down, .fa-chevron-up').toggleClass('fa-chevron-down fa-chevron-up');">
						<i class="fa fa-question-circle text-info mr-2"></i>
						<span class="font-weight-bold" style="font-size: 12px;">What do these numbers mean?</span>
						<i class="fa fa-chevron-down ml-2 text-muted" style="font-size: 10px;"></i>
					</div>
					<div class="mpc-help-content small" style="display: none; background: var(--subtle-fg); padding: 12px; border-radius: 4px;">
						<table class="table table-sm mb-0" style="font-size: 12px;">
							<tbody>
								<tr>
									<td style="width: 120px;"><strong>Mean (μ)</strong></td>
									<td>The <strong>average price</strong> you have paid for this item. This is typically a good starting point for your Expected Rate.</td>
								</tr>
								<tr>
									<td><strong>Std Dev (σ)</strong></td>
									<td><strong>Standard Deviation</strong> - measures how much prices typically vary from the average. A low value means prices are consistent; a high value means prices fluctuate a lot.</td>
								</tr>
								<tr>
									<td><strong>UCL (μ+2σ)</strong></td>
									<td><strong>Upper Control Limit</strong> - approximately 95% of normal prices fall below this value. Prices above this are unusually high and may indicate errors or market changes.</td>
								</tr>
								<tr>
									<td><strong>LCL (μ-2σ)</strong></td>
									<td><strong>Lower Control Limit</strong> - approximately 95% of normal prices fall above this value. Prices below this are unusually low and may indicate errors or special discounts.</td>
								</tr>
								<tr>
									<td><strong>Data Points</strong></td>
									<td>Number of purchase transactions analyzed. More data points (50+) give more reliable statistics. Fewer points mean the numbers should be used as rough guidance only.</td>
								</tr>
							</tbody>
						</table>
						<div class="alert alert-light mt-2 mb-0 p-2" style="font-size: 11px; border: 1px solid var(--border-color);">
							<strong>💡 Quick Guide:</strong><br/>
							• Set <strong>Expected Rate</strong> = Mean (average historical price)<br/>
							• Set <strong>Min Rate</strong> = LCL (flags unusually low prices)<br/>
							• Set <strong>Max Rate</strong> = UCL (flags unusually high prices)<br/>
							• The 2σ range covers ~95% of normal price variations with sufficient data
						</div>
					</div>
				</div>
			</div>
		`;
		
		// Insert at the END of the form (after all fields)
		$(frm.wrapper).find(".form-layout").append(html);
		
		// Create date controls
		const $section = $(frm.wrapper).find(".mpc-stats-section");
		
		frm.stats_from_date = frappe.ui.form.make_control({
			df: {
				fieldtype: "Date",
				fieldname: "stats_from_date",
				placeholder: "From Date",
				default: defaultFromDate
			},
			parent: $section.find(".mpc-stats-from-date"),
			render_input: true
		});
		frm.stats_from_date.set_value(defaultFromDate);
		frm.stats_from_date.$input.css({"width": "120px", "height": "28px"});
		
		frm.stats_to_date = frappe.ui.form.make_control({
			df: {
				fieldtype: "Date",
				fieldname: "stats_to_date",
				placeholder: "To Date",
				default: defaultToDate
			},
			parent: $section.find(".mpc-stats-to-date"),
			render_input: true
		});
		frm.stats_to_date.set_value(defaultToDate);
		frm.stats_to_date.$input.css({"width": "120px", "height": "28px"});
		
		// Bind refresh button
		$section.find(".mpc-refresh-stats-btn").on("click", function() {
			frm.trigger("fetch_item_statistics");
		});
		
		// Bind date change events
		frm.stats_from_date.$input.on("change", function() {
			if (frm.doc.item_code) {
				frm.trigger("fetch_item_statistics");
			}
		});
		
		frm.stats_to_date.$input.on("change", function() {
			if (frm.doc.item_code) {
				frm.trigger("fetch_item_statistics");
			}
		});
	},

	fetch_item_statistics: function(frm) {
		const $statsContent = $(frm.wrapper).find(".mpc-stats-content");
		if (!$statsContent.length) return;
		
		let fromDate = frm.stats_from_date ? frm.stats_from_date.get_value() : null;
		let toDate = frm.stats_to_date ? frm.stats_to_date.get_value() : null;
		
		if (!toDate) {
			toDate = frappe.datetime.get_today();
		}
		if (!fromDate) {
			fromDate = frappe.datetime.add_months(toDate, -6);
		}
		
		$statsContent.html('<div class="text-muted"><i class="fa fa-spinner fa-spin"></i> Loading statistics...</div>');
		
		frappe.call({
			method: "material_price_control.material_price_control.guard.get_item_statistics",
			args: {
				item_code: frm.doc.item_code,
				warehouse: frm.doc.warehouse || null,
				from_date: fromDate,
				to_date: toDate
			},
			callback: function(r) {
				if (r.message && !r.message.error) {
					frm.events.render_statistics(frm, r.message);
				} else {
					$statsContent.html('<div class="text-muted">No data available</div>');
				}
			},
			error: function() {
				$statsContent.html('<div class="text-muted text-danger">Error loading statistics</div>');
			}
		});
	},

	render_statistics: function(frm, data) {
		const $statsContent = $(frm.wrapper).find(".mpc-stats-content");
		if (!$statsContent.length) return;
		
		const stats = data.statistics || {};
		const count = stats.count || 0;
		
		let html = '';
		
		if (count === 0) {
			html = '<div class="text-muted">No historical data found for this item/warehouse combination in the selected date range</div>';
		} else {
			const mean = stats.mean ? stats.mean.toFixed(2) : "0.00";
			const stdDev = stats.std_dev ? stats.std_dev.toFixed(2) : "0.00";
			const ucl = stats.ucl ? stats.ucl.toFixed(2) : "0.00";
			const lcl = stats.lcl ? stats.lcl.toFixed(2) : "0.00";
			
			// Calculate coefficient of variation (CV) for context
			const cv = stats.mean > 0 ? ((stats.std_dev / stats.mean) * 100).toFixed(1) : 0;
			let cvNote = '';
			if (cv < 10) {
				cvNote = '<span class="text-success">Prices are very consistent</span>';
			} else if (cv < 25) {
				cvNote = '<span class="text-warning">Moderate price variation</span>';
			} else {
				cvNote = '<span class="text-danger">High price variation - review suppliers</span>';
			}
			
			// Data reliability note
			let reliabilityNote = '';
			if (count < 10) {
				reliabilityNote = '<span class="badge badge-warning">Low data - use with caution</span>';
			} else if (count < 30) {
				reliabilityNote = '<span class="badge badge-info">Moderate data</span>';
			} else {
				reliabilityNote = '<span class="badge badge-success">Good data reliability</span>';
			}
			
			html = `
				<div class="row">
					<div class="col-md-5">
						<table class="table table-sm table-bordered mb-0">
							<tbody>
								<tr>
									<td><strong>Data Points</strong></td>
									<td class="text-right">${count} ${reliabilityNote}</td>
								</tr>
								<tr class="table-primary">
									<td><strong>Mean (μ)</strong></td>
									<td class="text-right font-weight-bold">₹${mean}</td>
								</tr>
								<tr>
									<td><strong>Std Dev (σ)</strong></td>
									<td class="text-right">₹${stdDev} <small class="text-muted">(${cv}% of mean)</small></td>
								</tr>
								<tr>
									<td><strong>UCL (μ+2σ)</strong></td>
									<td class="text-right text-warning">₹${ucl}</td>
								</tr>
								<tr>
									<td><strong>LCL (μ-2σ)</strong></td>
									<td class="text-right text-warning">₹${lcl}</td>
								</tr>
							</tbody>
						</table>
						<div class="small mt-2">${cvNote}</div>
					</div>
					<div class="col-md-7">
						<div class="alert alert-primary mb-2" style="font-size: 12px;">
							<strong>📊 Recommended Settings:</strong><br/>
							<table class="mt-1" style="font-size: 12px;">
								<tr>
									<td style="padding-right: 10px;">Expected Rate:</td>
									<td><strong>₹${mean}</strong> <small>(the average)</small></td>
								</tr>
								<tr>
									<td>Min Rate:</td>
									<td><strong>₹${lcl}</strong> <small>(flags unusually low)</small></td>
								</tr>
								<tr>
									<td>Max Rate:</td>
									<td><strong>₹${ucl}</strong> <small>(flags unusually high)</small></td>
								</tr>
							</table>
						</div>
						<div class="d-flex" style="gap: 8px;">
							<button class="btn btn-xs btn-primary mpc-apply-mean-btn" data-mean="${stats.mean}">
								<i class="fa fa-magic"></i> Apply Mean as Expected Rate
							</button>
							<button class="btn btn-xs btn-default mpc-apply-all-btn" 
								data-mean="${stats.mean}" 
								data-min="${stats.lcl}" 
								data-max="${stats.ucl}">
								<i class="fa fa-bolt"></i> Apply All Suggested Values
							</button>
						</div>
						<div class="text-muted small mt-2">
							${data.warehouse ? `Warehouse: ${data.warehouse}` : 'All Warehouses'}
						</div>
					</div>
				</div>
			`;
		}
		
		$statsContent.html(html);
		
		// Bind click events for buttons
		$statsContent.find(".mpc-apply-mean-btn").on("click", function() {
			const mean = parseFloat($(this).data("mean"));
			if (mean && mean > 0) {
				frm.set_value("expected_rate", mean);
				frappe.show_alert({
					message: __("Expected Rate set to historical mean"),
					indicator: "green"
				});
			}
		});
		
		$statsContent.find(".mpc-apply-all-btn").on("click", function() {
			const mean = parseFloat($(this).data("mean"));
			const min = parseFloat($(this).data("min"));
			const max = parseFloat($(this).data("max"));
			
			if (mean && mean > 0) {
				frm.set_value("expected_rate", mean);
			}
			if (min && min > 0) {
				frm.set_value("min_rate", min);
			}
			if (max && max > 0) {
				frm.set_value("max_rate", max);
			}
			
			frappe.show_alert({
				message: __("Applied Mean, Min, and Max rates from historical data"),
				indicator: "green"
			});
		});
	},

	clear_statistics: function(frm) {
		const $statsContent = $(frm.wrapper).find(".mpc-stats-content");
		if ($statsContent.length) {
			$statsContent.html('<div class="text-muted">Select an item to view historical statistics</div>');
		}
	}
});
