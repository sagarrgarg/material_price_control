# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate


class CostValuationRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allowed_variance_pct: DF.Percent | None
		enabled: DF.Check
		expected_rate: DF.Currency
		from_date: DF.Date | None
		item_code: DF.Link | None
		item_group: DF.Link | None
		max_rate: DF.Currency | None
		min_rate: DF.Currency | None
		rule_for: DF.Literal["Item", "Item Group"]
		to_date: DF.Date | None
		warehouse: DF.Link | None
	# end: auto-generated types

	def autoname(self):
		"""Generate smart name like CV-{item_code or item_group}-####"""
		if self.rule_for == "Item" and self.item_code:
			prefix = f"CV-{self.item_code}-.####"
		elif self.item_group:
			prefix = f"CV-{self.item_group}-.####"
		else:
			prefix = "CV-.####"
		self.name = make_autoname(prefix)

	def validate(self):
		# Ensure only one field is set based on rule_for
		if self.rule_for == "Item":
			if not self.item_code:
				frappe.throw(_("Item Code is required when Rule For is Item"))
			self.item_group = None
		else:
			if not self.item_group:
				frappe.throw(_("Item Group is required when Rule For is Item Group"))
			self.item_code = None

		# Validate date range
		self.validate_dates()

		# Check for duplicate/overlapping active rules
		self.validate_unique_rule()

	def validate_dates(self):
		"""Ensure from_date <= to_date if both are set."""
		if self.from_date and self.to_date:
			if getdate(self.from_date) > getdate(self.to_date):
				frappe.throw(_("From Date cannot be after To Date"))

	def validate_unique_rule(self):
		"""
		Ensure no overlapping active rules for same item/warehouse.
		
		Logic:
		- Perpetual rule (no dates): Only one allowed per item+warehouse
		- Dated rule: Cannot overlap with other dated rules for same item+warehouse
		- Fallback behavior: Dated rules take priority over perpetual rules
		"""
		if not self.enabled:
			return

		target = self.item_code or self.item_group
		is_perpetual = not self.from_date and not self.to_date

		if is_perpetual:
			# Check if another perpetual rule exists for same item/warehouse
			existing = self._find_perpetual_rule()
			if existing:
				frappe.throw(
					_("A perpetual rule already exists for {0} {1}{2}: {3}").format(
						self.rule_for,
						frappe.bold(target),
						f" in warehouse {self.warehouse}" if self.warehouse else "",
						frappe.bold(existing)
					)
				)
		else:
			# Check for overlapping dated rules
			overlapping = self._find_overlapping_dated_rules()
			if overlapping:
				frappe.throw(
					_("Date range overlaps with existing rule: {0}").format(
						frappe.bold(overlapping)
					)
				)

	def _find_perpetual_rule(self):
		"""Find existing perpetual rule (no dates) for same item/warehouse."""
		filters = self._get_base_filters()
		filters["from_date"] = ["is", "not set"]
		filters["to_date"] = ["is", "not set"]
		return frappe.db.get_value("Cost Valuation Rule", filters, "name")

	def _find_overlapping_dated_rules(self):
		"""
		Find rules with overlapping date ranges.
		
		Date overlap logic: (start1 <= end2) AND (end1 >= start2)
		Handle NULL dates as infinite range.
		"""
		base_filters = self._get_base_filters()
		
		# Get all enabled dated rules for same item/warehouse
		rules = frappe.get_all(
			"Cost Valuation Rule",
			filters=base_filters,
			fields=["name", "from_date", "to_date"]
		)
		
		for rule in rules:
			# Skip perpetual rules (they don't overlap with dated rules)
			if not rule.from_date and not rule.to_date:
				continue
			
			# Check overlap
			if self._dates_overlap(
				self.from_date, self.to_date,
				rule.from_date, rule.to_date
			):
				return rule.name
		
		return None

	def _dates_overlap(self, start1, end1, start2, end2):
		"""
		Check if two date ranges overlap.
		NULL means infinite (no boundary).
		"""
		# Convert to dates for comparison
		s1 = getdate(start1) if start1 else None
		e1 = getdate(end1) if end1 else None
		s2 = getdate(start2) if start2 else None
		e2 = getdate(end2) if end2 else None
		
		# Check if ranges overlap
		# Overlap if: start1 <= end2 AND end1 >= start2
		# NULL start = -infinity, NULL end = +infinity
		
		# start1 <= end2
		if s1 and e2 and s1 > e2:
			return False
		
		# end1 >= start2
		if e1 and s2 and e1 < s2:
			return False
		
		return True

	def _get_base_filters(self):
		"""Get base filters for finding conflicting rules."""
		filters = {
			"enabled": 1,
			"name": ["!=", self.name],
			"rule_for": self.rule_for
		}
		
		if self.rule_for == "Item":
			filters["item_code"] = self.item_code
		else:
			filters["item_group"] = self.item_group
		
		# Warehouse filter (null matches null)
		if self.warehouse:
			filters["warehouse"] = self.warehouse
		else:
			filters["warehouse"] = ["is", "not set"]
		
		return filters
