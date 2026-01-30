# Copyright (c) 2026, Material Price Control and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCostValuationSettings(FrappeTestCase):
	"""Test cases for Cost Valuation Settings."""

	def test_settings_doctype_exists(self):
		"""Test that Cost Valuation Settings doctype exists."""
		self.assertTrue(frappe.db.exists("DocType", "Cost Valuation Settings"))

	def test_default_settings(self):
		"""Test that default settings can be fetched."""
		from material_price_control.material_price_control.guard import get_settings

		settings = get_settings()
		# Settings may or may not exist, but the function should not throw
		if settings:
			self.assertIsNotNone(settings.name)

	def test_version_module(self):
		"""Test version compatibility module loads correctly."""
		from material_price_control.material_price_control.version import (
			get_frappe_version,
			is_version_15_or_above,
			is_version_16_or_above,
			get_version_info,
		)

		version = get_frappe_version()
		self.assertIsNotNone(version)
		self.assertIsNotNone(version.major)

		# Version checks should return booleans
		self.assertIsInstance(is_version_15_or_above(), bool)
		self.assertIsInstance(is_version_16_or_above(), bool)

		# Version info should return a dict with expected keys
		info = get_version_info()
		self.assertIsInstance(info, dict)
		self.assertIn("major", info)
		self.assertIn("supported", info)
		self.assertIn("is_v14", info)
		self.assertIn("is_v15", info)
		self.assertIn("is_v16", info)
