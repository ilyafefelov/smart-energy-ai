<!-- markdownlint-disable-file -->

# Release Changes: Stage 2 Diploma MVP

**Related Plan**: .copilot-tracking/plans/20260329-stage2-diploma-mvp-plan.instructions.md
**Implementation Date**: 2026-03-29

## Summary

Backfill the March 29 Stage 2 diploma MVP baseline into its own release-style tracker instead of continuing to overload the March 7 learned-policy migration backlog. The completed slices already landed in the active runtime cover policy compliance utility and recommendation-contract wiring, decision snapshot persistence and optimization-history contracts, UI policy trace surfacing in the control timeline, regime-aware financial analytics in `/api/history` and `analytics.vue`, and operator inputs for connected power plus market-regime override in the config-backed settings flow.

## Changes

### Added

- .copilot-tracking/changes/20260329-stage2-diploma-mvp-changes.md - Established a Stage 2-specific release tracker for the active diploma MVP baseline.

### Modified

- dashboard/server/utils/market-policy.ts - Added the Stage 2 policy utility for market-regime inference, silence-window export vetoes, reserve-floor guards, REMIT deliverable-energy checks, and regime override normalization.
- dashboard/server/utils/recommendation-contract.ts - Normalized Stage 2 action and provenance vocabulary so policy compliance and recommendation surfaces share one contract.
- dashboard/server/api/control/execute.post.ts - Attached policy-compliance data and `decision_snapshot` metadata to executed control actions.
- dashboard/server/api/control/schedule.post.ts - Persisted the same `decision_snapshot` contract for scheduled actions so the control path keeps one audit vocabulary.
- dashboard/server/utils/optimization-history.ts - Established `decision_snapshot_v1` and compliance-aware optimization-history reconciliation as the Stage 2 audit ledger.
- dashboard/server/api/control/history.get.ts - Exposed decision snapshot data through the control-history API for the active reasoning timeline.
- dashboard/app/components/Battery/InteractiveIllustration.vue - Surfaced decision-source badges, policy explanations, market regime, veto labeling, and adjusted-action trace details in the active control-history UI.
- dashboard/server/api/history.ts - Added Saved Funds, Earned Funds, and top-level `stage2_financials` to the canonical dashboard financial telemetry surface.
- dashboard/app/pages/analytics.vue - Consumed the new Stage 2 financial telemetry to show regime-aware totals, labels, and comparative value breakdowns.
- dashboard/app/components/Preferences/OptimizationProfile.vue - Added connected site power and market-regime override controls to the active settings flow.
- dashboard/server/api/config/current.get.ts - Returned Stage 2 operator-input defaults and normalized persisted `market_regime_override` values.
- dashboard/server/api/config/save.post.ts - Validated and stored `connected_power_kw` plus `market_regime_override` in the tenant config contract.
- tests/unit/stage2_market_policy_contract.test.mjs - Locked in silence-window, reserve-floor, REMIT, and comparative regime-override behavior for the Stage 2 policy layer.
- tests/unit/decision_snapshot_history_contract.test.mjs - Locked in the decision snapshot and optimization-history reconciliation contract used by the Stage 2 audit trail.
- tests/test_dashboard_battery_control_regression.py - Preserved regression coverage for control-history decision-trace fields in the active dashboard runtime.
- tests/test_dashboard_economics_api.py - Preserved regression coverage for `/api/history` economics alignment and tenant-scoped financial telemetry.

### Removed

- None.

## Validation Context

- tests/unit/stage2_market_policy_contract.test.mjs - Existing focused Stage 2 rule coverage proves the hard market-policy layer already has dedicated regression tests.
- tests/unit/decision_snapshot_history_contract.test.mjs - Existing contract coverage proves decision snapshot persistence and optimization-history reconciliation are already test-backed.
- tests/test_dashboard_battery_control_regression.py - Existing dashboard regression coverage proves the control-history timeline already exposes decision-trace fields.
- tests/test_dashboard_economics_api.py - Existing economics API coverage proves `/api/history` remains the canonical Stage 2 financial telemetry surface.

## Release Summary

**Total Files Affected**: 17

### Files Created (1)

- .copilot-tracking/changes/20260329-stage2-diploma-mvp-changes.md - Created the Stage 2-specific release tracker that backfills the current diploma MVP baseline.

### Files Modified (16)

- dashboard/server/utils/market-policy.ts - Added the Stage 2 market-policy contract and compliance utility.
- dashboard/server/utils/recommendation-contract.ts - Kept Stage 2 action and provenance vocabulary normalized across recommendation and control surfaces.
- dashboard/server/api/control/execute.post.ts - Persisted executed decisions with policy-compliance and decision-snapshot metadata.
- dashboard/server/api/control/schedule.post.ts - Persisted scheduled decisions with the same decision-snapshot contract.
- dashboard/server/utils/optimization-history.ts - Added the canonical Stage 2 audit ledger and reconciliation helpers.
- dashboard/server/api/control/history.get.ts - Surfaced decision-trace metadata through the active history API.
- dashboard/app/components/Battery/InteractiveIllustration.vue - Rendered the active Stage 2 policy trace and decision-source timeline UI.
- dashboard/server/api/history.ts - Added regime-aware Stage 2 financial telemetry.
- dashboard/app/pages/analytics.vue - Rendered regime-aware Saved Funds and Earned Funds analytics.
- dashboard/app/components/Preferences/OptimizationProfile.vue - Exposed Stage 2 operator inputs in the active settings form.
- dashboard/server/api/config/current.get.ts - Returned Stage 2 operator-input defaults and normalized override values.
- dashboard/server/api/config/save.post.ts - Validated and stored Stage 2 operator-input changes.
- tests/unit/stage2_market_policy_contract.test.mjs - Protected Stage 2 hard-rule behavior from regression.
- tests/unit/decision_snapshot_history_contract.test.mjs - Protected the Stage 2 audit-history contract from regression.
- tests/test_dashboard_battery_control_regression.py - Protected the control-history timeline trace fields from regression.
- tests/test_dashboard_economics_api.py - Protected Stage 2 financial telemetry alignment from regression.

### Files Removed (0)

- None.

### Dependencies & Infrastructure

- **New Dependencies**: None.
- **Updated Dependencies**: None.
- **Infrastructure Changes**: None.
- **Configuration Updates**: Tenant config now carries `connected_power_kw` and `market_regime_override` for Stage 2 regime-aware behavior.

### Deployment Notes

This backfill establishes the March 29 Stage 2 baseline only. Remaining work is still open for the regime-aware optimizer extension, focused validation completion, end-to-end demo scenarios, and final diploma-facing documentation alignment.