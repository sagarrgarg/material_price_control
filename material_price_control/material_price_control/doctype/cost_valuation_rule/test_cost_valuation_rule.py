# Copyright (c) 2026, Material Price Control and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCostValuationRule(FrappeTestCase):
	"""Test cases for Cost Valuation Rule."""

	def test_rule_doctype_exists(self):
		"""Test that Cost Valuation Rule doctype exists."""
		self.assertTrue(frappe.db.exists("DocType", "Cost Valuation Rule"))

	def test_upsert_rule_function(self):
		"""Test that upsert_cost_valuation_rule function is callable."""
		from material_price_control.material_price_control.guard import upsert_cost_valuation_rule

		self.assertTrue(callable(upsert_cost_valuation_rule))

	def test_bulk_upsert_function(self):
		"""Test that bulk_upsert_cost_valuation_rules function is callable."""
		from material_price_control.material_price_control.guard import bulk_upsert_cost_valuation_rules

		self.assertTrue(callable(bulk_upsert_cost_valuation_rules))

		# Test with empty rules returns expected structure
		result = bulk_upsert_cost_valuation_rules([])
		self.assertEqual(result["success_count"], 0)
		self.assertEqual(result["results"], [])
		self.assertEqual(result["errors"], [])
