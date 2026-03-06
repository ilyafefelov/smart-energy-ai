<!-- markdownlint-disable-file -->

# Task Details: Battery Auto Mode Monetization and Notifications

## Research Reference

**Source Research**: #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md

## Phase 1: Auto Mode Decision and Execution Correctness

### Task 1.1: Unify auto-mode state machine and recommendation-driven actuation

Replace split control behavior (widget heuristic path vs control page command path) with one authoritative mode/action pipeline that consumes smart recommendations and records decision source.

- **Files**:
  - `dashboard/server/api/battery/simulate.ts` - Replace module-global heuristic mode handling with tenant-scoped state and recommendation-aware execution decision hook.
  - `dashboard/server/api/control/execute.post.ts` - Make `auto` command trigger recommendation-to-action flow instead of idle-only mapping.
  - `dashboard/server/api/control/status.get.ts` - Return explicit authoritative mode/action state instead of deriving from recent command history.
  - `dashboard/app/pages/control.vue` - Align auto toggle/control actions with unified backend contract.
  - `dashboard/stores/batteryPhysicsStore.ts` - Align client mode toggles with single server contract.
- **Success**:
  - Auto mode always resolves to deterministic action outcomes (`charge|discharge|hold`) with source marker (`ml|dagster|heuristic`).
  - Widget and control page show the same mode and active action state.
  - No fallback path infers mode only from command history.
- **Research References**:
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 9-21) - Heuristic auto behavior and disconnected control paths.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 96-111) - Split-path architecture and non-realized `auto` action mapping.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 225-227) - Technical requirement for recommendation-backed auto decisions.
- **Dependencies**:
  - Tenant context contract from `dashboard/server/utils/tenant-context.ts`.
  - Recommendation endpoint availability (`/api/ml/recommendation` and/or `/api/dagster/recommendation`).

### Task 1.2: Fix control runner contract and eliminate dead execution dependencies

Harden control execution reliability by reconciling Python runner argument contract and either implementing or removing stale script references in scheduling/history APIs.

- **Files**:
  - `dashboard/server/utils/python-runner.js` - Support object-to-CLI arg serialization or enforce typed array contract at call sites.
  - `dashboard/server/api/control/execute.post.ts` - Pass valid python-runner arguments and validate command invocation status.
  - `dashboard/server/api/control/history.get.ts` - Resolve missing script fallback path behavior and mark source provenance.
  - `dashboard/server/api/control/schedule.post.ts` - Validate script integration path for scheduling and fallback semantics.
  - `dashboard/server/api/control/scheduled.get.ts` - Align retrieval path with real backing implementation.
  - `dashboard/server/api/control/schedule/[id].delete.ts` - Align cancel path with verified script/service behavior.
- **Success**:
  - Control APIs do not rely on missing scripts in normal path.
  - Python invocation contract is deterministic and testable.
  - API responses include explicit source metadata for fallback vs primary paths.
- **Research References**:
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 42-50) - Runner mismatch and missing scripts.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 212-221) - Concrete contract mismatch example.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 255-256) - Implementation guidance for runner/script hardening.
- **Dependencies**:
  - Task 1.1 completion.
  - Verified Python script inventory under `energy_ml/scripts/`.

## Phase 2: Realized Earnings Ledger and Historical Truth

### Task 2.1: Extend optimization history for realized economics and transition events

Add realized revenue/cost/net and transition metadata so historical data captures actual monetization outcomes, not only estimated deltas.

- **Files**:
  - `dashboard/server/utils/optimization-history.ts` - Add schema fields for realized economics and transition event metadata with idempotent upsert handling.
  - `dashboard/server/api/control/execute.post.ts` - Persist realized earnings and transition attributes at execution time.
  - `dashboard/server/api/control/schedule.post.ts` - Separate intent rows from execution rows with explicit `execution_status`.
  - `src/models.py` - Keep ORM schema aligned with new optimization history columns.
- **Success**:
  - Every executed auto/manual transition writes one canonical realized-economics row.
  - Intent-only rows are distinguishable from executed rows.
  - Upsert logic remains idempotent by `execution_key`.
- **Research References**:
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 28-35) - Existing persistence and override gaps.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 168-176) - Current persisted fields in execute path.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 242-244) - Recommended realized-economics field set.
- **Dependencies**:
  - Phase 1 completion.
  - PostgreSQL schema migration permissions.

### Task 2.2: Align history and metrics APIs to realized earnings as canonical source

Ensure dashboard and analytics cards/series report realized ledger outcomes first, with explicit fallback labeling when necessary.

- **Files**:
  - `dashboard/server/api/history.ts` - Aggregate realized earnings columns and expose execution-quality metadata.
  - `dashboard/server/api/metrics.ts` - Use realized history totals for savings KPIs before artifacts.
  - `dashboard/server/api/metrics/dashboard.ts` - Stop overriding realized values with recommendation estimates in normal operation.
  - `dashboard/app/stores/metricsStore.ts` - Consume and label realized-vs-fallback source metadata.
- **Success**:
  - Daily/monthly earnings cards match realized execution ledger.
  - `economics_source` clearly indicates when fallback is active.
  - Dashboard totals reconcile with historical series.
- **Research References**:
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 30-35) - History/metrics source behavior and override risk.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 187-193) - API documentation of earnings routes.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 228-232) - Requirements for history/metrics and canonical series.
- **Dependencies**:
  - Task 2.1 completion.

## Phase 3: User Notifications and Reactive Graphs

### Task 3.1: Add corner transition notifications with dedup/debounce and user preference gating

Emit global corner toasts when mode/action changes (`charge`, `discharge`, `hold`, `auto`, `manual`, `idle`) with deterministic IDs and debounce to avoid poll-jitter spam.

- **Files**:
  - `dashboard/app/pages/control.vue` - Add transition watcher using previous/current state with `toast.add({ id })` dedupe and debounce.
  - `dashboard/app/components/Battery/InteractiveIllustration.vue` - Route local feedback to global toasts for consistent UX.
  - `dashboard/app/stores/settingsStore.ts` - Surface notification preference flags used for transition-toasts gating.
  - `dashboard/app/composables/` (new `useControlTransitionNotifications.ts`) - Shared transition->toast mapping logic for reuse.
- **Success**:
  - Transition notifications appear exactly once per state change window.
  - Notification behavior honors user notification preferences.
  - No repeated spam toasts during steady polling.
- **Research References**:
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 16-18) - Existing toast usage without dedupe keys.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 70-83) - Verified dedupe/debounce patterns from Nuxt UI and VueUse.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 245-247) - Recommended notification strategy.
- **Dependencies**:
  - Phase 1 unified state stream.
  - Nuxt UI toast infrastructure availability.

### Task 3.2: Rewire dashboard graphs to canonical realized series and live mode transitions

Update dashboard charts and trend cards to react to real transition events and realized earnings, minimizing synthetic-only visual paths.

- **Files**:
  - `dashboard/app/pages/index.vue` - Replace synthetic weekly savings series fallback with realized history-backed series by default.
  - `dashboard/app/pages/analytics.vue` - Bind mode/earnings visualizations to canonical API data.
  - `dashboard/app/components/ML/ForecastChart.vue` - Add overlays or status rows for executed mode/economic realization where applicable.
  - `dashboard/app/stores/mlPipelineStore.ts` - Expose recommendation+execution linkage state for UI reactivity.
- **Success**:
  - Dashboard earnings and mode charts react to new executed events without manual refresh.
  - Synthetic trend generation is clearly marked fallback-only.
  - Forecast and control widgets no longer present conflicting status/economic signals.
- **Research References**:
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 36-41) - Current chart/recommendation refresh limitations.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 63-66) - Existing trend/fetch wiring locations.
  - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md (Lines 248-250) - Canonical charts/reactivity recommendation.
- **Dependencies**:
  - Phase 2 API canonicalization.
  - Task 3.1 transition event stream.

## Dependencies

- Beads issue: `smart-energy-ai-e9x` (in progress).
- Tenant-aware dashboard API baseline and config contract from earlier planning tracks.
- PostgreSQL `optimization_history` access and migration workflow.
- Control and recommendation API availability in local runtime.

## Success Criteria

- Auto mode executes recommendation-backed profitable actions (or explicit no-op) with deterministic event records.
- Realized earnings are persisted historically and become the canonical source for dashboard totals/graphs.
- Corner notifications are emitted for mode/status changes with dedup/debounce and user-preference gating.
- Dashboard charts and cards react to canonical transition/history data instead of synthetic-only trends.
