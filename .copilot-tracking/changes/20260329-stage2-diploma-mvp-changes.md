<!-- markdownlint-disable-file -->

# Release Changes: Stage 2 Diploma MVP

**Related Plan**: .copilot-tracking/plans/20260329-stage2-diploma-mvp-plan.instructions.md
**Implementation Date**: 2026-03-29

## Summary

Backfill the March 29 Stage 2 diploma MVP baseline into its own release-style tracker instead of continuing to overload the March 7 learned-policy migration backlog. The completed slices already landed in the active runtime cover policy compliance utility and recommendation-contract wiring, decision snapshot persistence and optimization-history contracts, UI policy trace surfacing in the control timeline, regime-aware financial analytics in `/api/history` and `analytics.vue`, and operator inputs for connected power plus market-regime override in the config-backed settings flow.

Later March 29 slices completed the remaining regime-aware optimizer work in the active schedule asset, propagated Stage 2 policy semantics into the Dagster-backed and deterministic 24-hour schedule timeline contract, and added focused regression coverage for the live `/api/dagster/recommendation` payload.

## Changes

### Added

- .copilot-tracking/changes/20260329-stage2-diploma-mvp-changes.md - Established a Stage 2-specific release tracker for the active diploma MVP baseline.
- dashboard/server/utils/dagster-schedule-policy.ts - Added a pure helper that applies the canonical Stage 2 policy layer to individual Dagster schedule rows.
- tests/unit/stage2_dagster_schedule_policy_contract.test.mjs - Added focused regression coverage for Stage 2 row-level Dagster schedule policy veto behavior.

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
- src/assets/core/optimization_schedule.py - Replaced the fixed degradation placeholder with config-driven Stage 2 inputs, regime inference, site-power caps, and economics-derived degradation cost.
- tests/unit/test_core_market_and_schedule_assets.py - Locked in the optimizer asset contract proving Stage 2 inputs flow into `BaselineDPOptimizer`.
- dashboard/server/api/dagster/recommendation.ts - Propagated Stage 2 policy semantics across both Dagster-materialized and deterministic fallback 24-hour schedule rows.
- scripts/read_dagster_schedule.py - Preserved richer materialized schedule row state so the dashboard policy layer can evaluate each future hour without duplicating rules in Python.
- tests/unit/test_schedule_reconcile_and_test_runner_scripts.py - Locked in the richer Dagster schedule row normalization contract used by the dashboard timeline.
- tests/test_dashboard_battery_control_regression.py - Added live integration coverage proving `/api/dagster/recommendation` exposes row-level Stage 2 policy metadata in the schedule payload.
- .copilot-tracking/plans/20260329-stage2-diploma-mvp-plan.instructions.md - Marked the landed optimizer, analytics, reasoning-timeline, operator-input, and focused validation tasks complete.
- .copilot-tracking/research/20260329-stage2-diploma-mvp-status-audit-research.md - Updated the status audit so the next work is demo evidence and broader doc cleanup rather than schedule-policy propagation.
- docs/Stage 2/plan.md - Synced the narrative execution snapshot to the landed Stage 2 runtime status and remaining open work.
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
- tests/unit/test_core_market_and_schedule_assets.py - Focused optimizer-asset coverage proves the Stage 2 schedule asset now consumes configuration-driven degradation and regime-aware inputs.
- tests/unit/stage2_dagster_schedule_policy_contract.test.mjs - Focused policy coverage proves a raw Dagster sell row can be surfaced as a Stage 2-adjusted hold when the silence window applies.
- tests/unit/test_schedule_reconcile_and_test_runner_scripts.py - Focused script coverage proves richer Dagster schedule state survives normalization into the dashboard-facing JSON contract.
- tests/test_dashboard_battery_control_regression.py - Live integration coverage now proves `/api/dagster/recommendation` schedule rows carry `requested_action`, `policy_compliance`, and regime metadata.

## Release Summary

**Total Files Affected**: 28

### Files Created (3)

- .copilot-tracking/changes/20260329-stage2-diploma-mvp-changes.md - Created the Stage 2-specific release tracker that backfills the current diploma MVP baseline.
- dashboard/server/utils/dagster-schedule-policy.ts - Added the shared row-level Stage 2 schedule-policy helper used by the Dagster timeline.
- tests/unit/stage2_dagster_schedule_policy_contract.test.mjs - Added focused contract coverage for Dagster schedule policy adjustments.

### Files Modified (25)

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
- src/assets/core/optimization_schedule.py - Upgraded the deterministic schedule asset to use Stage 2 regime-aware inputs and economics-derived degradation cost.
- tests/unit/test_core_market_and_schedule_assets.py - Protected the optimizer Stage 2 input contract from regression.
- dashboard/server/api/dagster/recommendation.ts - Unified Stage 2 schedule row semantics across Dagster-backed and deterministic fallback recommendation paths.
- scripts/read_dagster_schedule.py - Preserved richer Dagster row state for downstream Stage 2 policy evaluation.
- tests/unit/test_schedule_reconcile_and_test_runner_scripts.py - Protected the Dagster schedule normalization contract with richer row fields.
- tests/test_dashboard_battery_control_regression.py - Extended the live dashboard regression to assert row-level Stage 2 schedule policy metadata.
- .copilot-tracking/plans/20260329-stage2-diploma-mvp-plan.instructions.md - Updated tracker status and marked landed tasks complete.
- .copilot-tracking/research/20260329-stage2-diploma-mvp-status-audit-research.md - Updated the Stage 2 status audit to reflect the landed schedule-policy slice and the remaining work.
- docs/Stage 2/plan.md - Updated the narrative execution snapshot to match the landed runtime and open work.
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

The active Stage 2 code path is now aligned through optimizer inputs, schedule-policy propagation, and focused validation. Remaining work is limited to capturing repeatable Stage 2 demo evidence from the active runtime and finishing the broader diploma-facing document cleanup for future-scope RL, Modulus, PatchTST, and VPP references.