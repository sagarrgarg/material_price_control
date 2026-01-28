// Copyright (c) 2026, Material Price Control and Contributors
// License: MIT

frappe.pages["cost-valuation-chart"].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Cost Valuation Control Chart"),
		single_column: true
	});

	// Store references
	wrapper.page = page;
	wrapper.chart_page = new CostValuationChart(wrapper);
};

frappe.pages["cost-valuation-chart"].on_page_show = function(wrapper) {
	// Refresh dashboard when page is shown
	if (wrapper.chart_page) {
		wrapper.chart_page.loadDashboard();
	}
};


class CostValuationChart {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.chart = null;
		this.chartData = null;
		this.settings = {};
		
		this.setupPage();
		this.setupFilters();
		this.bindEvents();
		this.loadSettings();
		this.loadDashboard();
	}

	async loadSettings() {
		// Load settings to get default for include_internal_suppliers
		try {
			const response = await frappe.call({
				method: "material_price_control.material_price_control.guard.get_chart_settings"
			});
			if (response.message) {
				this.settings = response.message;
				// Set checkbox to match setting
				const checkbox = this.page.main.find("#include-internal-suppliers");
				checkbox.prop("checked", this.settings.include_internal_suppliers ? true : false);
			}
		} catch (error) {
			console.error("Error loading settings:", error);
		}
	}

	setupPage() {
		// Create main container with filters
		this.page.main.html(`
			<div class="cost-valuation-chart-container">
				<!-- Filters Section -->
				<div class="filter-section frappe-card mb-4 p-3">
					<div class="row align-items-end">
						<div class="col-md-3">
							<div class="form-group mb-0">
								<label class="control-label">${__("Item")} <span class="text-danger">*</span></label>
								<div id="item-filter"></div>
							</div>
						</div>
						<div class="col-md-2">
							<div class="form-group mb-0">
								<label class="control-label">${__("From Date")}</label>
								<div id="from-date-filter"></div>
							</div>
						</div>
						<div class="col-md-2">
							<div class="form-group mb-0">
								<label class="control-label">${__("To Date")}</label>
								<div id="to-date-filter"></div>
							</div>
						</div>
						<div class="col-md-3">
							<div class="form-group mb-0">
								<div class="custom-control custom-checkbox mt-4">
									<input type="checkbox" class="custom-control-input" id="include-internal-suppliers">
									<label class="custom-control-label" for="include-internal-suppliers">
										${__("Include Internal Suppliers")}
									</label>
								</div>
							</div>
						</div>
						<div class="col-md-2">
							<button class="btn btn-primary btn-sm btn-block" id="refresh-chart-btn">
								<i class="fa fa-refresh"></i> ${__("Refresh")}
							</button>
						</div>
					</div>
				</div>

				<!-- Method Description (Collapsible) -->
				<div class="method-section frappe-card mb-4">
					<div class="method-header p-3" style="cursor: pointer;" id="toggle-method-desc">
						<h6 class="mb-0 d-flex justify-content-between align-items-center">
							<span><i class="fa fa-info-circle text-info"></i> ${__("How This Chart Works")}</span>
							<i class="fa fa-chevron-down" id="method-chevron"></i>
						</h6>
					</div>
					<div class="method-body p-3 border-top" id="method-description" style="display: none;">
						<div class="row">
							<div class="col-md-6">
								<h6 class="font-weight-bold">${__("Data Source")}</h6>
								<ul class="small mb-3">
									<li><strong>${__("Source")}:</strong> Stock Ledger Entry (incoming qty > 0)</li>
									<li><strong>${__("Vouchers")}:</strong> Purchase Receipt, Purchase Invoice, Stock Entry, Stock Reconciliation</li>
									<li><strong>${__("Rate")}:</strong> <code>incoming_rate</code>, fallback to <code>|stock_value_difference / actual_qty|</code></li>
								</ul>
								
								<h6 class="font-weight-bold">${__("Statistical Measures")}</h6>
								<ul class="small mb-3">
									<li><strong>${__("Mean")} (μ):</strong> Σx / n</li>
									<li><strong>${__("RMS")}:</strong> √(Σx² / n)</li>
									<li><strong>${__("Std Dev")} (σ):</strong> √(Σ(x-μ)² / n)</li>
									<li><strong>${__("UCL")}:</strong> μ + 2σ (Upper Control Limit)</li>
									<li><strong>${__("LCL")}:</strong> μ - 2σ (Lower Control Limit, min 0)</li>
								</ul>
							</div>
							<div class="col-md-6">
								<h6 class="font-weight-bold">${__("Variance Calculation")}</h6>
								<ul class="small mb-3">
									<li><strong>${__("Reference Rate")}:</strong> Rule expected rate (if exists), otherwise Mean</li>
									<li><strong>${__("Variance Amount")} (Δ₹):</strong> rate - reference_rate</li>
									<li><strong>${__("Variance Percent")} (|Δ%|):</strong> |rate - reference| / reference × 100</li>
								</ul>
								
								<h6 class="font-weight-bold">${__("Internal Supplier Filter")}</h6>
								<p class="small mb-0">
									Purchase Receipts and Purchase Invoices from suppliers marked as 
									<code>is_internal_supplier</code> or <code>is_bns_internal_supplier</code> are 
									filtered based on the <strong>Include Internal Suppliers</strong> setting in 
									<a href="/app/cost-valuation-settings" target="_blank">Cost Valuation Settings</a>. 
									This setting also controls whether validation is performed during document submission.
									The checkbox above reflects the current setting value.
								</p>
							</div>
						</div>
					</div>
				</div>

				<!-- Dashboard Summary -->
				<div class="dashboard-section frappe-card mb-4 p-3">
					<h5 class="text-muted mb-3">
						<i class="fa fa-dashboard"></i> ${__("Top Items with Anomalies (Last 30 Days)")}
					</h5>
					<div id="anomaly-summary" class="anomaly-summary">
						<div class="text-center text-muted p-3">
							<i class="fa fa-spinner fa-spin"></i> ${__("Loading...")}
						</div>
					</div>
				</div>
				
				<!-- Main Chart -->
				<div class="chart-section frappe-card mb-4 p-3">
					<div class="chart-header d-flex justify-content-between align-items-center mb-3">
						<h5 class="text-muted mb-0">
							<i class="fa fa-line-chart"></i> ${__("Rate Control Chart")}
						</h5>
						<div class="d-flex align-items-center">
							<div id="chart-stats" class="chart-stats text-muted small mr-3"></div>
							<button class="btn btn-xs btn-default" id="download-chart-btn" title="${__("Download Chart as PNG")}" style="display: none;">
								<i class="fa fa-download"></i> ${__("Chart")}
							</button>
						</div>
					</div>
					<div id="control-chart" style="width: 100%; height: 450px;">
						<div class="text-muted text-center p-5">
							<i class="fa fa-arrow-up fa-2x mb-3 d-block"></i>
							${__("Select an item above to view the control chart")}
						</div>
					</div>
				</div>
				
				<!-- Data Table -->
				<div class="table-section frappe-card p-3">
					<div class="d-flex justify-content-between align-items-center mb-3">
						<h5 class="text-muted mb-0">
							<i class="fa fa-table"></i> ${__("Data Points")}
						</h5>
						<div class="d-flex align-items-center" id="table-controls" style="display: none;">
							<input type="text" class="form-control form-control-sm mr-2" id="table-search" 
								placeholder="${__("Search...")}" style="width: 200px;">
							<button class="btn btn-xs btn-default" id="download-csv-btn" title="${__("Download as CSV")}">
								<i class="fa fa-download"></i> ${__("Download CSV")}
							</button>
						</div>
					</div>
					<div id="data-table">
						<div class="text-muted text-center p-3">
							${__("No data to display")}
						</div>
					</div>
				</div>
			</div>
		`);
	}

	setupFilters() {
		// Item Link field
		this.itemField = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				fieldname: "item_code",
				options: "Item",
				placeholder: __("Select Item...")
			},
			parent: this.page.main.find("#item-filter"),
			render_input: true
		});
		this.itemField.refresh();

		// From Date field
		this.fromDateField = frappe.ui.form.make_control({
			df: {
				fieldtype: "Date",
				fieldname: "from_date",
				default: frappe.datetime.add_months(frappe.datetime.get_today(), -6)
			},
			parent: this.page.main.find("#from-date-filter"),
			render_input: true
		});
		this.fromDateField.refresh();
		this.fromDateField.set_value(frappe.datetime.add_months(frappe.datetime.get_today(), -6));

		// To Date field
		this.toDateField = frappe.ui.form.make_control({
			df: {
				fieldtype: "Date",
				fieldname: "to_date",
				default: frappe.datetime.get_today()
			},
			parent: this.page.main.find("#to-date-filter"),
			render_input: true
		});
		this.toDateField.refresh();
		this.toDateField.set_value(frappe.datetime.get_today());
	}

	bindEvents() {
		const self = this;

		// Refresh button click
		this.page.main.find("#refresh-chart-btn").on("click", () => {
			this.refreshChart();
		});

		// Item field change - auto refresh
		this.itemField.$input.on("change", () => {
			setTimeout(() => this.refreshChart(), 100);
		});

		// Enter key on item field
		this.itemField.$input.on("keypress", (e) => {
			if (e.which === 13) {
				this.refreshChart();
			}
		});

		// Include internal suppliers checkbox
		this.page.main.find("#include-internal-suppliers").on("change", () => {
			this.refreshChart();
		});

		// Toggle method description
		this.page.main.find("#toggle-method-desc").on("click", () => {
			const body = this.page.main.find("#method-description");
			const chevron = this.page.main.find("#method-chevron");
			body.slideToggle(200);
			chevron.toggleClass("fa-chevron-down fa-chevron-up");
		});

		// Download chart as PNG
		this.page.main.find("#download-chart-btn").on("click", () => {
			this.downloadChart();
		});

		// Download CSV
		this.page.main.find("#download-csv-btn").on("click", () => {
			this.downloadData("csv");
		});

		// Table search
		this.page.main.find("#table-search").on("input", function() {
			self.filterTable($(this).val());
		});
	}

	downloadChart() {
		if (!this.chart) return;
		
		const url = this.chart.getDataURL({
			type: "png",
			pixelRatio: 2,
			backgroundColor: "#fff"
		});
		
		const link = document.createElement("a");
		link.download = `control-chart-${this.chartData.item_code}-${frappe.datetime.get_today()}.png`;
		link.href = url;
		link.click();
	}

	downloadData() {
		if (!this.chartData || !this.chartData.data_points) return;
		
		const data = this.chartData.data_points;
		const itemCode = this.chartData.item_code;
		
		// Prepare data for export
		const exportData = data.map(dp => ({
			"Date": dp.date,
			"Rate": dp.rate,
			"Reference Rate": dp.reference_rate,
			"Reference Source": dp.reference_source || "",
			"Variance (₹)": dp.variance_amount,
			"Variance (%)": dp.variance_pct,
			"Supplier": dp.supplier || "",
			"Internal": dp.is_internal_supplier ? "Yes" : "No",
			"Voucher Type": dp.voucher_type,
			"Voucher No": dp.voucher_no,
			"Warehouse": dp.warehouse || "",
			"Created By": dp.created_by || "",
			"Status": dp.severity || "Normal"
		}));
		
		this.downloadCSV(exportData, `control-chart-${itemCode}-${frappe.datetime.get_today()}.csv`);
	}

	downloadCSV(data, filename) {
		if (!data.length) return;
		
		const headers = Object.keys(data[0]);
		const csvContent = [
			headers.join(","),
			...data.map(row => headers.map(h => {
				let val = row[h];
				if (val === null || val === undefined) val = "";
				// Escape quotes and wrap in quotes if contains comma
				val = String(val).replace(/"/g, '""');
				if (val.includes(",") || val.includes('"') || val.includes("\n")) {
					val = `"${val}"`;
				}
				return val;
			}).join(","))
		].join("\n");
		
		const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
		const link = document.createElement("a");
		link.href = URL.createObjectURL(blob);
		link.download = filename;
		link.click();
	}

	scrollToTableRow(voucherType, voucherNo) {
		const rowId = `row-${voucherType.replace(/ /g, "-")}-${voucherNo}`;
		const $row = this.page.main.find(`#${rowId}`);
		
		if ($row.length) {
			// Remove highlight from all rows
			this.page.main.find("#data-points-table tbody tr").removeClass("table-info");
			
			// Highlight the target row
			$row.addClass("table-info");
			
			// Scroll to the row
			$row[0].scrollIntoView({ behavior: "smooth", block: "center" });
		}
	}

	filterTable(searchText) {
		const $table = this.page.main.find("#data-table table");
		if (!$table.length) return;
		
		const search = searchText.toLowerCase().trim();
		
		$table.find("tbody tr").each(function() {
			const $row = $(this);
			const text = $row.text().toLowerCase();
			$row.toggle(text.includes(search) || !search);
		});
	}

	async loadDashboard() {
		try {
			const data = await frappe.call({
				method: "material_price_control.material_price_control.guard.get_items_with_anomalies",
				args: {
					from_date: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
					to_date: frappe.datetime.get_today(),
					limit: 12
				}
			});

			if (data.message && data.message.length > 0) {
				this.renderAnomalySummary(data.message);
			} else {
				$("#anomaly-summary").html(`
					<div class="text-muted text-center p-3">
						<i class="fa fa-check-circle fa-2x mb-2 d-block text-success"></i>
						${__("No anomalies detected in the last month")}
					</div>
				`);
			}
		} catch (error) {
			console.error("Error loading dashboard:", error);
			$("#anomaly-summary").html(`
				<div class="text-muted text-center p-3">
					${__("Failed to load anomaly summary")}
				</div>
			`);
		}
	}

	renderAnomalySummary(items) {
		const self = this;
		let html = '<div class="row">';
		
		items.slice(0, 12).forEach(item => {
			const severeClass = item.severe_count > 0 ? "text-danger" : "text-muted";
			const warningClass = item.warning_count > 0 ? "text-warning" : "text-muted";
			const cardClass = item.severe_count > 0 ? "border-danger" : (item.warning_count > 0 ? "border-warning" : "");
			
			html += `
				<div class="col-lg-2 col-md-3 col-sm-4 col-6 mb-3">
					<div class="card h-100 item-card ${cardClass}" data-item="${item.item_code}" style="cursor: pointer;">
						<div class="card-body p-2 text-center">
							<div class="font-weight-bold text-truncate small" title="${item.item_code}">
								${item.item_code}
							</div>
							<div class="mt-2">
								<span class="${severeClass}" title="${__("Severe")}">
									<i class="fa fa-exclamation-circle"></i> ${item.severe_count || 0}
								</span>
								<span class="${warningClass} ml-2" title="${__("Warning")}">
									<i class="fa fa-warning"></i> ${item.warning_count || 0}
								</span>
							</div>
							<div class="small text-muted mt-1">
								${__("Total")}: ${item.anomaly_count}
							</div>
						</div>
					</div>
				</div>
			`;
		});
		
		html += "</div>";
		$("#anomaly-summary").html(html);

		// Bind click events to cards
		$(".item-card").on("click", function() {
			const itemCode = $(this).data("item");
			self.itemField.set_value(itemCode);
			setTimeout(() => self.refreshChart(), 100);
		});
	}

	async refreshChart() {
		const itemCode = this.itemField.get_value();
		const fromDate = this.fromDateField.get_value();
		const toDate = this.toDateField.get_value();
		const includeInternal = this.page.main.find("#include-internal-suppliers").is(":checked") ? 1 : 0;

		if (!itemCode) {
			$("#control-chart").html(`
				<div class="text-muted text-center p-5">
					<i class="fa fa-arrow-up fa-2x mb-3 d-block"></i>
					${__("Select an item above to view the control chart")}
				</div>
			`);
			$("#chart-stats").html("");
			$("#data-table").html(`
				<div class="text-muted text-center p-3">
					${__("No data to display")}
				</div>
			`);
			return;
		}

		// Show loading
		$("#control-chart").html(`
			<div class="text-center p-5">
				<i class="fa fa-spinner fa-spin fa-2x"></i>
				<div class="mt-2">${__("Loading chart data...")}</div>
			</div>
		`);

		try {
			const response = await frappe.call({
				method: "material_price_control.material_price_control.guard.get_chart_data",
				args: {
					item_code: itemCode,
					from_date: fromDate,
					to_date: toDate,
					include_internal_suppliers: includeInternal
				}
			});

			if (response.message) {
				this.chartData = response.message;
				this.renderChart();
				this.renderStats();
				this.renderDataTable();
			}
		} catch (error) {
			frappe.msgprint({
				title: __("Error"),
				indicator: "red",
				message: __("Failed to load chart data")
			});
			console.error("Error loading chart data:", error);
			$("#control-chart").html(`
				<div class="text-danger text-center p-5">
					<i class="fa fa-exclamation-triangle fa-2x mb-3 d-block"></i>
					${__("Failed to load chart data")}
				</div>
			`);
		}
	}

	renderChart() {
		const container = document.getElementById("control-chart");
		if (!container) return;

		const data = this.chartData;
		if (!data.data_points || data.data_points.length === 0) {
			container.innerHTML = `
				<div class="text-muted text-center p-5">
					<i class="fa fa-info-circle fa-2x mb-3 d-block"></i>
					${__("No data available for the selected period")}
				</div>
			`;
			return;
		}

		// Clear container first
		container.innerHTML = "";

		// Initialize ECharts instance
		if (this.chart) {
			this.chart.dispose();
		}
		this.chart = echarts.init(container);

		// Handle resize
		const resizeHandler = () => {
			if (this.chart) {
				this.chart.resize();
			}
		};
		window.removeEventListener("resize", resizeHandler);
		window.addEventListener("resize", resizeHandler);

		// Prepare data series
		const normalData = [];
		const anomalyData = [];
		const dates = [];

		data.data_points.forEach(dp => {
			const point = [dp.date, dp.rate];
			dates.push(dp.date);
			
			// Build data object with all fields for tooltip
			const dataObj = {
				value: point,
				voucher_type: dp.voucher_type,
				voucher_no: dp.voucher_no,
				supplier: dp.supplier,
				is_internal_supplier: dp.is_internal_supplier,
				created_by: dp.created_by,
				reference_rate: dp.reference_rate,
				reference_source: dp.reference_source,
				variance_amount: dp.variance_amount,
				variance_pct: dp.variance_pct,
				severity: dp.severity
			};
			
			if (dp.is_anomaly) {
				dataObj.itemStyle = {
					color: dp.severity === "Severe" ? "#ee6666" : "#fac858"
				};
				anomalyData.push(dataObj);
			} else {
				normalData.push(dataObj);
			}
		});

		// Prepare control lines
		const stats = data.statistics;
		const rule = data.rule;
		const minDate = dates[0];
		const maxDate = dates[dates.length - 1];

		// Build series - include both Mean and RMS lines
		const series = [
			// Normal points
			{
				name: __("Normal"),
				type: "scatter",
				data: normalData,
				symbolSize: 10,
				itemStyle: { color: "#5470c6" }
			},
			// Anomaly points
			{
				name: __("Anomaly"),
				type: "scatter",
				data: anomalyData,
				symbolSize: 14,
				itemStyle: { color: "#ee6666" }
			},
			// Mean line
			{
				name: __("Mean (μ)"),
				type: "line",
				data: [[minDate, stats.mean], [maxDate, stats.mean]],
				lineStyle: { color: "#91cc75", width: 2 },
				symbol: "none"
			},
			// RMS line
			{
				name: __("RMS"),
				type: "line",
				data: [[minDate, stats.rms], [maxDate, stats.rms]],
				lineStyle: { color: "#9b59b6", width: 2, type: "dotted" },
				symbol: "none"
			},
			// UCL line
			{
				name: __("UCL (μ+2σ)"),
				type: "line",
				data: [[minDate, stats.ucl], [maxDate, stats.ucl]],
				lineStyle: { color: "#fac858", width: 2, type: "dashed" },
				symbol: "none"
			},
			// LCL line
			{
				name: __("LCL (μ-2σ)"),
				type: "line",
				data: [[minDate, stats.lcl], [maxDate, stats.lcl]],
				lineStyle: { color: "#fac858", width: 2, type: "dashed" },
				symbol: "none"
			}
		];

		// Add rule lines if available
		if (rule) {
			if (rule.expected_rate) {
				series.push({
					name: __("Expected Rate"),
					type: "line",
					data: [[minDate, rule.expected_rate], [maxDate, rule.expected_rate]],
					lineStyle: { color: "#73c0de", width: 2, type: "dotted" },
					symbol: "none"
				});
			}
			if (rule.min_rate) {
				series.push({
					name: __("Min Rate (Hard)"),
					type: "line",
					data: [[minDate, rule.min_rate], [maxDate, rule.min_rate]],
					lineStyle: { color: "#ee6666", width: 2, type: "solid" },
					symbol: "none"
				});
			}
			if (rule.max_rate) {
				series.push({
					name: __("Max Rate (Hard)"),
					type: "line",
					data: [[minDate, rule.max_rate], [maxDate, rule.max_rate]],
					lineStyle: { color: "#ee6666", width: 2, type: "solid" },
					symbol: "none"
				});
			}
		}

		// Chart options
		const option = {
			title: {
				text: __("Control Chart: {0}", [data.item_code]),
				subtext: __("Period: {0} to {1}", [data.from_date, data.to_date]),
				left: "center",
				textStyle: { fontSize: 16, fontWeight: "bold" }
			},
			tooltip: {
				trigger: "item",
				formatter: function(params) {
					if (params.seriesType === "scatter") {
						const d = params.data;
						let html = `<strong>${params.value[0]}</strong><br/>`;
						html += `<b>${__("Rate")}:</b> ₹${params.value[1].toFixed(2)}<br/>`;
						
						// Show reference and variance
						if (d.reference_rate !== null) {
							html += `<b>${__("Reference")}:</b> ₹${d.reference_rate.toFixed(2)} (${d.reference_source})<br/>`;
							const sign = d.variance_amount >= 0 ? "+" : "";
							html += `<b>${__("Variance")}:</b> ${sign}₹${d.variance_amount.toFixed(2)} (${d.variance_pct.toFixed(1)}%)<br/>`;
						}
						
						// Show supplier info for PR/PI
						if (d.supplier) {
							html += `<b>${__("Supplier")}:</b> ${d.supplier}`;
							if (d.is_internal_supplier) {
								html += ` <span style="color: #9b59b6;">(Internal)</span>`;
							}
							html += `<br/>`;
						}
						
						if (d.voucher_type) {
							html += `<b>${__("Voucher")}:</b> ${d.voucher_type} / ${d.voucher_no}<br/>`;
						}
						
						// Show created by
						if (d.created_by) {
							html += `<b>${__("Created By")}:</b> ${d.created_by}<br/>`;
						}
						
						if (d.severity) {
							const color = d.severity === "Severe" ? "#ee6666" : "#fac858";
							html += `<span style="color: ${color}; font-weight: bold;">${__("Status")}: ${d.severity}</span>`;
						} else {
							html += `<span style="color: #91cc75;">${__("Status")}: Normal</span>`;
						}
						return html;
					}
					return `${params.seriesName}: ₹${params.value[1].toFixed(2)}`;
				}
			},
			legend: {
				data: series.map(s => s.name),
				bottom: 0,
				type: "scroll"
			},
			grid: {
				left: "3%",
				right: "4%",
				bottom: "15%",
				top: "15%",
				containLabel: true
			},
			xAxis: {
				type: "time",
				name: __("Date"),
				nameLocation: "middle",
				nameGap: 30,
				axisLabel: {
					formatter: function(value) {
						return frappe.datetime.str_to_user(new Date(value).toISOString().split("T")[0]);
					}
				}
			},
			yAxis: {
				type: "value",
				name: __("Rate (₹)"),
				nameLocation: "middle",
				nameGap: 60,
				axisLabel: {
					formatter: "₹{value}"
				}
			},
			series: series,
			dataZoom: [
				{
					type: "inside",
					start: 0,
					end: 100
				},
				{
					type: "slider",
					start: 0,
					end: 100,
					bottom: 35
				}
			]
		};

		this.chart.setOption(option, true);

		// Add click handler for chart points
		const self = this;
		this.chart.off("click"); // Remove existing handlers
		this.chart.on("click", function(params) {
			if (params.seriesType === "scatter" && params.data) {
				const d = params.data;
				if (d.voucher_type && d.voucher_no) {
					self.scrollToTableRow(d.voucher_type, d.voucher_no);
				}
			}
		});
	}

	renderStats() {
		const stats = this.chartData.statistics;
		const rule = this.chartData.rule;
		
		let html = `
			<div class="mb-1">
				<span class="badge badge-secondary mr-2">${__("Points")}: ${stats.count}</span>
				<span class="badge badge-success mr-2">${__("Mean")}: ₹${stats.mean}</span>
				<span class="badge mr-2" style="background-color: #9b59b6; color: white;">${__("RMS")}: ₹${stats.rms}</span>
				<span class="badge badge-info mr-2">${__("σ")}: ₹${stats.std_dev}</span>
				<span class="badge badge-warning mr-2">${__("UCL")}: ₹${stats.ucl}</span>
				<span class="badge badge-warning">${__("LCL")}: ₹${stats.lcl}</span>
			</div>
		`;
		
		if (rule) {
			html += `<div class="mt-1">`;
			html += `<span class="badge badge-primary mr-1">${__("Rule")}: ${rule.rule_source}</span>`;
			if (rule.expected_rate) {
				html += `<span class="badge badge-light mr-1">${__("Expected")}: ₹${rule.expected_rate}</span>`;
			}
			if (rule.min_rate) {
				html += `<span class="badge badge-danger mr-1">${__("Min")}: ₹${rule.min_rate}</span>`;
			}
			if (rule.max_rate) {
				html += `<span class="badge badge-danger">${__("Max")}: ₹${rule.max_rate}</span>`;
			}
			html += `</div>`;
		} else {
			html += `<div class="mt-1"><span class="badge badge-secondary">${__("No rule defined - using statistical limits")}</span></div>`;
		}
		
		$("#chart-stats").html(html);
	}

	renderDataTable() {
		const data = this.chartData.data_points;
		if (!data || data.length === 0) {
			$("#data-table").html(`
				<div class="text-muted text-center p-3">
					${__("No data to display")}
				</div>
			`);
			// Hide controls
			this.page.main.find("#table-controls").hide();
			this.page.main.find("#download-chart-btn").hide();
			return;
		}

		// Show controls
		this.page.main.find("#table-controls").show();
		this.page.main.find("#download-chart-btn").show();
		this.page.main.find("#table-search").val("");

		let html = `
			<div class="table-responsive">
				<table class="table table-bordered table-hover table-sm" id="data-points-table">
					<thead class="thead-light">
						<tr>
							<th>${__("Date")}</th>
							<th>${__("Rate (₹)")}</th>
							<th>${__("Reference")}</th>
							<th>${__("Δ₹")}</th>
							<th>${__("|Δ%|")}</th>
							<th>${__("Supplier")}</th>
							<th>${__("Voucher")}</th>
							<th>${__("Warehouse")}</th>
							<th>${__("Created By")}</th>
							<th>${__("Status")}</th>
						</tr>
					</thead>
					<tbody>
		`;

		data.forEach(dp => {
			const statusClass = dp.severity === "Severe" ? "table-danger" : 
			                   dp.severity === "Warning" ? "table-warning" : "";
			const statusBadge = dp.severity === "Severe" ? 
				`<span class="badge badge-danger">${dp.severity}</span>` :
				dp.severity === "Warning" ?
				`<span class="badge badge-warning">${dp.severity}</span>` :
				`<span class="badge badge-success">${__("Normal")}</span>`;
			
			const voucherSlug = dp.voucher_type.toLowerCase().replace(/ /g, "-");
			
			// Unique row ID for scroll-to functionality
			const rowId = `row-${dp.voucher_type.replace(/ /g, "-")}-${dp.voucher_no}`;
			
			// Format variance
			const varianceSign = dp.variance_amount >= 0 ? "+" : "";
			const varianceAmount = dp.variance_amount !== null ? `${varianceSign}₹${dp.variance_amount.toFixed(2)}` : "-";
			const variancePct = dp.variance_pct !== null ? `${dp.variance_pct.toFixed(1)}%` : "-";
			const refRate = dp.reference_rate !== null ? `₹${dp.reference_rate.toFixed(2)}` : "-";
			const refSource = dp.reference_source ? `<small class="text-muted">(${dp.reference_source})</small>` : "";
			
			// Supplier with internal indicator
			let supplierDisplay = dp.supplier || "-";
			if (dp.is_internal_supplier) {
				supplierDisplay = `${dp.supplier} <span class="badge badge-secondary">Int</span>`;
			}
			
			// Created by - show user full name
			const createdBy = dp.created_by || "-";
			
			html += `
				<tr id="${rowId}" class="${statusClass}">
					<td>${frappe.datetime.str_to_user(dp.date)}</td>
					<td class="text-right">₹${dp.rate.toFixed(2)}</td>
					<td class="text-right">${refRate} ${refSource}</td>
					<td class="text-right">${varianceAmount}</td>
					<td class="text-right">${variancePct}</td>
					<td>${supplierDisplay}</td>
					<td><a href="/app/${voucherSlug}/${dp.voucher_no}" target="_blank">${dp.voucher_type} / ${dp.voucher_no}</a></td>
					<td>${dp.warehouse || "-"}</td>
					<td>${createdBy}</td>
					<td class="text-center">${statusBadge}</td>
				</tr>
			`;
		});

		html += "</tbody></table></div>";
		$("#data-table").html(html);
	}
}
