# Copyright (c) 2026, Material Price Control and Contributors
# See license.txt

"""
Tests for the guard module's statistical calculations and helper functions.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from material_price_control.material_price_control.guard import (
	calculate_statistics,
	calculate_variance,
)


class TestGuardStatistics(FrappeTestCase):
	"""Test cases for guard module statistics functions."""

	def test_calculate_statistics_empty(self):
		"""Test statistics with empty data points."""
		result = calculate_statistics([])

		self.assertEqual(result["count"], 0)
		self.assertEqual(result["mean"], 0)
		self.assertEqual(result["std_dev"], 0)
		self.assertEqual(result["ucl"], 0)
		self.assertEqual(result["lcl"], 0)

	def test_calculate_statistics_single_point(self):
		"""Test statistics with a single data point."""
		data_points = [{"rate": 100.0}]
		result = calculate_statistics(data_points)

		self.assertEqual(result["count"], 1)
		self.assertEqual(result["mean"], 100.0)
		self.assertEqual(result["std_dev"], 0)  # No variance with single point

	def test_calculate_statistics_multiple_points(self):
		"""Test statistics with multiple data points."""
		data_points = [
			{"rate": 100.0},
			{"rate": 110.0},
			{"rate": 90.0},
			{"rate": 105.0},
			{"rate": 95.0},
		]
		result = calculate_statistics(data_points)

		self.assertEqual(result["count"], 5)
		self.assertEqual(result["mean"], 100.0)  # Average of 100, 110, 90, 105, 95
		self.assertGreater(result["std_dev"], 0)
		self.assertGreater(result["ucl"], result["mean"])
		self.assertLess(result["lcl"], result["mean"])

	def test_calculate_variance_normal(self):
		"""Test variance calculation with normal values."""
		# 10% variance
		variance = calculate_variance(110.0, 100.0)
		self.assertEqual(variance, 10.0)

	def test_calculate_variance_zero_expected(self):
		"""Test variance calculation with zero expected rate."""
		variance = calculate_variance(100.0, 0)
		self.assertEqual(variance, 0)

	def test_calculate_variance_negative_expected(self):
		"""Test variance calculation with negative expected rate."""
		variance = calculate_variance(100.0, -50.0)
		self.assertEqual(variance, 0)


class TestGuardHelpers(FrappeTestCase):
	"""Test cases for guard module helper functions."""

	def test_has_custom_field(self):
		"""Test has_custom_field utility."""
		from material_price_control.material_price_control.guard import has_custom_field

		# Test with non-existent field
		result = has_custom_field("Item", "nonexistent_custom_field_xyz")
		self.assertFalse(result)

	def test_get_settings(self):
		"""Test get_settings function."""
		from material_price_control.material_price_control.guard import get_settings

		# Should not raise an error, may return None if not configured
		settings = get_settings()
		# Either None or a valid settings object
		if settings:
			self.assertEqual(settings.doctype, "Cost Valuation Settings")
