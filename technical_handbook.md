# Technical Handbook - Material Price Control

## Change Log

### 2026-02-24 - Override Reason Flow (replaces Bypass Checkbox)

- **What changed**
  - Removed `bypass_cost_validation` checkbox from all 5 doctypes (PO, PR, PI, SE, SR).
  - Removed `validate_bypass_cost_validation` hook and all `bypass_cost_validation` references in `guard.py`.
  - Removed Property Setter fixtures (no longer needed).
  - Added `mpc_override_reason` (Small Text), `mpc_overridden_by` (Data), `mpc_overridden_at` (Datetime) custom fields on all 5 doctypes via fixture.
    - Fields are in a collapsible "Cost Validation Override" section that only appears after an override is recorded.
  - Added `override_reason` field to `Cost Anomaly Log` doctype JSON for full audit trail.
  - Rewrote severe-block flow in `guard.py`:
    - If `mpc_override_reason` is filled AND user has bypass role → allow submission, log audit.
    - If user has bypass role but no reason → show error dialog with **Override** button (via `frappe.msgprint` `primary_action.client_action`).
    - If user has no bypass role → show standard blocked error.
  - Added `can_override_cost_validation` whitelisted API for client-side role check.
  - Created `public/js/cost_override.js` — defines `material_price_control.show_override_dialog` called by the error dialog's Override button.
    - Dialog prompts for mandatory reason → persists to doc → re-submits.
  - Updated `hooks.py`:
    - Removed all `validate` hooks (no bypass checkbox to validate).
    - Added `cost_override.js` to `app_include_js`.
    - Removed Property Setter fixture entry.

- **Why it changed**
  - A checkbox bypass provided no audit trail and could be toggled silently.
  - Override-with-reason ensures every bypass is documented and traceable.
  - Error message stays the same (rates, thresholds, variations) — override users get an additional button in the error dialog.

- **Impacted modules**
  - `hooks.py` — doc_events, app_include_js, fixtures
  - `guard.py` — check_item_rate, throw_anomaly_error, new API
  - `public/js/cost_override.js` — new file
  - `fixtures/custom_field.json` — replaced bypass_cost_validation with override fields
  - `fixtures/property_setter.json` — deleted (no longer needed)
  - `Cost Anomaly Log` doctype JSON — added override_reason field

- **Migration implications**
  - Sites with existing `bypass_cost_validation` custom fields will need those removed (fixture overwrite handles this).
  - New custom fields (`mpc_override_reason`, `mpc_overridden_by`, `mpc_overridden_at`) created via fixture sync.
  - `Cost Anomaly Log` schema updated — `bench migrate` adds the new column.

## Removed Logic

- `validate_bypass_cost_validation` function — no longer needed; the bypass checkbox is gone.
- `bypass_cost_validation` custom field and associated Property Setters — replaced by override-reason flow.
- Reason: checkbox-based bypass had no audit trail and could be misused silently.

### 2026-02-24 - Bypass Field Migration to Fixtures (superseded)

- Initial fixture migration from patch-based `bypass_cost_validation` creation.
- Superseded by the override-reason flow above.
