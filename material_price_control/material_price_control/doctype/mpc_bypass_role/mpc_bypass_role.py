# Copyright (c) 2026, Material Price Control and Contributors
# License: MIT

from frappe.model.document import Document


class MPCBypassRole(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		role: DF.Link

	# end: auto-generated types
	pass
