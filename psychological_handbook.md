# Psychological Handbook - Material Price Control

## Architectural Intent

- Block abnormal valuation rates by default; allow override only through explicit, auditable action.
- Override is an exception path requiring a written reason — not a toggle.
- Metadata customizations are fixture-first for reproducibility and auditability.
- Client-side UX (override dialog in error message) keeps the flow contextual — user sees the anomaly details and can override in the same interaction.

## Business Reasoning

- Valuation mistakes materially affect inventory and accounting; prevention beats correction.
- Teams need controlled emergency override for legitimate edge cases (supplier negotiations, market shifts).
- Every override must be traceable: who, when, and why — stored on both the transaction doc and the Cost Anomaly Log.
- The error message always shows rates, thresholds, and allowed variations so the user understands the violation before deciding to override.

## Constraints

- Server-side authorization in `guard.py` is mandatory and cannot be replaced by client/UI rules alone.
- `mpc_override_reason` is validated server-side — even if set via API, the user must have a bypass role.
- Fixture records are the source of truth for schema-level customizations.
- Changes must stay compatible with standard ERPNext stock and purchase doctypes.
- The override dialog relies on Frappe's `primary_action.client_action` pattern — the JS function must be globally available via `app_include_js`.

## Anti-Patterns to Avoid

- Using a simple checkbox for bypass — it provides no justification trail.
- Relying only on client-side role checks for permission-sensitive overrides.
- Auto-bypassing severe blocks without requiring an explicit reason.
- Spreading override logic across multiple entry points without centralized guard validation.
- Creating schema metadata through ad-hoc patches when fixtures can represent the same outcome.
