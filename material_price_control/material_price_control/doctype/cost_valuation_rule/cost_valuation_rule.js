// Copyright (c) 2026, Material Price Control and Contributors
// License: MIT

frappe.ui.form.on("Cost Valuation Rule", {
	rule_for: function(frm) {
		// Clear fields when rule_for changes
		if (frm.doc.rule_for == "Item") {
			frm.set_value("item_group", null);
		} else {
			frm.set_value("item_code", null);
		}
	}
});
