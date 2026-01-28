# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

"""
Historical Anomaly Finder Report

This report scans historical Stock Ledger Entries and identifies transactions
that would be flagged as anomalies based on current Cost Valuation Rules.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

TRANSFER_STOCK_ENTRY_PURPOSES = (
	"Material Transfer",
	"Material Transfer for Manufacture",
)


def execute(filters=None):
	"""Main entry point for the report."""
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""Define report columns."""
	return [
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "voucher_type",
			"label": _("Voucher Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "voucher_no",
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 150
		},
		{
			"fieldname": "created_by",
			"label": _("Created By"),
			"fieldtype": "Link",
			"options": "User",
			"width": 120
		},
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		},
		{
			"fieldname": "item_name",
			"label": _("Item Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 120
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 80
		},
		{
			"fieldname": "incoming_rate",
			"label": _("Incoming Rate"),
			"fieldtype": "Currency",
			"width": 110
		},
		{
			"fieldname": "expected_rate",
			"label": _("Expected Rate"),
			"fieldtype": "Currency",
			"width": 110
		},
		{
			"fieldname": "variance_pct",
			"label": _("Variance %"),
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "severity",
			"label": _("Severity"),
			"fieldtype": "Data",
			"width": 90
		},
		{
			"fieldname": "rule_source",
			"label": _("Rule Source"),
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters):
	"""Fetch and process Stock Ledger Entries."""
	conditions = build_conditions(filters)
	
	# Fetch Stock Ledger Entries with incoming qty
	sle_data = frappe.db.sql("""
		SELECT
			sle.posting_date,
			sle.voucher_type,
			sle.voucher_no,
			sle.item_code,
			sle.warehouse,
			sle.actual_qty as qty,
			sle.incoming_rate,
			sle.stock_value_difference,
			item.item_name,
			item.item_group
		FROM `tabStock Ledger Entry` sle
		LEFT JOIN `tabStock Entry` se
			ON sle.voucher_type = 'Stock Entry' AND sle.voucher_no = se.name
		INNER JOIN `tabItem` item ON sle.item_code = item.name
		WHERE
			sle.actual_qty > 0
			AND sle.is_cancelled = 0
			AND sle.voucher_type IN ('Purchase Receipt', 'Purchase Invoice', 'Stock Entry', 'Stock Reconciliation')
			AND (
				sle.voucher_type NOT IN ('Stock Entry')
				OR se.purpose NOT IN %(transfer_purposes)s
			)
			{conditions}
		ORDER BY sle.posting_date DESC, sle.posting_time DESC
		LIMIT 5000
	""".format(conditions=conditions), {**filters, "transfer_purposes": TRANSFER_STOCK_ENTRY_PURPOSES}, as_dict=True)
	
	# Get settings for thresholds
	settings = get_settings()
	
	# Get voucher owners for created_by column
	voucher_owners = get_voucher_owners(sle_data)
	
	# Process each entry and calculate anomalies
	result = []
	only_with_rules = filters.get("only_with_rules")
	created_by_filter = filters.get("created_by")
	
	for sle in sle_data:
		# Get created_by from voucher
		created_by = voucher_owners.get((sle.voucher_type, sle.voucher_no))
		
		# Filter by created_by if specified
		if created_by_filter and created_by != created_by_filter:
			continue
		
		row = process_sle_entry(sle, settings, filters, created_by)
		if row:
			# Filter out items without rules if only_with_rules is checked
			if only_with_rules and row.get("rule_source") == "None":
				continue
			result.append(row)
	
	return result


def get_voucher_owners(sle_data):
	"""
	Get the owner (created_by) for each voucher.
	
	Args:
		sle_data: List of SLE entries
		
	Returns:
		dict mapping (voucher_type, voucher_no) -> owner
	"""
	# Group vouchers by type
	vouchers_by_type = {}
	for sle in sle_data:
		vtype = sle.voucher_type
		if vtype not in vouchers_by_type:
			vouchers_by_type[vtype] = set()
		vouchers_by_type[vtype].add(sle.voucher_no)
	
	result = {}
	
	# Fetch owners for each voucher type
	for vtype, voucher_nos in vouchers_by_type.items():
		if not voucher_nos:
			continue
		
		doctype = vtype
		owners = frappe.get_all(
			doctype,
			filters={"name": ["in", list(voucher_nos)]},
			fields=["name", "owner"]
		)
		
		for row in owners:
			result[(vtype, row.name)] = row.owner
	
	return result


def build_conditions(filters):
	"""Build SQL conditions from filters."""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("AND sle.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND sle.posting_date <= %(to_date)s")
	
	if filters.get("item_code"):
		conditions.append("AND sle.item_code = %(item_code)s")
	
	if filters.get("item_group"):
		conditions.append("AND item.item_group = %(item_group)s")
	
	if filters.get("warehouse"):
		conditions.append("AND sle.warehouse = %(warehouse)s")
	
	if filters.get("voucher_type"):
		conditions.append("AND sle.voucher_type = %(voucher_type)s")
	
	return " ".join(conditions)


def process_sle_entry(sle, settings, filters, created_by=None):
	"""
	Process a single SLE entry and determine if it's an anomaly.
	
	Args:
		sle: Stock Ledger Entry dict
		settings: Cost Valuation Settings
		filters: Report filters
		created_by: User who created the voucher
		
	Returns:
		dict with processed data or None if filtered out
	"""
	# Calculate effective incoming rate
	incoming_rate = flt(sle.incoming_rate)
	if not incoming_rate and sle.stock_value_difference and sle.qty:
		incoming_rate = abs(flt(sle.stock_value_difference) / flt(sle.qty))
	
	# Get expected rate from rules
	expected = get_expected_rate(sle.item_code)
	
	# Build result row
	row = {
		"posting_date": sle.posting_date,
		"voucher_type": sle.voucher_type,
		"voucher_no": sle.voucher_no,
		"created_by": created_by,
		"item_code": sle.item_code,
		"item_name": sle.item_name,
		"warehouse": sle.warehouse,
		"qty": sle.qty,
		"incoming_rate": incoming_rate,
		"expected_rate": None,
		"variance_pct": None,
		"severity": "No Rule",
		"rule_source": "None"
	}
	
	if expected:
		row["expected_rate"] = expected["expected_rate"]
		row["rule_source"] = expected.get("rule_source", "Unknown")
		
		# Calculate variance
		if expected["expected_rate"] and flt(expected["expected_rate"]) > 0:
			row["variance_pct"] = abs(incoming_rate - expected["expected_rate"]) / expected["expected_rate"] * 100
		
		# Determine severity
		row["severity"] = determine_severity(
			incoming_rate, expected, row["variance_pct"], settings
		)
	
	# Filter based on show_only_anomalies
	if filters.get("show_only_anomalies"):
		if row["severity"] not in ("Warning", "Severe", "No Rule"):
			return None
	
	return row


def determine_severity(incoming_rate, expected, variance_pct, settings):
	"""
	Determine the severity of the anomaly.
	
	Args:
		incoming_rate: Actual rate from SLE
		expected: Expected rate dict
		variance_pct: Calculated variance percentage
		settings: Cost Valuation Settings
		
	Returns:
		Severity string: 'Normal', 'Warning', or 'Severe'
	"""
	if not settings:
		return "Normal"
	
	# Check hard bounds first
	if expected.get("min_rate") and incoming_rate < expected["min_rate"]:
		return "Severe"
	
	if expected.get("max_rate") and incoming_rate > expected["max_rate"]:
		return "Severe"
	
	# Check variance thresholds
	if variance_pct is None:
		return "Normal"
	
	allowed_variance = flt(expected.get("allowed_variance_pct")) or flt(settings.default_variance_pct)
	severe_threshold = allowed_variance * flt(settings.severe_multiplier)
	
	if variance_pct > severe_threshold:
		return "Severe"
	elif variance_pct > allowed_variance:
		return "Warning"
	
	return "Normal"


def get_expected_rate(item_code):
	"""
	Get expected rate for an item from Cost Valuation Rules.
	
	Resolution order:
	1. Item-level rule
	2. Item Group rule
	3. None
	
	Args:
		item_code: Item code to look up
		
	Returns:
		dict with expected_rate, allowed_variance_pct, min_rate, max_rate, rule_source
		or None if no rule found
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


def get_settings():
	"""
	Get Cost Valuation Settings.
	
	Returns:
		Cost Valuation Settings document or None
	"""
	try:
		return frappe.get_single("Cost Valuation Settings")
	except Exception:
		return None
