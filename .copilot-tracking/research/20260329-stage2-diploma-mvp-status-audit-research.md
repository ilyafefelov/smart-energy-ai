<!-- markdownlint-disable-file -->

# Task Research Notes: Stage 2 Diploma MVP Status Audit

## Research Executed

### File Analysis

- docs/Stage 2/plan.md
  - Active human-readable Stage 2 plan exists, but it does not reflect March 29 implementation progress and still reads as if steps 1-13 are entirely future work.
- .copilot-tracking/plans/20260307-learned-policy-migration-backlog-plan.instructions.md
  - Existing .copilot-tracking plan is a precursor learned-policy migration tracker, not the umbrella Stage 2 implementation tracker for the current workstream.
- .copilot-tracking/changes/20260307-learned-policy-migration-backlog-changes.md
  - Existing changes file covers March 7 migration work only and should not absorb March 29 Stage 2 MVP implementation slices.
- dashboard/server/utils/market-policy.ts
  - Stage 2 policy layer now exists with regime inference, silence-window export veto, reserve-floor veto, REMIT deliverable-energy checks, and market-regime override support.
- dashboard/server/utils/optimization-history.ts
  - Decision snapshot and optimization-history reconciliation are already implemented as the canonical audit/history contract.
- dashboard/server/api/history.ts
  - Stage 2 financial analytics now expose saved-versus-earned funds and a regime-aware `stage2_financials` summary.
- dashboard/app/components/Preferences/OptimizationProfile.vue
  - The active config-backed settings flow now exposes connected site power and market-regime override inputs for Stage 2 operator control.
- tests/unit/stage2_market_policy_contract.test.mjs
  - Focused policy tests now cover silence-window, REMIT, reserve inference, and comparative regime override behavior.

### Code Search Results

- stage2 tracking plan glob
  - No Stage 2-specific files exist under `.copilot-tracking/plans/`.
- stage2 tracking changes glob
  - No Stage 2-specific files exist under `.copilot-tracking/changes/`.
- market-policy|stage2_financials|decision_snapshot|market_regime_override|connected_power_kw
  - Matches confirm completed Stage 2 slices in policy, decision snapshot/history, UI policy trace, financial analytics, and operator settings.
- git log --oneline -5
  - Recent landed progress is visible in `f31a87d` (operator inputs), `0193e76` (financial regime analytics), and `220f985` (policy trace UI), with earlier March 29 Stage 2 commits just below the backup commits.

### External Research

- No new external web or GitHub research was required for this audit; plan-update decisions are fully supported by current repo state plus existing internal research at `.copilot-tracking/research/20260307-ml-pipeline-trading-logic-research.md`.

### Project Conventions

- Standards referenced: `AGENTS.md`, `.github/copilot-instructions.md`, and the task-implementation tracking instructions for `.copilot-tracking/changes/*.md`.
- Instructions followed: Beads-first workflow, preserve precursor trackers instead of repurposing them, and treat `.copilot-tracking/` as the authoritative implementation-tracking area when the workstream needs execution artifacts.

## Key Discoveries

### Project Structure

The active Stage 2 MVP plan currently lives only in `docs/Stage 2/plan.md`, while the implementation work is already spanning runtime helpers, recommendation APIs, optimization-history persistence, analytics, and dashboard settings. There is no Stage 2-specific umbrella tracker under `.copilot-tracking/plans/`, `.copilot-tracking/details/`, or `.copilot-tracking/changes/`. The March 7 learned-policy migration plan remains useful as a precursor and dependency baseline, but it is no longer the correct place to track the current Stage 2 diploma MVP execution.

### Implementation Patterns

The implemented Stage 2 work follows one consistent pattern: reuse the active `dashboard/` runtime surfaces instead of creating parallel code paths. Policy and regime logic live in shared server utilities; recommendation APIs attach normalized contracts and compliance metadata; decision snapshots persist through optimization history; analytics consume the canonical `/api/history` surface; and the active config-backed preferences panel owns the new operator inputs. This means the plan update should track vertical Stage 2 slices on top of the existing runtime, not a separate architecture branch.

### Complete Examples

```ts
const sitePowerKw = inferSitePowerKw(configPayload?.data || null)
const marketRegime = inferMarketRegime(sitePowerKw, configPayload?.data?.market_regime_override)
const financialMode = buildFinancialModeSummary(marketRegime)
```

```ts
const response = await $fetch<any>('/api/config/save', {
  method: 'POST',
  query: { tenantId },
  headers: { 'x-tenant-id': tenantId },
  body: {
    tenantId,
    optimization_strategy: toApiStrategy(selectedStrategy.value),
    battery_soc_min: batterySocMin.value,
    battery_c_rate_discharge: batteryCRateDischarge.value,
    ml_forecast_horizon_hours: forecastHorizonHours.value,
    connected_power_kw: connectedPowerKw.value,
    market_regime_override: marketRegimeOverride.value,
  },
})
```

### API and Schema Documentation

- Stage 2 policy contract:
  - `dashboard/server/utils/market-policy.ts`
  - Regime inference now accepts raw power plus optional `marketRegimeOverride`.
- Stage 2 analytics contract:
  - `dashboard/server/api/history.ts`
  - Adds `saved_funds_uah`, `earned_funds_uah`, and top-level `stage2_financials` with `market_regime`, `site_power_kw`, `financial_mode_label`, `financial_mode_summary`, and aggregate totals.
- Stage 2 audit/history contract:
  - `dashboard/server/utils/optimization-history.ts`
  - Canonical `decision_snapshot_v1` exists and is already wired into scheduled and executed control flows.
- Stage 2 operator input contract:
  - `dashboard/server/api/config/current.get.ts` and `dashboard/server/api/config/save.post.ts`
  - Adds `connected_power_kw` and `market_regime_override` to the saved tenant config.

### Configuration Examples

```json
{
  "battery_soc_min": 0.1,
  "battery_c_rate_discharge": 1.0,
  "ml_forecast_horizon_hours": 24,
  "connected_power_kw": 75,
  "market_regime_override": "auto"
}
```

### Technical Requirements

- Update `docs/Stage 2/plan.md` with a concise execution-status snapshot instead of leaving all steps implied as not started.
- Create one new Stage 2 umbrella tracker set under `.copilot-tracking/` rather than repurposing the March 7 learned-policy migration tracker.
- Backfill the already-landed Stage 2 slices into a dedicated Stage 2 changes log so future work is tracked from the real current baseline.
- Limit any new research to one narrow status-audit refresh only if the new plan needs explicit March 29 file-level evidence for remaining optimizer-core gaps.

## Recommended Approach

Do not start with a broad new research cycle. The correct next move is to create a new Stage 2 umbrella tracker set under `.copilot-tracking/` and treat `docs/Stage 2/plan.md` as the human-readable narrative plan. Keep the March 7 learned-policy migration artifacts as completed precursor work. The new tracker should pre-mark current status as follows: steps 1-3 completed, step 4 not started, step 5 completed, step 6 completed, step 7 in progress, step 8 completed, step 9 in progress, step 10 in progress, step 11 in progress, step 12 not started, and step 13 in progress. The recommended filenames are:

- `20260329-stage2-diploma-mvp-plan.instructions.md`
- `20260329-stage2-diploma-mvp-details.md`
- `20260329-stage2-diploma-mvp-changes.md`
- Companion prompt: `implement-stage2-diploma-mvp.prompt.md`

## Implementation Guidance

- **Objectives**: Separate the active Stage 2 diploma MVP tracker from the older learned-policy migration backlog, preserve accurate progress visibility, and make future implementation work target the correct remaining slices.
- **Key Tasks**: Create a new Stage 2 plan/details/changes set, backfill completed March 29 slices, update `docs/Stage 2/plan.md` with a short tracker pointer and step-status summary, and leave the March 7 migration artifacts as prerequisite history rather than active execution docs.
- **Dependencies**: Existing internal research at `.copilot-tracking/research/20260307-ml-pipeline-trading-logic-research.md`, the March 7 learned-policy migration plan as precursor context, and the landed Stage 2 runtime files under `dashboard/server/**` and `dashboard/app/**`.
- **Success Criteria**: One authoritative Stage 2 tracker exists under `.copilot-tracking/`, `docs/Stage 2/plan.md` no longer implies zero progress, completed March 29 slices are backfilled into a Stage 2 changes log, and future implementation prompts can target remaining Stage 2 work without overloading the learned-policy backlog.
