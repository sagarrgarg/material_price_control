# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

import frappe
from frappe import _
from frappe.model.document import Document


class CostValuationSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from material_price_control.material_price_control.doctype.mpc_bypass_role.mpc_bypass_role import MPCBypassRole

		block_if_no_rule: DF.Check
		block_severe: DF.Check
		bypass_roles: DF.TableMultiSelect[MPCBypassRole]
		default_variance_pct: DF.Percent
		enabled: DF.Check
		severe_multiplier: DF.Float
	# end: auto-generated types

	def validate(self):
		if self.enabled and not self.default_variance_pct:
			frappe.throw(_("Default Variance % is required when enabled"))
