# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document


class CostValuationRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allowed_variance_pct: DF.Percent | None
		enabled: DF.Check
		expected_rate: DF.Currency
		item_code: DF.Link | None
		item_group: DF.Link | None
		max_rate: DF.Currency | None
		min_rate: DF.Currency | None
		rule_for: DF.Literal["Item", "Item Group"]
	# end: auto-generated types

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

		# Check for duplicate active rules
		self.validate_unique_rule()

	def validate_unique_rule(self):
		"""Ensure only one active rule per Item or Item Group"""
		if not self.enabled:
			return

		filters = {
			"enabled": 1,
			"name": ["!=", self.name]
		}

		if self.rule_for == "Item":
			filters["item_code"] = self.item_code
			filters["rule_for"] = "Item"
		else:
			filters["item_group"] = self.item_group
			filters["rule_for"] = "Item Group"

		if frappe.db.exists("Cost Valuation Rule", filters):
			target = self.item_code or self.item_group
			frappe.throw(
				_("An active rule already exists for {0} {1}").format(
					self.rule_for, frappe.bold(target)
				)
			)
