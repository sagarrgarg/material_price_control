# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

"""
Item Valuation Statistics Report

Shows historical mean, std dev, UCL, LCL for items based on Stock Ledger Entry data.
Helps users understand incoming rate patterns and set appropriate Cost Valuation Rules.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from material_price_control.material_price_control.guard import (
	get_incoming_rates,
	calculate_statistics,
	get_expected_rate,
	get_settings
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
			"width": 200
		},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 120
		},
		{
			"fieldname": "data_points",
			"label": _("Data Points"),
			"fieldtype": "Int",
			"width": 90
		},
		{
			"fieldname": "mean",
			"label": _("Mean (μ)"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "std_dev",
			"label": _("Std Dev (σ)"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "ucl",
			"label": _("UCL (μ+2σ)"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "lcl",
			"label": _("LCL (μ-2σ)"),
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"fieldname": "rule_expected_rate",
			"label": _("Rule Expected Rate"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "variance_vs_mean",
			"label": _("Variance vs Mean %"),
			"fieldtype": "Percent",
			"width": 120
		},
		{
			"fieldname": "rule_name",
			"label": _("Rule"),
			"fieldtype": "Link",
			"options": "Cost Valuation Rule",
			"width": 120
		}
	]


def get_data(filters):
	"""Fetch and process data for the report."""
	# Get list of items to analyze
	items = get_items_to_analyze(filters)
	
	if not items:
		return []
	
	# Get settings
	settings = get_settings()
	include_internal = getattr(settings, 'include_internal_suppliers', 0) if settings else 0
	
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	warehouse = filters.get("warehouse")
	
	data = []
	
	for item in items:
		row = {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"item_group": item.item_group
		}
		
		# Get incoming rates for this item
		data_points = get_incoming_rates(
			item.item_code, from_date, to_date, include_internal
		)
		
		# Filter by warehouse if specified
		if warehouse:
			data_points = [dp for dp in data_points if dp.get("warehouse") == warehouse]
		
		# Calculate statistics
		stats = calculate_statistics(data_points)
		
		row["data_points"] = stats.get("count", 0)
		row["mean"] = stats.get("mean", 0)
		row["std_dev"] = stats.get("std_dev", 0)
		row["ucl"] = stats.get("ucl", 0)
		row["lcl"] = stats.get("lcl", 0)
		
		# Get current rule
		current_rule = get_expected_rate(
			item.item_code, 
			warehouse=warehouse, 
			posting_date=to_date
		)
		
		if current_rule:
			row["rule_expected_rate"] = current_rule.get("expected_rate", 0)
			row["rule_name"] = current_rule.get("rule_name")
			
			# Calculate variance between rule and historical mean
			if row["mean"] and row["mean"] > 0:
				variance = (flt(current_rule.get("expected_rate", 0)) - row["mean"]) / row["mean"] * 100
				row["variance_vs_mean"] = round(variance, 2)
		else:
			row["rule_expected_rate"] = None
			row["rule_name"] = None
			row["variance_vs_mean"] = None
		
		data.append(row)
	
	# Sort by data points descending
	data.sort(key=lambda x: x.get("data_points", 0), reverse=True)
	
	return data


def get_items_to_analyze(filters):
	"""Get list of items based on filters."""
	item_filters = {}
	
	if filters.get("item_code"):
		item_filters["name"] = filters.get("item_code")
	
	if filters.get("item_group"):
		item_filters["item_group"] = filters.get("item_group")
	
	# If no filters, get items that have stock transactions
	if not item_filters:
		# Get items with recent SLE entries
		items_with_sle = frappe.db.sql("""
			SELECT DISTINCT item_code
			FROM `tabStock Ledger Entry`
			WHERE posting_date >= %(from_date)s
			AND posting_date <= %(to_date)s
			AND actual_qty > 0
			AND is_cancelled = 0
			LIMIT 500
		""", {
			"from_date": filters.get("from_date"),
			"to_date": filters.get("to_date")
		}, as_dict=True)
		
		if not items_with_sle:
			return []
		
		item_codes = [d.item_code for d in items_with_sle]
		item_filters["name"] = ["in", item_codes]
	
	items = frappe.get_all(
		"Item",
		filters=item_filters,
		fields=["name as item_code", "item_name", "item_group"],
		limit=500
	)
	
	return items
