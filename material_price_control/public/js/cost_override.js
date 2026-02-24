frappe.provide('material_price_control');

material_price_control.show_override_dialog = function () {
  const frm = cur_frm;
  if (!frm) return;

  if (frappe.msg_dialog) {
    frappe.msg_dialog.hide();
  }

  const d = new frappe.ui.Dialog({
    title: __('Override Cost Validation'),
    fields: [
      {
        label: __('Override Reason'),
        fieldname: 'reason',
        fieldtype: 'Small Text',
        reqd: 1,
        description: __('Mandatory: explain why this cost anomaly is acceptable.')
      }
    ],
    size: 'small',
    primary_action_label: __('Override & Submit'),
    primary_action(values) {
      d.hide();
      frm.set_value('mpc_override_reason', values.reason);
      frm.dirty();
      frm.save()
        .then(() => frm.save('Submit'))
        .then(() => {
          frappe.show_alert({
            message: __('Document submitted with cost override.'),
            indicator: 'green'
          });
        })
        .catch(() => {
          frappe.msgprint(__('Override failed. Please try again.'));
        });
    }
  });
  d.show();
};
