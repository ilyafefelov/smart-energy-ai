<!-- markdownlint-disable-file -->
# Release Changes: Battery Auto Mode Monetization and Notifications

**Related Plan**: 20260303-battery-auto-mode-monetization-notifications-plan.instructions.md
**Implementation Date**: 2026-03-03

## Summary

Tracking file for implementation updates of auto-mode control correctness, realized earnings ledger persistence, transition notifications, and reactive dashboard graph alignment.

## Changes

### Added

- `dashboard/app/composables/useControlTransitionNotifications.ts` - Added shared control-transition notification composable with deterministic dedupe IDs, debounce suppression, and settings-gated global toast emission.

### Modified

- `dashboard/server/api/dagster/recommendation.ts` - Added tenant-aware request propagation and tenant metadata in response so recommendation composition respects tenant isolation.
- `dashboard/server/api/dagster/schedule-24h.ts` - Added tenant-aware request propagation and tenant/source metadata for deterministic tenant-scoped schedule responses.
- `dashboard/server/api/dagster/trigger.post.ts` - Switched trigger selection to include upstream dependencies by default (`*asset`) to prevent downstream materialization failures from missing inputs.
- `dashboard/server/api/dagster/trigger.post.ts` - Persisted normalized Dagster schedule snapshots into Postgres `asset_results` with tenant metadata so recommendations can use DB-backed materialized outputs.
- `dashboard/server/api/dagster/recommendation.ts` - Changed source priority to Postgres Dagster snapshot first, then file-backed Dagster asset, then ML API fallback.
- `scripts/read_dagster_schedule.py` - Added Python bridge for reading and normalizing latest Dagster materialized schedule assets into recommendation-ready JSON.
- `dashboard/server/utils/optimization-history.ts` - Extended optimization history insert schema/SQL to store decision source, transition metadata, execution status, and realized economics fields.
- `dashboard/server/api/control/execute.post.ts` - Implemented recommendation-driven auto command resolution (`charge|discharge|hold`) with source fallback chain (`dagster -> ml -> heuristic`), persisted transition/realized fields, and returned requested vs resolved command metadata.
- `dashboard/server/api/control/status.get.ts` - Switched mode/action reporting to authoritative per-tenant control state with fallback to recent history.
- `dashboard/server/api/history.ts` - Added daily realized revenue/cost/net and auto-transition aggregation in optimization history reconciliation output.
- `dashboard/server/api/metrics.ts` - Added realized earnings metrics block and reconciliation metadata propagation from history rows.
- `dashboard/server/api/metrics/dashboard.ts` - Exposed realized metrics in dashboard response and used realized daily net fallback for savings card inputs.
- `dashboard/app/pages/control.vue` - Added deduped/debounced corner transition toasts with tenant-aware settings gating (`general.notificationsEnabled` + `notifications.systemAlerts`).
- `dashboard/server/utils/python-runner.js` - Reworked Python runner to use safe `execFile`, object-to-CLI argument serialization, script existence checks, and robust `energy_ml` path resolution.
- `dashboard/server/api/control/execute.post.ts` - Fixed Python command invocation contract to match script flags and added explicit script availability/fallback source metadata in responses.
- `dashboard/server/api/control/status.get.ts` - Added script availability gating and fallback reason metadata so status path cleanly distinguishes Python execution vs fallback.
- `dashboard/server/api/control/history.get.ts` - Added script availability checks and explicit fallback metadata to eliminate dead Python history script dependency ambiguity.
- `dashboard/server/api/control/schedule.post.ts` - Added script availability checks and fallback provenance metadata for schedule creation when Python schedule script is absent.
- `dashboard/server/api/control/scheduled.get.ts` - Added script availability checks and fallback provenance metadata for scheduled command listing.
- `dashboard/server/api/control/schedule/[id].delete.ts` - Added tenant-safe schedule cancellation filtering plus script availability/fallback metadata.
- `dashboard/server/api/battery/simulate.ts` - Replaced module-global heuristic mode handling with tenant-scoped control mirror and routed manual/auto actions through authoritative `/api/control/execute` decisions.
- `dashboard/stores/batteryPhysicsStore.ts` - Aligned widget mode/power toggles to the unified control execution contract and refreshed state from canonical simulator payloads.
- `dashboard/server/api/control/status.get.ts` - Overlaid Python status with tenant control-mode state so active command/mode remains consistent across control page and widget surfaces.
- `dashboard/app/stores/metricsStore.ts` - Added canonical metrics source ingestion from `/api/metrics`, exposed realized-vs-fallback source labels, and enriched savings tooltips with economics provenance.
- `dashboard/app/pages/index.vue` - Added explicit daily-savings source description text so cards visibly indicate realized ledger vs fallback source.
- `dashboard/server/api/control/schedule.post.ts` - Tagged scheduled intent writes with explicit `execution_status`, `event_type`, and transition/economics metadata fields.
- `dashboard/server/api/control/history.get.ts` - Tagged history backfill writes with explicit execution/transition metadata fields for consistent optimization ledger semantics.
- `src/models.py` - Extended `OptimizationHistory` ORM schema with decision/transition and realized economics columns to match server persistence fields.
- `dashboard/app/pages/control.vue` - Replaced inline transition-toast state machine with `useControlTransitionNotifications` so dedupe/debounce and settings gating are centralized.
- `dashboard/app/components/Battery/InteractiveIllustration.vue` - Routed local control feedback through shared global transition/action toasts with deterministic dedupe keys while preserving inline feedback text.
- `dashboard/app/pages/index.vue` - Rewired 7-day savings trend to canonical `/api/history` realized rows by default (with explicit fallback labeling) and removed stray invalid template token in savings section.
- `dashboard/app/pages/analytics.vue` - Bound historical performance cards and control/system status badges to canonical history/control APIs instead of static placeholder values.
- `dashboard/app/components/ML/ForecastChart.vue` - Added recommendation-to-execution linkage overlay showing live mode/action source and realized-net context from canonical control/history state.
- `dashboard/app/stores/mlPipelineStore.ts` - Added tenant-aware request routing plus `recommendationExecutionLink` state and fetcher to expose recommendation-execution linkage for reactive UI updates.

Note: These Dagster endpoint fixes were implemented outside the strict phase order of the current plan to address a validated runtime reliability blocker discovered during smoke testing (`price_forecast_asset` trigger failure due to missing upstream asset materialization).

### Removed

## Release Summary

**Total Files Affected**: 31

### Files Created (8)

- `dashboard/app/composables/useControlTransitionNotifications.ts` - Shared transition/action notification composable for deduped global toasts.
- `scripts/read_dagster_schedule.py` - Dagster schedule snapshot reader/normalizer used for DB-backed recommendation ingestion.
- `.copilot-tracking/plans/20260303-battery-auto-mode-monetization-notifications-plan.instructions.md` - Task execution checklist and phase tracking.
- `.copilot-tracking/details/20260303-battery-auto-mode-monetization-notifications-details.md` - Detailed per-task implementation requirements.
- `.copilot-tracking/changes/20260303-battery-auto-mode-monetization-notifications-changes.md` - Incremental change log for this implementation track.
- `.copilot-tracking/research/20260303-battery-auto-mode-monetization-notifications-research.md` - Research findings used to drive implementation.
- `.copilot-tracking/research/20260303-forecasting-settings-generation-integration-research.md` - Related forecasting/settings integration research context.
- `.copilot-tracking/research/20260303-settings-generation-enhancements-research.md` - Related settings/generation enhancement research context.

### Files Modified (23)

- `dashboard/server/api/control/execute.post.ts` - Recommendation-driven auto execution, authoritative mode updates, and realized-economics persistence.
- `dashboard/server/api/control/status.get.ts` - Authoritative mode/action overlay with explicit Python fallback metadata.
- `dashboard/server/api/control/history.get.ts` - Script availability guards plus normalized fallback provenance and ledger backfill metadata.
- `dashboard/server/api/control/schedule.post.ts` - Script fallback provenance and explicit scheduled-intent execution metadata.
- `dashboard/server/api/control/scheduled.get.ts` - Scheduled command retrieval fallback provenance hardening.
- `dashboard/server/api/control/schedule/[id].delete.ts` - Tenant-safe cancellation with script fallback metadata.
- `dashboard/server/api/battery/simulate.ts` - Unified tenant-scoped control mirror with authoritative control endpoint integration.
- `dashboard/server/utils/python-runner.js` - Safe Python runner contract with arg serialization and script existence checks.
- `dashboard/server/utils/optimization-history.ts` - Schema + upsert expansion for decision/transition/realized columns.
- `dashboard/server/api/history.ts` - Canonical realized revenue/cost/net and transition reconciliation aggregation.
- `dashboard/server/api/metrics.ts` - Realized metrics block and source/reconciliation metadata exposure.
- `dashboard/server/api/metrics/dashboard.ts` - Dashboard metrics alignment to realized net fallbacks.
- `dashboard/server/api/dagster/recommendation.ts` - Postgres-first Dagster recommendation sourcing with tenant metadata.
- `dashboard/server/api/dagster/schedule-24h.ts` - Tenant-aware schedule retrieval path.
- `dashboard/server/api/dagster/trigger.post.ts` - Upstream-inclusive trigger selection and snapshot persistence.
- `dashboard/stores/batteryPhysicsStore.ts` - Widget control commands routed through canonical control execution contract.
- `dashboard/app/pages/control.vue` - Shared transition toast composable adoption.
- `dashboard/app/components/Battery/InteractiveIllustration.vue` - Shared global action toast emission for interactive controls.
- `dashboard/app/stores/metricsStore.ts` - Canonical economics-source ingestion and realized/fallback labeling.
- `dashboard/app/pages/index.vue` - Canonical history-driven weekly trend chart and source labeling.
- `dashboard/app/pages/analytics.vue` - Canonical history/control bindings for analytics cards and status.
- `dashboard/app/components/ML/ForecastChart.vue` - Execution linkage overlay and canonical mode/action context.
- `dashboard/app/stores/mlPipelineStore.ts` - Tenant-aware recommendation pipeline fetches and recommendation-execution linkage state.

### Files Removed (0)

- None.

### Dependencies & Infrastructure

- **New Dependencies**: None.
- **Updated Dependencies**: None.
- **Infrastructure Changes**: None.
- **Configuration Updates**: `optimization_history` logical schema extended via runtime migration SQL in `dashboard/server/utils/optimization-history.ts`.

### Deployment Notes

- Nuxt production build validated successfully after implementation.
- Existing warning remains about duplicate component name resolution (`NavigationMenu`) in two component paths; unrelated to this release scope.
