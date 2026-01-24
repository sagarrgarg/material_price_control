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
		
		this.setupPage();
		this.setupFilters();
		this.bindEvents();
		this.loadDashboard();
	}

	setupPage() {
		// Create main container with filters
		this.page.main.html(`
			<div class="cost-valuation-chart-container">
				<!-- Filters Section -->
				<div class="filter-section frappe-card mb-4 p-3">
					<div class="row align-items-end">
						<div class="col-md-4">
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
						<div class="col-md-2">
							<button class="btn btn-primary btn-sm btn-block" id="refresh-chart-btn">
								<i class="fa fa-refresh"></i> ${__("Refresh")}
							</button>
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
						<div id="chart-stats" class="chart-stats text-muted small"></div>
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
					<h5 class="text-muted mb-3">
						<i class="fa fa-table"></i> ${__("Data Points")}
					</h5>
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
					to_date: toDate
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
			
			if (dp.is_anomaly) {
				anomalyData.push({
					value: point,
					itemStyle: {
						color: dp.severity === "Severe" ? "#ee6666" : "#fac858"
					},
					voucher_type: dp.voucher_type,
					voucher_no: dp.voucher_no,
					severity: dp.severity
				});
			} else {
				normalData.push({
					value: point,
					voucher_type: dp.voucher_type,
					voucher_no: dp.voucher_no
				});
			}
		});

		// Prepare control lines
		const stats = data.statistics;
		const rule = data.rule;
		const minDate = dates[0];
		const maxDate = dates[dates.length - 1];

		// Build series
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
						html += `${__("Rate")}: ₹${params.value[1].toFixed(2)}<br/>`;
						if (d.voucher_type) {
							html += `${__("Voucher")}: ${d.voucher_type}<br/>`;
							html += `${__("No")}: ${d.voucher_no}<br/>`;
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
	}

	renderStats() {
		const stats = this.chartData.statistics;
		const rule = this.chartData.rule;
		
		let html = `
			<div class="mb-1">
				<span class="badge badge-secondary mr-2">${__("Points")}: ${stats.count}</span>
				<span class="badge badge-success mr-2">${__("Mean")}: ₹${stats.mean}</span>
				<span class="badge badge-info mr-2">${__("Std Dev")}: ₹${stats.std_dev}</span>
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
			return;
		}

		let html = `
			<div class="table-responsive">
				<table class="table table-bordered table-hover table-sm">
					<thead class="thead-light">
						<tr>
							<th>${__("Date")}</th>
							<th>${__("Rate (₹)")}</th>
							<th>${__("Voucher Type")}</th>
							<th>${__("Voucher No")}</th>
							<th>${__("Warehouse")}</th>
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
			
			html += `
				<tr class="${statusClass}">
					<td>${frappe.datetime.str_to_user(dp.date)}</td>
					<td class="text-right">₹${dp.rate.toFixed(2)}</td>
					<td>${dp.voucher_type}</td>
					<td><a href="/app/${voucherSlug}/${dp.voucher_no}" target="_blank">${dp.voucher_no}</a></td>
					<td>${dp.warehouse || "-"}</td>
					<td class="text-center">${statusBadge}</td>
				</tr>
			`;
		});

		html += "</tbody></table></div>";
		$("#data-table").html(html);
	}
}
