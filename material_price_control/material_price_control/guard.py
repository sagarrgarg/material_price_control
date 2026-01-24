# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

"""
Material Price Control - Guard Module

This module provides hooks to check valuation rates on stock-in transactions
(Purchase Receipt, Purchase Invoice, Stock Entry) and detect anomalies.
"""

import math
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, nowdate


def check_purchase_receipt(doc, method):
	"""Check Purchase Receipt items for valuation anomalies"""
	settings = get_settings()
	if not settings or not settings.enabled:
		return

	for item in doc.items:
		if flt(item.qty) <= 0:
			continue

		incoming_rate = flt(item.valuation_rate)
		if not incoming_rate:
			continue

		check_item_rate(doc, item, incoming_rate, "Purchase Receipt", settings)


def check_purchase_invoice(doc, method):
	"""Check Purchase Invoice items for valuation anomalies (only if update_stock=1)"""
	settings = get_settings()
	if not settings or not settings.enabled:
		return

	if not doc.update_stock:
		return

	for item in doc.items:
		if flt(item.qty) <= 0:
			continue

		incoming_rate = flt(item.valuation_rate)
		if not incoming_rate:
			continue

		check_item_rate(doc, item, incoming_rate, "Purchase Invoice", settings)


def check_stock_entry(doc, method):
	"""Check Stock Entry items for valuation anomalies (only incoming items)"""
	settings = get_settings()
	if not settings or not settings.enabled:
		return

	for item in doc.items:
		# Only check items with target warehouse (incoming)
		if not item.t_warehouse or flt(item.transfer_qty) <= 0:
			continue

		incoming_rate = flt(item.valuation_rate)
		if not incoming_rate:
			continue

		check_item_rate(doc, item, incoming_rate, "Stock Entry", settings)


def check_item_rate(doc, item_row, incoming_rate, voucher_type, settings):
	"""
	Core logic to check if incoming rate is anomalous.
	
	Args:
		doc: Parent document (PR/PI/SE)
		item_row: Item row from child table
		incoming_rate: The valuation rate being checked
		voucher_type: Type of voucher (Purchase Receipt, Purchase Invoice, Stock Entry)
		settings: Cost Valuation Settings document
	"""
	expected = get_expected_rate(item_row.item_code)

	# Handle case when no rule exists
	if not expected:
		if getattr(settings, 'block_if_no_rule', False):
			if not can_bypass_block(settings):
				frappe.throw(
					_("Transaction blocked: No Cost Valuation Rule exists for Item {0}. "
					  "Please create a rule before proceeding.").format(
						frappe.bold(item_row.item_code)
					),
					title=_("Missing Cost Valuation Rule")
				)
		return

	# Calculate variance percentage
	variance_pct = calculate_variance(incoming_rate, expected["expected_rate"])

	# Get thresholds
	allowed_variance = flt(expected.get("allowed_variance_pct")) or flt(settings.default_variance_pct)
	severe_threshold = allowed_variance * flt(settings.severe_multiplier)

	# Determine severity and block reason
	severity, block_reason = determine_severity(
		incoming_rate, expected, variance_pct, allowed_variance, severe_threshold
	)

	if not severity:
		return  # Normal rate, no action needed

	# Log the anomaly
	log_anomaly(doc, item_row, incoming_rate, expected, variance_pct, severity, voucher_type)

	# Block if severe and blocking enabled
	if severity == "Severe" and settings.block_severe:
		if not can_bypass_block(settings):
			throw_anomaly_error(
				item_row, incoming_rate, expected, variance_pct,
				allowed_variance, severe_threshold, block_reason
			)


def determine_severity(incoming_rate, expected, variance_pct, allowed_variance, severe_threshold):
	"""
	Determine the severity of the anomaly.
	
	Returns:
		tuple: (severity, block_reason) or (None, None) if normal
	"""
	# Check hard bounds first
	if expected.get("min_rate") and incoming_rate < expected["min_rate"]:
		return "Severe", _("Rate ₹{0} is below minimum allowed rate ₹{1}").format(
			incoming_rate, expected["min_rate"]
		)
	
	if expected.get("max_rate") and incoming_rate > expected["max_rate"]:
		return "Severe", _("Rate ₹{0} is above maximum allowed rate ₹{1}").format(
			incoming_rate, expected["max_rate"]
		)
	
	# Check variance thresholds
	if variance_pct > severe_threshold:
		return "Severe", _("Variance {0:.1f}% exceeds severe threshold {1:.1f}%").format(
			variance_pct, severe_threshold
		)
	
	if variance_pct > allowed_variance:
		return "Warning", None
	
	return None, None


def throw_anomaly_error(item_row, incoming_rate, expected, variance_pct,
                        allowed_variance, severe_threshold, block_reason):
	"""Build and throw detailed error message for blocked transactions."""
	msg = _("Cost Valuation Anomaly for Item {0}").format(frappe.bold(item_row.item_code))
	msg += "<br><br>"
	msg += "<table style='width:100%; border-collapse: collapse;'>"
	msg += "<tr><td style='padding:4px;'><b>" + _("Incoming Rate") + ":</b></td>"
	msg += "<td style='padding:4px;'>₹{0}</td></tr>".format(incoming_rate)

	# Check if this is a hard bound violation or variance violation
	is_hard_bound_violation = (
		(expected.get("min_rate") and incoming_rate < expected["min_rate"]) or
		(expected.get("max_rate") and incoming_rate > expected["max_rate"])
	)

	if is_hard_bound_violation:
		# Show only hard bounds info - no variance details
		if expected.get("min_rate"):
			msg += "<tr><td style='padding:4px;'><b>" + _("Minimum Allowed") + ":</b></td>"
			msg += "<td style='padding:4px;'>₹{0}</td></tr>".format(expected["min_rate"])
		if expected.get("max_rate"):
			msg += "<tr><td style='padding:4px;'><b>" + _("Maximum Allowed") + ":</b></td>"
			msg += "<td style='padding:4px;'>₹{0}</td></tr>".format(expected["max_rate"])
	else:
		# Show variance-related info
		msg += "<tr><td style='padding:4px;'><b>" + _("Expected Rate") + ":</b></td>"
		msg += "<td style='padding:4px;'>₹{0}</td></tr>".format(expected["expected_rate"])
		msg += "<tr><td style='padding:4px;'><b>" + _("Variance") + ":</b></td>"
		msg += "<td style='padding:4px;'>{0:.1f}%</td></tr>".format(variance_pct)
		msg += "<tr><td style='padding:4px;'><b>" + _("Allowed Variance") + ":</b></td>"
		msg += "<td style='padding:4px;'>≤ {0:.1f}%</td></tr>".format(allowed_variance)
		msg += "<tr><td style='padding:4px;'><b>" + _("Severe Threshold") + ":</b></td>"
		msg += "<td style='padding:4px;'>> {0:.1f}%</td></tr>".format(severe_threshold)

	msg += "</table>"
	msg += "<br>"
	msg += "<b>" + _("Reason") + ":</b> " + block_reason
	msg += "<br><br>"
	msg += _("Please correct the rate or contact a user with bypass permissions.")

	frappe.throw(msg, title=_("Cost Valuation Anomaly - Blocked"))


def get_expected_rate(item_code):
	"""
	Get expected rate for an item.
	
	Resolution order:
	1. Item-level rule (exact match)
	2. Item Group rule
	3. None (no expectation)
	
	Args:
		item_code: The item code to look up
		
	Returns:
		dict with expected_rate, allowed_variance_pct, min_rate, max_rate or None
	"""
	# Check item-level rule first
	item_rule = frappe.db.get_value(
		"Cost Valuation Rule",
		{
			"rule_for": "Item",
			"item_code": item_code,
			"enabled": 1
		},
		["expected_rate", "allowed_variance_pct", "min_rate", "max_rate"],
		as_dict=True
	)

	if item_rule:
		return {
			"expected_rate": flt(item_rule.expected_rate),
			"allowed_variance_pct": flt(item_rule.allowed_variance_pct) if item_rule.allowed_variance_pct else None,
			"min_rate": flt(item_rule.min_rate) if item_rule.min_rate else None,
			"max_rate": flt(item_rule.max_rate) if item_rule.max_rate else None,
			"rule_source": "Item"
		}

	# Check item group rule
	item_group = frappe.db.get_value("Item", item_code, "item_group")
	if item_group:
		group_rule = frappe.db.get_value(
			"Cost Valuation Rule",
			{
				"rule_for": "Item Group",
				"item_group": item_group,
				"enabled": 1
			},
			["expected_rate", "allowed_variance_pct", "min_rate", "max_rate"],
			as_dict=True
		)

		if group_rule:
			return {
				"expected_rate": flt(group_rule.expected_rate),
				"allowed_variance_pct": flt(group_rule.allowed_variance_pct) if group_rule.allowed_variance_pct else None,
				"min_rate": flt(group_rule.min_rate) if group_rule.min_rate else None,
				"max_rate": flt(group_rule.max_rate) if group_rule.max_rate else None,
				"rule_source": "Item Group"
			}

	return None


def calculate_variance(incoming_rate, expected_rate):
	"""
	Calculate variance percentage between incoming and expected rates.
	
	Args:
		incoming_rate: The actual rate
		expected_rate: The expected rate
		
	Returns:
		Variance as percentage (0 if expected_rate is 0 or None)
	"""
	if not expected_rate or flt(expected_rate) == 0:
		return 0
	return abs(flt(incoming_rate) - flt(expected_rate)) / flt(expected_rate) * 100


def log_anomaly(doc, item_row, incoming_rate, expected, variance_pct, severity, voucher_type):
	"""
	Create Cost Anomaly Log entry.
	
	Args:
		doc: Parent document
		item_row: Item row from child table
		incoming_rate: The valuation rate that triggered the anomaly
		expected: Expected rate dict from get_expected_rate()
		variance_pct: Calculated variance percentage
		severity: 'Warning' or 'Severe'
		voucher_type: Type of voucher
	"""
	# Safe warehouse access - PR/PI use 'warehouse', SE uses 't_warehouse'
	warehouse = getattr(item_row, 'warehouse', None) or getattr(item_row, 't_warehouse', None)
	
	anomaly = frappe.get_doc({
		"doctype": "Cost Anomaly Log",
		"voucher_type": voucher_type,
		"voucher_no": doc.name,
		"item_code": item_row.item_code,
		"warehouse": warehouse,
		"incoming_rate": incoming_rate,
		"expected_rate": expected["expected_rate"],
		"variance_pct": variance_pct,
		"severity": severity,
		"status": "Open"
	})
	anomaly.insert(ignore_permissions=True)


def get_settings():
	"""
	Get Cost Valuation Settings.
	
	Returns:
		Cost Valuation Settings document or None if not found
	"""
	try:
		return frappe.get_single("Cost Valuation Settings")
	except Exception:
		return None


def can_bypass_block(settings):
	"""
	Check if current user has bypass role.
	
	Args:
		settings: Cost Valuation Settings document
		
	Returns:
		True if user can bypass blocking, False otherwise
	"""
	if not settings or not settings.bypass_roles:
		return False

	user_roles = frappe.get_roles()
	# Read roles from Table MultiSelect (child table)
	bypass_roles = [row.role for row in settings.bypass_roles if row.role]

	return bool(set(user_roles) & set(bypass_roles))


# =============================================================================
# Chart Data API
# =============================================================================

@frappe.whitelist()
def get_chart_data(item_code, from_date=None, to_date=None):
	"""
	Fetch incoming rates and calculate statistics for control chart.
	
	Args:
		item_code: The item to get chart data for
		from_date: Start date (defaults to 6 months ago)
		to_date: End date (defaults to today)
		
	Returns:
		dict with:
		- data_points: [{date, rate, voucher_type, voucher_no, is_anomaly, severity}]
		- statistics: {mean, rms, std_dev, ucl, lcl}
		- rule: {expected_rate, allowed_variance_pct, min_rate, max_rate, rule_source}
	"""
	if not item_code:
		return {"error": "Item code is required"}
	
	# Set default date range
	if not to_date:
		to_date = nowdate()
	if not from_date:
		from_date = add_months(getdate(to_date), -6)
	
	# Fetch incoming rates from Stock Ledger Entry
	data_points = get_incoming_rates(item_code, from_date, to_date)
	
	# Get rule for the item
	rule = get_expected_rate(item_code)
	
	# Get settings for thresholds
	settings = get_settings()
	
	# Calculate statistics
	statistics = calculate_statistics(data_points)
	
	# Flag anomalies based on rule and statistics
	flag_anomalies(data_points, rule, statistics, settings)
	
	return {
		"data_points": data_points,
		"statistics": statistics,
		"rule": rule,
		"item_code": item_code,
		"from_date": str(from_date),
		"to_date": str(to_date)
	}


def get_incoming_rates(item_code, from_date, to_date):
	"""
	Fetch incoming rates from Stock Ledger Entry.
	
	Args:
		item_code: The item code
		from_date: Start date
		to_date: End date
		
	Returns:
		List of dicts with date, rate, voucher_type, voucher_no
	"""
	sle_data = frappe.db.sql("""
		SELECT
			sle.posting_date as date,
			sle.incoming_rate as rate,
			sle.voucher_type,
			sle.voucher_no,
			sle.actual_qty as qty,
			sle.stock_value_difference,
			sle.warehouse
		FROM `tabStock Ledger Entry` sle
		WHERE
			sle.item_code = %(item_code)s
			AND sle.actual_qty > 0
			AND sle.is_cancelled = 0
			AND sle.voucher_type IN ('Purchase Receipt', 'Purchase Invoice', 'Stock Entry')
			AND sle.posting_date >= %(from_date)s
			AND sle.posting_date <= %(to_date)s
		ORDER BY sle.posting_date ASC, sle.posting_time ASC
	""", {
		"item_code": item_code,
		"from_date": from_date,
		"to_date": to_date
	}, as_dict=True)
	
	# Process and clean data
	data_points = []
	for sle in sle_data:
		rate = flt(sle.rate)
		# If incoming_rate is 0, calculate from stock_value_difference
		if not rate and sle.stock_value_difference and sle.qty:
			rate = abs(flt(sle.stock_value_difference) / flt(sle.qty))
		
		if rate > 0:
			data_points.append({
				"date": str(sle.date),
				"rate": rate,
				"voucher_type": sle.voucher_type,
				"voucher_no": sle.voucher_no,
				"warehouse": sle.warehouse,
				"is_anomaly": False,
				"severity": None
			})
	
	return data_points


def calculate_statistics(data_points):
	"""
	Calculate statistical measures for control chart.
	
	Args:
		data_points: List of data point dicts with 'rate' field
		
	Returns:
		dict with mean, rms, std_dev, ucl, lcl
	"""
	if not data_points:
		return {
			"mean": 0,
			"rms": 0,
			"std_dev": 0,
			"ucl": 0,
			"lcl": 0,
			"count": 0
		}
	
	rates = [dp["rate"] for dp in data_points]
	n = len(rates)
	
	# Mean (average)
	mean = sum(rates) / n
	
	# RMS (Root Mean Square)
	sum_of_squares = sum(r * r for r in rates)
	rms = math.sqrt(sum_of_squares / n)
	
	# Standard Deviation
	if n > 1:
		variance = sum((r - mean) ** 2 for r in rates) / n
		std_dev = math.sqrt(variance)
	else:
		std_dev = 0
	
	# Control Limits (2 sigma = ~95% confidence)
	ucl = mean + (2 * std_dev)  # Upper Control Limit
	lcl = max(0, mean - (2 * std_dev))  # Lower Control Limit (can't be negative for rates)
	
	return {
		"mean": round(mean, 2),
		"rms": round(rms, 2),
		"std_dev": round(std_dev, 2),
		"ucl": round(ucl, 2),
		"lcl": round(lcl, 2),
		"count": n
	}


def flag_anomalies(data_points, rule, statistics, settings):
	"""
	Flag data points that are anomalies based on rule or statistical limits.
	
	Args:
		data_points: List of data point dicts (modified in place)
		rule: Expected rate rule dict or None
		statistics: Statistics dict with ucl, lcl
		settings: Cost Valuation Settings
	"""
	if not data_points:
		return
	
	# Get thresholds from settings
	default_variance = flt(settings.default_variance_pct) if settings else 30
	severe_multiplier = flt(settings.severe_multiplier) if settings else 2
	
	for dp in data_points:
		rate = dp["rate"]
		is_anomaly = False
		severity = None
		
		if rule:
			# Check against rule
			expected = flt(rule.get("expected_rate"))
			allowed_variance = flt(rule.get("allowed_variance_pct")) or default_variance
			severe_threshold = allowed_variance * severe_multiplier
			min_rate = rule.get("min_rate")
			max_rate = rule.get("max_rate")
			
			# Check hard bounds first
			if min_rate and rate < min_rate:
				is_anomaly = True
				severity = "Severe"
			elif max_rate and rate > max_rate:
				is_anomaly = True
				severity = "Severe"
			elif expected:
				# Check variance
				variance_pct = calculate_variance(rate, expected)
				if variance_pct > severe_threshold:
					is_anomaly = True
					severity = "Severe"
				elif variance_pct > allowed_variance:
					is_anomaly = True
					severity = "Warning"
		else:
			# No rule - use statistical limits
			ucl = statistics.get("ucl", 0)
			lcl = statistics.get("lcl", 0)
			
			if ucl and lcl:
				if rate > ucl or rate < lcl:
					is_anomaly = True
					severity = "Warning"
		
		dp["is_anomaly"] = is_anomaly
		dp["severity"] = severity


@frappe.whitelist()
def get_items_with_anomalies(from_date=None, to_date=None, limit=20):
	"""
	Get items with the most anomalies for dashboard view.
	
	Args:
		from_date: Start date
		to_date: End date
		limit: Maximum number of items to return
		
	Returns:
		List of items with anomaly counts
	"""
	if not to_date:
		to_date = nowdate()
	if not from_date:
		from_date = add_months(getdate(to_date), -1)
	
	# Get anomaly counts by item
	anomaly_data = frappe.db.sql("""
		SELECT
			item_code,
			COUNT(*) as anomaly_count,
			SUM(CASE WHEN severity = 'Severe' THEN 1 ELSE 0 END) as severe_count,
			SUM(CASE WHEN severity = 'Warning' THEN 1 ELSE 0 END) as warning_count
		FROM `tabCost Anomaly Log`
		WHERE
			creation >= %(from_date)s
			AND creation <= %(to_date)s
		GROUP BY item_code
		ORDER BY anomaly_count DESC
		LIMIT %(limit)s
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"limit": int(limit)
	}, as_dict=True)
	
	return anomaly_data


@frappe.whitelist()
def get_recent_anomalies(limit=50):
	"""
	Get recent anomalies for dashboard view.
	
	Args:
		limit: Maximum number of anomalies to return
		
	Returns:
		List of recent anomalies
	"""
	anomalies = frappe.db.sql("""
		SELECT
			name,
			item_code,
			voucher_type,
			voucher_no,
			incoming_rate,
			expected_rate,
			variance_pct,
			severity,
			status,
			creation
		FROM `tabCost Anomaly Log`
		ORDER BY creation DESC
		LIMIT %(limit)s
	""", {"limit": int(limit)}, as_dict=True)
	
	return anomalies
