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


# =============================================================================
# Utility Functions
# =============================================================================

def has_custom_field(doctype, fieldname):
	"""Check if a custom field exists on a doctype."""
	return frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname})


# =============================================================================
# Validation Hooks (before_submit)
# =============================================================================

def check_purchase_receipt(doc, method):
	"""Check Purchase Receipt items for valuation anomalies"""
	settings = get_settings()
	if not settings or not settings.enabled:
		return

	# Skip validation for internal suppliers if setting is disabled
	if not getattr(settings, 'include_internal_suppliers', False):
		if is_internal_supplier(doc.supplier):
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

	# Skip validation for internal suppliers if setting is disabled
	if not getattr(settings, 'include_internal_suppliers', False):
		if is_internal_supplier(doc.supplier):
			return

	for item in doc.items:
		if flt(item.qty) <= 0:
			continue

		incoming_rate = flt(item.valuation_rate)
		if not incoming_rate:
			continue

		check_item_rate(doc, item, incoming_rate, "Purchase Invoice", settings)


def is_internal_supplier(supplier_name):
	"""
	Check if a supplier is marked as internal.
	
	Args:
		supplier_name: The supplier name to check
		
	Returns:
		True if supplier is internal (is_internal_supplier or is_bns_internal_supplier)
	"""
	if not supplier_name:
		return False
	
	# Check if custom field exists
	has_bns_field = has_custom_field("Supplier", "is_bns_internal_supplier")
	
	# Build field list
	fields = ["is_internal_supplier"]
	if has_bns_field:
		fields.append("is_bns_internal_supplier")
	
	supplier_data = frappe.db.get_value("Supplier", supplier_name, fields, as_dict=True)
	if not supplier_data:
		return False
	
	is_internal = supplier_data.get("is_internal_supplier", 0)
	if has_bns_field:
		is_internal = is_internal or supplier_data.get("is_bns_internal_supplier", 0)
	
	return bool(is_internal)


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
	# Get warehouse and posting date for rule resolution
	warehouse = getattr(item_row, 'warehouse', None) or getattr(item_row, 't_warehouse', None)
	posting_date = getattr(doc, 'posting_date', None) or nowdate()
	
	expected = get_expected_rate(item_row.item_code, warehouse=warehouse, posting_date=posting_date)

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


def get_expected_rate(item_code, warehouse=None, posting_date=None):
	"""
	Get expected rate for an item with date and warehouse context.
	
	Resolution order (priority high to low):
	1. Item rule with matching warehouse + valid date range
	2. Item rule with no warehouse + valid date range
	3. Item fallback rule (no dates) with matching warehouse
	4. Item fallback rule (no dates) with no warehouse
	5. Same hierarchy for Item Group
	
	Args:
		item_code: The item code to look up
		warehouse: Optional warehouse for warehouse-specific rules
		posting_date: Optional posting date for date-range rules (defaults to today)
		
	Returns:
		dict with expected_rate, allowed_variance_pct, min_rate, max_rate, rule_source, rule_name or None
	"""
	if not posting_date:
		posting_date = nowdate()
	
	posting_date = getdate(posting_date)
	
	# Try Item-level rules first
	item_rule = _find_matching_rule("Item", item_code, warehouse, posting_date)
	if item_rule:
		return _format_rule_result(item_rule, "Item")
	
	# Try Item Group rules
	item_group = frappe.db.get_value("Item", item_code, "item_group")
	if item_group:
		group_rule = _find_matching_rule("Item Group", item_group, warehouse, posting_date)
		if group_rule:
			return _format_rule_result(group_rule, "Item Group")
	
	return None


def _find_matching_rule(rule_for, target, warehouse, posting_date):
	"""
	Find the best matching rule for the given target.
	
	Priority:
	1. Dated rule with warehouse match
	2. Dated rule without warehouse
	3. Fallback (perpetual) rule with warehouse match
	4. Fallback (perpetual) rule without warehouse
	
	Args:
		rule_for: "Item" or "Item Group"
		target: item_code or item_group
		warehouse: warehouse to match (or None)
		posting_date: date to check against rule date range
		
	Returns:
		Rule dict or None
	"""
	# Build base filter
	base_filter = {
		"enabled": 1,
		"rule_for": rule_for
	}
	
	if rule_for == "Item":
		base_filter["item_code"] = target
	else:
		base_filter["item_group"] = target
	
	# Get all matching rules
	rules = frappe.get_all(
		"Cost Valuation Rule",
		filters=base_filter,
		fields=["name", "expected_rate", "allowed_variance_pct", "min_rate", "max_rate",
		        "warehouse", "from_date", "to_date"]
	)
	
	if not rules:
		return None
	
	# Categorize rules
	dated_with_warehouse = []
	dated_no_warehouse = []
	fallback_with_warehouse = []
	fallback_no_warehouse = []
	
	for rule in rules:
		is_dated = rule.from_date or rule.to_date
		has_warehouse = bool(rule.warehouse)
		warehouse_match = (rule.warehouse == warehouse) if has_warehouse else False
		
		# Check if date is in range
		if is_dated:
			if not _date_in_range(posting_date, rule.from_date, rule.to_date):
				continue
			if warehouse and warehouse_match:
				dated_with_warehouse.append(rule)
			elif not has_warehouse:
				dated_no_warehouse.append(rule)
		else:
			# Fallback rule
			if warehouse and warehouse_match:
				fallback_with_warehouse.append(rule)
			elif not has_warehouse:
				fallback_no_warehouse.append(rule)
	
	# Return first match in priority order
	for rule_list in [dated_with_warehouse, dated_no_warehouse, 
	                  fallback_with_warehouse, fallback_no_warehouse]:
		if rule_list:
			return rule_list[0]
	
	return None


def _date_in_range(check_date, from_date, to_date):
	"""Check if check_date is within the from_date to to_date range."""
	if from_date and getdate(from_date) > check_date:
		return False
	if to_date and getdate(to_date) < check_date:
		return False
	return True


def _format_rule_result(rule, rule_source):
	"""Format a rule dict into the expected return format."""
	return {
		"expected_rate": flt(rule.expected_rate),
		"allowed_variance_pct": flt(rule.allowed_variance_pct) if rule.allowed_variance_pct else None,
		"min_rate": flt(rule.min_rate) if rule.min_rate else None,
		"max_rate": flt(rule.max_rate) if rule.max_rate else None,
		"rule_source": rule_source,
		"rule_name": rule.name
	}


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


@frappe.whitelist()
def get_chart_settings():
	"""
	Get settings relevant for the chart page.
	
	Returns:
		dict with include_internal_suppliers flag
	"""
	settings = get_settings()
	return {
		"include_internal_suppliers": getattr(settings, 'include_internal_suppliers', 0) if settings else 0
	}


@frappe.whitelist()
def get_item_statistics(item_code, warehouse=None, from_date=None, to_date=None, months=6):
	"""
	Get historical statistics for an item.
	
	This API is used by the Cost Valuation Rule form to show historical
	mean, std dev, etc. to help users set appropriate expected rates.
	
	Args:
		item_code: The item code to get statistics for
		warehouse: Optional warehouse filter
		from_date: Start date for analysis (optional, defaults to months ago)
		to_date: End date for analysis (optional, defaults to today)
		months: Number of months of history if dates not provided (default 6)
		
	Returns:
		dict with:
		- item_code: The item code
		- item_name: The item name
		- statistics: {mean, rms, std_dev, ucl, lcl, count}
		- current_rule: Current rule details if exists
	"""
	if not item_code:
		return {"error": "Item code is required"}
	
	# Get item name
	item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
	
	# Calculate date range - use provided dates or fall back to months
	if not to_date:
		to_date = nowdate()
	if not from_date:
		from_date = add_months(getdate(to_date), -frappe.utils.cint(months))
	
	# Get settings for internal supplier filtering
	settings = get_settings()
	include_internal = getattr(settings, 'include_internal_suppliers', 0) if settings else 0
	
	# Get incoming rates - reuse existing function
	data_points = get_incoming_rates(item_code, from_date, to_date, include_internal)
	
	# Filter by warehouse if specified
	if warehouse:
		data_points = [dp for dp in data_points if dp.get("warehouse") == warehouse]
	
	# Calculate statistics
	statistics = calculate_statistics(data_points)
	
	# Get current rule
	current_rule = get_expected_rate(item_code, warehouse=warehouse, posting_date=to_date)
	
	return {
		"item_code": item_code,
		"item_name": item_name,
		"warehouse": warehouse,
		"from_date": str(from_date),
		"to_date": str(to_date),
		"statistics": statistics,
		"current_rule": current_rule
	}


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

def get_supplier_internal_flags(supplier_names):
	"""
	Get internal supplier flags for a list of suppliers.
	
	Args:
		supplier_names: List of supplier names
		
	Returns:
		dict mapping supplier_name -> is_internal (bool)
	"""
	if not supplier_names:
		return {}
	
	# Check if custom field exists
	has_bns_field = has_custom_field("Supplier", "is_bns_internal_supplier")
	
	# Build field list
	fields = ["name", "is_internal_supplier"]
	if has_bns_field:
		fields.append("is_bns_internal_supplier")
	
	suppliers = frappe.get_all(
		"Supplier",
		filters={"name": ["in", list(supplier_names)]},
		fields=fields
	)
	
	result = {}
	for s in suppliers:
		is_internal = s.get("is_internal_supplier", 0)
		if has_bns_field:
			is_internal = is_internal or s.get("is_bns_internal_supplier", 0)
		result[s.name] = bool(is_internal)
	
	return result


def get_voucher_suppliers(voucher_nos_by_type):
	"""
	Get supplier for each voucher.
	
	Args:
		voucher_nos_by_type: dict with keys 'Purchase Receipt', 'Purchase Invoice'
		                    and values as lists of voucher_nos
		
	Returns:
		dict mapping (voucher_type, voucher_no) -> supplier_name
	"""
	result = {}
	
	# Purchase Receipts
	pr_nos = voucher_nos_by_type.get("Purchase Receipt", [])
	if pr_nos:
		prs = frappe.get_all(
			"Purchase Receipt",
			filters={"name": ["in", pr_nos]},
			fields=["name", "supplier"]
		)
		for pr in prs:
			result[("Purchase Receipt", pr.name)] = pr.supplier
	
	# Purchase Invoices
	pi_nos = voucher_nos_by_type.get("Purchase Invoice", [])
	if pi_nos:
		pis = frappe.get_all(
			"Purchase Invoice",
			filters={"name": ["in", pi_nos]},
			fields=["name", "supplier"]
		)
		for pi in pis:
			result[("Purchase Invoice", pi.name)] = pi.supplier
	
	return result


@frappe.whitelist()
def get_chart_data(item_code, from_date=None, to_date=None, include_internal_suppliers=0):
	"""
	Fetch incoming rates and calculate statistics for control chart.
	
	Args:
		item_code: The item to get chart data for
		from_date: Start date (defaults to 6 months ago)
		to_date: End date (defaults to today)
		include_internal_suppliers: If 0 (default), exclude PR/PI from internal suppliers
		
	Returns:
		dict with:
		- data_points: [{date, rate, voucher_type, voucher_no, is_anomaly, severity,
		                 supplier, is_internal_supplier, reference_rate, reference_source,
		                 variance_amount, variance_pct}]
		- statistics: {mean, rms, std_dev, ucl, lcl, count}
		- rule: {expected_rate, allowed_variance_pct, min_rate, max_rate, rule_source}
	"""
	if not item_code:
		return {"error": "Item code is required"}
	
	# Normalize boolean
	include_internal = frappe.utils.cint(include_internal_suppliers)
	
	# Set default date range
	if not to_date:
		to_date = nowdate()
	if not from_date:
		from_date = add_months(getdate(to_date), -6)
	
	# Fetch incoming rates from Stock Ledger Entry
	data_points = get_incoming_rates(item_code, from_date, to_date, include_internal)
	
	# Get rule for the item
	rule = get_expected_rate(item_code)
	
	# Get settings for thresholds
	settings = get_settings()
	
	# Calculate statistics
	statistics = calculate_statistics(data_points)
	
	# Enrich data points with variance and anomaly info
	enrich_data_points(data_points, rule, statistics, settings)
	
	return {
		"data_points": data_points,
		"statistics": statistics,
		"rule": rule,
		"item_code": item_code,
		"from_date": str(from_date),
		"to_date": str(to_date)
	}


def get_incoming_rates(item_code, from_date, to_date, include_internal_suppliers=0):
	"""
	Fetch incoming rates from Stock Ledger Entry.
	
	Args:
		item_code: The item code
		from_date: Start date
		to_date: End date
		include_internal_suppliers: If 0, exclude PR/PI from internal suppliers
		
	Returns:
		List of dicts with date, rate, voucher_type, voucher_no, supplier, is_internal_supplier
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
	
	# Build voucher lists for supplier lookup (PR and PI only)
	voucher_nos_by_type = {
		"Purchase Receipt": [],
		"Purchase Invoice": []
	}
	for sle in sle_data:
		if sle.voucher_type in voucher_nos_by_type:
			voucher_nos_by_type[sle.voucher_type].append(sle.voucher_no)
	
	# Get supplier for each voucher
	voucher_suppliers = get_voucher_suppliers(voucher_nos_by_type)
	
	# Get all unique suppliers
	all_suppliers = set(voucher_suppliers.values())
	
	# Get internal flags for all suppliers
	supplier_internal_flags = get_supplier_internal_flags(all_suppliers)
	
	# Process and clean data
	data_points = []
	for sle in sle_data:
		rate = flt(sle.rate)
		# If incoming_rate is 0, calculate from stock_value_difference
		if not rate and sle.stock_value_difference and sle.qty:
			rate = abs(flt(sle.stock_value_difference) / flt(sle.qty))
		
		if rate <= 0:
			continue
		
		# Get supplier info for PR/PI
		supplier = None
		is_internal = False
		if sle.voucher_type in ("Purchase Receipt", "Purchase Invoice"):
			supplier = voucher_suppliers.get((sle.voucher_type, sle.voucher_no))
			if supplier:
				is_internal = supplier_internal_flags.get(supplier, False)
		
		# Filter out internal suppliers if not included
		if not include_internal_suppliers and is_internal:
			continue
		
		data_points.append({
			"date": str(sle.date),
			"rate": rate,
			"voucher_type": sle.voucher_type,
			"voucher_no": sle.voucher_no,
			"warehouse": sle.warehouse,
			"supplier": supplier,
			"is_internal_supplier": is_internal,
			"is_anomaly": False,
			"severity": None,
			"reference_rate": None,
			"reference_source": None,
			"variance_amount": None,
			"variance_pct": None
		})
	
	return data_points


def calculate_statistics(data_points):
	"""
	Calculate statistical measures for control chart.
	
	Formulas:
	- Mean (μ): Σx / n
	- RMS (Root Mean Square): √(Σx² / n)
	- Standard Deviation (σ): √(Σ(x-μ)² / n) [population std dev]
	- UCL (Upper Control Limit): μ + 2σ
	- LCL (Lower Control Limit): μ - 2σ (min 0)
	
	Args:
		data_points: List of data point dicts with 'rate' field
		
	Returns:
		dict with mean, rms, std_dev, ucl, lcl, count
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
	
	# Mean (average): μ = Σx / n
	mean = sum(rates) / n
	
	# RMS (Root Mean Square): √(Σx² / n)
	sum_of_squares = sum(r * r for r in rates)
	rms = math.sqrt(sum_of_squares / n)
	
	# Standard Deviation (population): σ = √(Σ(x-μ)² / n)
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


def enrich_data_points(data_points, rule, statistics, settings):
	"""
	Enrich data points with variance calculations and anomaly flags.
	
	Variance calculations:
	- Reference rate: Rule expected_rate if available, else chart mean
	- Variance amount (Δ₹): rate - reference_rate (signed)
	- Variance percent (|Δ%|): |rate - reference_rate| / reference_rate × 100
	
	Args:
		data_points: List of data point dicts (modified in place)
		rule: Expected rate rule dict or None
		statistics: Statistics dict with mean, ucl, lcl
		settings: Cost Valuation Settings
	"""
	if not data_points:
		return
	
	# Get thresholds from settings
	default_variance = flt(settings.default_variance_pct) if settings else 30
	severe_multiplier = flt(settings.severe_multiplier) if settings else 2
	
	# Determine reference rate and source
	if rule and flt(rule.get("expected_rate")) > 0:
		reference_rate = flt(rule.get("expected_rate"))
		reference_source = "Rule"
	elif flt(statistics.get("mean")) > 0:
		reference_rate = flt(statistics.get("mean"))
		reference_source = "Mean"
	else:
		reference_rate = 0
		reference_source = None
	
	# Minimum data points for reliable statistical analysis
	# With < 5 points, statistical limits are unreliable
	data_count = statistics.get("count", 0)
	has_reliable_stats = data_count >= 5
	
	for dp in data_points:
		rate = dp["rate"]
		
		# Calculate variance
		if reference_rate > 0:
			dp["reference_rate"] = round(reference_rate, 2)
			dp["reference_source"] = reference_source
			dp["variance_amount"] = round(rate - reference_rate, 2)
			dp["variance_pct"] = round(abs(rate - reference_rate) / reference_rate * 100, 2)
		else:
			dp["reference_rate"] = None
			dp["reference_source"] = None
			dp["variance_amount"] = None
			dp["variance_pct"] = None
		
		# Determine anomaly status
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
			elif expected and dp["variance_pct"] is not None:
				if dp["variance_pct"] > severe_threshold:
					is_anomaly = True
					severity = "Severe"
				elif dp["variance_pct"] > allowed_variance:
					is_anomaly = True
					severity = "Warning"
		else:
			# No rule - use statistical limits (only if we have enough data)
			if has_reliable_stats:
				ucl = statistics.get("ucl")
				lcl = statistics.get("lcl")
				std_dev = statistics.get("std_dev", 0)
				mean = statistics.get("mean", 0)
				
				# Check if we have valid statistics (ucl/lcl can be 0 which is valid)
				if ucl is not None and lcl is not None and std_dev > 0:
					if rate > ucl or rate < lcl:
						is_anomaly = True
						# Determine severity based on how far outside the limits
						# Beyond 3σ (UCL + 1σ or LCL - 1σ) is Severe
						severe_ucl = mean + 3 * std_dev
						severe_lcl = max(0, mean - 3 * std_dev)
						if rate > severe_ucl or rate < severe_lcl:
							severity = "Severe"
						else:
							severity = "Warning"
		
		# Additional check: extreme variance should always be flagged
		# Only apply if we have a rule OR reliable stats to compare against
		# This prevents false positives with few data points
		if not is_anomaly and dp["variance_pct"] is not None:
			# Only flag extreme variance if:
			# 1. There's a rule to compare against, OR
			# 2. We have reliable stats (5+ data points)
			if rule or has_reliable_stats:
				if dp["variance_pct"] > 100:
					is_anomaly = True
					severity = "Severe" if dp["variance_pct"] > 200 else "Warning"
		
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
