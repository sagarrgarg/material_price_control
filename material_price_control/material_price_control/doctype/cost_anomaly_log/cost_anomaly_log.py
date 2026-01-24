# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

import frappe
from frappe.model.document import Document


class CostAnomalyLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		expected_rate: DF.Currency
		incoming_rate: DF.Currency
		item_code: DF.Link | None
		notes: DF.SmallText | None
		severity: DF.Literal["Warning", "Severe"]
		status: DF.Literal["Open", "Reviewed", "Ignored"]
		variance_pct: DF.Percent
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Data | None
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
