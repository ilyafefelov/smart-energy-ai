<!-- markdownlint-disable-file -->

# Task Research Notes: Stage 2 Diploma MVP Status Audit

## Research Executed

### File Analysis

- docs/Stage 2/plan.md
  - The human-readable Stage 2 plan is now current enough to use as narrative status, with step 4 moved into progress and the `.copilot-tracking` umbrella tracker linked from the document.
- .copilot-tracking/plans/20260329-stage2-diploma-mvp-plan.instructions.md
  - The Stage 2 umbrella tracker now exists and correctly reflects the optimizer slice as in progress rather than not started.
- src/assets/core/optimization_schedule.py
  - The deterministic optimizer now resolves per-client Stage 2 inputs from `customers.yaml`, derives degradation cost from the shared economics model, infers market regime from site power plus override, and caps dispatch by site power.
- tests/unit/test_core_market_and_schedule_assets.py
  - Focused schedule-asset coverage now proves the Stage 2 optimizer inputs are passed into `BaselineDPOptimizer` instead of using the fixed degradation placeholder.
- dashboard/server/api/dagster/recommendation.ts
  - The live current-recommendation path and both 24-hour schedule builders now emit row-level Stage 2 semantics including `requested_action`, `policy_compliance`, `market_regime`, and adjusted profit handling.
- dashboard/server/api/dagster/schedule-24h.ts
  - The 24-hour schedule endpoint continues to relay and summarize `schedule_24h` rows from the recommendation endpoint, which now carry the Stage 2-adjusted semantics required by the UI.
- scripts/read_dagster_schedule.py
  - The Dagster asset reader now preserves richer schedule state so the dashboard-side policy layer can evaluate each future hour without duplicating legal logic in Python.
- tests/unit/test_schedule_reconcile_and_test_runner_scripts.py
  - Script coverage now locks the richer normalized schedule row contract used by the dashboard timeline.
- tests/test_dashboard_battery_control_regression.py
  - Integration coverage now proves the live `/api/dagster/recommendation` payload exposes row-level Stage 2 policy metadata in its `schedule_24h` contract.

### Code Search Results

- assessStage2MarketPolicy|inferReserveFloorPercent|inferSitePowerKw in dashboard/server/api/dagster/recommendation.ts
  - Matches confirm both the current recommendation and the schedule timeline are now Stage 2 policy-aware at the endpoint layer.
- requested_action|policy_compliance|market_regime across tests/test_dashboard_battery_control_regression.py and tests/unit/stage2_dagster_schedule_policy_contract.test.mjs
  - Matches confirm both focused unit coverage and live integration coverage now protect row-level Stage 2 schedule semantics.
- read_dagster_schedule.py|soc_before_kwh|grid_export_kwh across tests
  - Matches confirm richer Dagster row state is preserved through normalization and test-backed.
- market_regime|adjusted_action|policy_compliance in dashboard/app/**
  - Matches confirm the active battery/control timeline UI already knows how to render Stage 2 policy metadata when that contract is present.

### External Research

- No new external web or GitHub research was required. The next-slice decision is fully determined by current repository code paths, existing Stage 2 docs, and the landed March 29 implementation state.

### Project Conventions

- Standards referenced: `AGENTS.md`, `.github/copilot-instructions.md`, and the current `.copilot-tracking` execution tracker.
- Instructions followed: keep research evidence repo-grounded, remove outdated status claims immediately, and prefer the active `dashboard/` runtime surfaces over creating parallel Stage 2 paths.

## Key Discoveries

### Project Structure

The active Stage 2 MVP now has three aligned production layers: a regime-aware optimizer input layer in `src/assets/core/optimization_schedule.py`, a canonical policy/compliance layer in `dashboard/server/utils/market-policy.ts`, and a recommendation/timeline layer in `dashboard/server/api/dagster/recommendation.ts` plus `schedule-24h.ts`. The previous mismatch between the policy layer and the 24-hour schedule contract is now closed. The remaining gap is no longer runtime behavior; it is execution evidence and broader diploma-facing document cleanup.

### Implementation Patterns

The repo is already converging on one correct architectural pattern: keep the legal and market-rule vocabulary canonical in TypeScript on the dashboard server side, and treat Python schedule assets as deterministic physics/economics producers rather than a second source of legal policy logic. The newly landed optimizer work strengthened the physics/economics side, and the schedule-policy propagation slice now carries that contract through both Dagster-backed and deterministic fallback schedule payloads.

### Complete Examples

```python
def _normalize_action(action_kw: float) -> str:
    if action_kw > 0.05:
        return "SELL"
    if action_kw < -0.05:
        return "BUY"
    return "HOLD"
```

```ts
const policyCompliance = assessStage2MarketPolicy({
  action: strategyAdjustedRecommendation.action,
  powerKw: strategyAdjustedRecommendation.action_kw,
  batterySocPercent: Number.isFinite(batterySoc) ? batterySoc : null,
  batteryCapacityKwh: configPayload?.data?.battery_capacity_kwh ?? batteryPayload?.battery?.capacity,
  reserveFloorPercent: inferReserveFloorPercent(configPayload?.data || null),
  sitePowerKw: inferSitePowerKw(configPayload?.data || null),
  marketRegimeOverride: configPayload?.data?.market_regime_override,
  timestamp: new Date().toISOString(),
  timezone: String(configPayload?.data?.timezone || 'Europe/Kiev'),
})
```

```ts
return {
  hour,
  time: formatClockHour(hour),
  price_uah_kwh: Number(Number(row.price || dagsterRow?.price_uah_kwh || 0).toFixed(2)),
  recommended_action: action,
  expected_profit_uah: Number(Number(dagsterRow?.expected_profit_uah || 0).toFixed(2)),
  confidence: Number(baseConfidence.toFixed(2)),
  is_peak: (hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 20),
  rationale,
}
```

### API and Schema Documentation

- Optimizer schedule asset contract:
  - `src/assets/core/optimization_schedule.py`
  - Still emits rich schedule state including `soc_before_kwh`, `soc_after_kwh`, `grid_export_kwh`, `purchase_cost_eur`, `export_revenue_eur`, and `net_cost_eur`; those fields are available for future Stage 2 schedule-policy propagation even though the current Dagster reader drops most of them.
- Current recommendation policy contract:
  - `dashboard/server/api/dagster/recommendation.ts`
  - Already returns top-level `recommendation.policy_compliance`, `contract.compliance`, and source metadata containing `market_regime`, `policy_rule_hits`, and `policy_veto_applied`.
- Schedule timeline contract:
  - `dashboard/server/api/dagster/recommendation.ts` -> `buildScheduleFromDagsterAsset(...)` and `buildDeterministicSchedule(...)`
  - Now returns `recommended_action`, `requested_action`, `requested_profit_uah`, `market_regime`, and `policy_compliance` per row so the timeline and current recommendation share one Stage 2 vocabulary.
- Dagster materialization reader contract:
  - `scripts/read_dagster_schedule.py`
  - Now serializes richer row state including SoC, import/export energy, and economics fields in addition to action and price data.

### Configuration Examples

```json
{
  "battery_capacity_kwh": 150,
  "battery_efficiency": 0.88,
  "battery_dod_max": 0.85,
  "battery_soc_min": 0.2,
  "connected_power_kw": 20,
  "market_regime_override": "market_premium"
}
```

### Technical Requirements

- Keep the Stage 2 tracker and narrative docs aligned now that the optimizer and schedule-policy slices are landed.
- Capture repeatable Stage 2 demo evidence from the active runtime for the required silence-window, evening discharge, low-SoC block, and comparative-regime scenarios.
- Reframe the broader diploma-facing Stage 2 docs that still describe PPO, Modulus, PatchTST, or VPP paths as active MVP behavior instead of deferred scope.

## Recommended Approach

The next implementation slice should shift away from runtime contract work and into evidence and truthfulness work. The code path is already aligned around one policy vocabulary and one deterministic optimizer. The highest-value next step is to run the required Stage 2 demo scenarios against the active runtime, capture evidence from the canonical APIs, and then update the broader diploma-facing docs so they describe the deterministic compliance-aware MVP that now exists while clearly deferring PPO, Modulus, PatchTST, real hardware control, and VPP aggregation.

## Implementation Guidance

- **Objectives**: Finish the remaining non-runtime Stage 2 work by capturing scenario evidence and cleaning up broader diploma-facing documentation.
- **Key Tasks**: Run the required Stage 2 scenarios against the active runtime; record evidence against the canonical recommendation and history contracts; update tracker artifacts; and reframe supporting Stage 2 docs so future-scope RL, Modulus, and VPP content is clearly marked as deferred.
- **Dependencies**: The landed optimizer, analytics, policy, and schedule-timeline slices in the active `dashboard/` and `src/assets/core/` surfaces.
- **Success Criteria**: Repeatable Stage 2 demo evidence exists for the required scenarios, the tracker stays aligned with the live code, and the remaining Stage 2 docs no longer overstate future-scope capabilities as implemented MVP behavior.
