# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

"""
Dashboard utilities for Cost Valuation workspace.
"""

import frappe


@frappe.whitelist()
def get_items_without_rules_count():
	"""
	Get count of stock items that don't have a Cost Valuation Rule.
	
	Returns:
		dict with value (count of items without rules)
	"""
	# Get all item codes that have rules
	items_with_rules = frappe.get_all(
		"Cost Valuation Rule",
		filters={"enabled": 1, "rule_for": "Item"},
		pluck="item_code"
	)
	
	# Get all item groups that have rules
	groups_with_rules = frappe.get_all(
		"Cost Valuation Rule",
		filters={"enabled": 1, "rule_for": "Item Group"},
		pluck="item_group"
	)
	
	# Count stock items without direct or group rules
	filters = {
		"is_stock_item": 1,
		"disabled": 0
	}
	
	# Exclude items that have direct rules
	if items_with_rules:
		filters["name"] = ["not in", items_with_rules]
	
	# Exclude items in groups that have rules
	if groups_with_rules:
		filters["item_group"] = ["not in", groups_with_rules]
	
	count = frappe.db.count("Item", filters)
	
	return {"value": count}


@frappe.whitelist()
def get_top_anomaly_items(limit=10):
	"""
	Get items with the most open anomalies.
	
	Args:
		limit: Maximum number of items to return
		
	Returns:
		list of dicts with item_code, item_name, anomaly_count
	"""
	data = frappe.db.sql("""
		SELECT 
			cal.item_code,
			i.item_name,
			COUNT(*) as anomaly_count,
			SUM(CASE WHEN cal.severity = 'Severe' THEN 1 ELSE 0 END) as severe_count
		FROM `tabCost Anomaly Log` cal
		LEFT JOIN `tabItem` i ON i.name = cal.item_code
		WHERE cal.status = 'Open'
		GROUP BY cal.item_code
		ORDER BY anomaly_count DESC
		LIMIT %(limit)s
	""", {"limit": int(limit)}, as_dict=True)
	
	return data


@frappe.whitelist()
def get_dashboard_stats():
	"""
	Get all dashboard statistics in one call.
	
	Returns:
		dict with all dashboard stats
	"""
	open_anomalies = frappe.db.count("Cost Anomaly Log", {"status": "Open"})
	severe_anomalies = frappe.db.count("Cost Anomaly Log", {"status": "Open", "severity": "Severe"})
	active_rules = frappe.db.count("Cost Valuation Rule", {"enabled": 1})
	
	items_without_rules = get_items_without_rules_count()
	top_items = get_top_anomaly_items(10)
	
	return {
		"open_anomalies": open_anomalies,
		"severe_anomalies": severe_anomalies,
		"active_rules": active_rules,
		"items_without_rules": items_without_rules.get("value", 0),
		"top_anomaly_items": top_items
	}
