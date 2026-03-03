<!-- markdownlint-disable-file -->
# Release Changes: Customer Dashboard System

**Related Plan**: `.copilot-tracking/plans/20260303-customer-dashboard-system-plan.instructions.md`
**Implementation Date**: 2026-03-03

## Summary

Implemented end-to-end tenant-aware dashboard behavior across API boundaries, persistence/state paths, frontend request propagation, and isolation-focused validation guardrails.

## Changes

### Added

- `.copilot-tracking/changes/20260303-customer-dashboard-system-changes.md` - Added release tracking document for progressive implementation updates.
- `dashboard/server/utils/tenant-context.ts` - Added shared tenant resolution and validation utilities backed by `customers.yaml` with stable invalid-tenant error envelopes.
- `dashboard/server/api/tenants.get.ts` - Added tenant discovery endpoint for frontend selectors and tenant-context bootstrapping.
- `dashboard/app/composables/useTenantContext.ts` - Added shared tenant selection composable with persistence and request helper metadata.
- `tests/test_dashboard_tenant_isolation.py` - Added API-level tenant isolation regression tests for control history and settings partitioning.

### Modified

- `.copilot-tracking/prompts/implement-customer-dashboard-system.prompt.md` - Updated frontmatter and changed unresolved tracking-file reference to a concrete path literal.
- `dashboard/server/api/metrics/dashboard.ts` - Added tenant-context resolution, tenant-propagated internal fetches, and tenant metadata in metrics responses.
- `dashboard/server/api/metrics.ts` - Enforced tenant-scoped internal API reads and added tenant/source metadata to the aggregated metrics contract.
- `dashboard/server/api/history.ts` - Added tenant resolution, tenant-scoped internal fetches, and tenant-filtered canonical history source selection.
- `dashboard/server/api/control/history.get.ts` - Scoped command history by tenant and added tenant/source metadata to response payloads.
- `dashboard/server/api/control/status.get.ts` - Scoped status fallback state by tenant and attached tenant validation metadata.
- `dashboard/server/api/control/scheduled.get.ts` - Scoped scheduled command listings by tenant with tenant filter metadata.
- `.copilot-tracking/plans/20260303-customer-dashboard-system-plan.instructions.md` - Marked Phase 1 tasks complete after implementing tenant-context API boundary and tenant-scoped read paths.
- `dashboard/server/utils/optimization-history.ts` - Added `tenant_id` schema/index support and tenant-aware persistence contract for optimization history upserts.
- `dashboard/server/api/control/execute.post.ts` - Added tenant-scoped command execution context and persisted optimization history rows with `tenant_id`.
- `dashboard/server/api/control/schedule.post.ts` - Added tenant-scoped schedule intent handling and persisted scheduled intents with `tenant_id`.
- `dashboard/server/api/control/history.get.ts` - Included `tenant_id` in optimization-history backfill writes and tenant-aware execution key generation.
- `src/models.py` - Added ORM `tenant_id` field and tenant-timestamp index alignment for `optimization_history`.
- `dashboard/server/api/settings/load.ts` - Moved settings reads to `data/tenants/<tenantId>/settings.json` with default-tenant legacy fallback.
- `dashboard/server/api/settings/save.ts` - Persisted settings writes under `data/tenants/<tenantId>/settings.json`.
- `dashboard/server/api/settings/import.ts` - Scoped import target and backups to tenant-specific directories under `data/tenants/<tenantId>/`.
- `dashboard/server/api/settings/export.ts` - Scoped exports to tenant-specific settings and included tenant metadata in export payload.
- `dashboard/server/utils/battery.ts` - Added tenant-aware battery state file resolution and tenant-scoped read/write/simulation helpers.
- `dashboard/server/api/battery/status.ts` - Resolved tenant at API boundary and routed battery status/simulation through tenant-scoped state files.
- `dashboard/server/api/retraining/start.ts` - Partitioned retraining progress files by tenant and keyed in-memory job state by `<tenantId>:<jobId>`.
- `dashboard/server/api/retraining/progress.ts` - Resolved retraining progress and metrics artifacts from tenant-specific directories.
- `dashboard/server/api/retraining/cancel.ts` - Scoped cancellation to tenant-specific retraining state files.
- `dashboard/server/api/config/current.get.ts` - Added tenant-specific config path resolution with legacy fallback metadata.
- `.copilot-tracking/plans/20260303-customer-dashboard-system-plan.instructions.md` - Marked Phase 2 tasks complete after tenant-id persistence and tenant state partitioning implementation.
- `dashboard/server/api/battery.ts` - Divergence from plan file: tenant-scoped battery aggregate endpoint updates were added because utility-only battery path changes would not take effect without endpoint tenant propagation.
- `dashboard/server/api/battery/simulate.ts` - Divergence from plan file: tenant-scoped simulation endpoint updates were added to prevent cross-tenant writes through simulation controls.
- `dashboard/server/utils/tenant-context.ts` - Added tenant listing exports used by frontend tenant selector API.
- `dashboard/app/stores/metricsStore.ts` - Added tenant-aware request propagation for dashboard metrics polling.
- `dashboard/app/stores/batteryStore.ts` - Added tenant-aware request propagation for battery status polling.
- `dashboard/app/stores/pricesStore.ts` - Added tenant-aware request propagation for price fetches used in dashboard/analytics views.
- `dashboard/app/stores/retrainingStore.ts` - Added tenant-aware retraining start/progress/cancel request propagation.
- `dashboard/app/stores/settingsStore.ts` - Switched settings load/save behavior to tenant-scoped backend APIs with tenant-scoped local fallback caching.
- `dashboard/stores/batteryPhysicsStore.ts` - Divergence from plan file: propagated tenant context into simulator control calls to prevent default-tenant coupling during interactive control actions.
- `dashboard/app/pages/index.vue` - Added tenant selector and tenant-change refresh workflow for dashboard cards and stores.
- `dashboard/app/pages/control.vue` - Added tenant selector and tenant-aware control/history/schedule request propagation.
- `dashboard/app/pages/analytics.vue` - Added tenant selector and tenant-change analytics refresh behavior.
- `dashboard/app/pages/settings.vue` - Added tenant selector and tenant-aware settings reload flow.
- `tests/test_dashboard_economics_api.py` - Added tenant-scoped metadata assertions and invalid-tenant envelope checks.
- `tests/e2e/test_dashboard_e2e.py` - Updated E2E base URL to 3600 and added tenant switch persistence flow coverage.
- `dashboard/scripts/api_smoke_test.ps1` - Added tenant-parameterized smoke checks and cross-tenant history leakage assertions.
- `.copilot-tracking/plans/20260303-customer-dashboard-system-plan.instructions.md` - Marked Phase 3 tasks complete after frontend propagation and guardrail implementation.

### Removed

- None yet.

## Release Summary

### Files Created

- `dashboard/server/utils/tenant-context.ts` - Shared tenant resolution/validation and tenant listing helpers.
- `dashboard/server/api/tenants.get.ts` - Tenant discovery endpoint for frontend selectors.
- `dashboard/app/composables/useTenantContext.ts` - Frontend tenant state and request helper composable.
- `tests/test_dashboard_tenant_isolation.py` - Tenant isolation API regression suite.
- `.copilot-tracking/changes/20260303-customer-dashboard-system-changes.md` - Progressive release tracking log.

### Files Modified

- `.copilot-tracking/plans/20260303-customer-dashboard-system-plan.instructions.md` - All phases/tasks marked complete.
- `src/models.py` - Added ORM tenant key/index alignment.
- `dashboard/server/utils/optimization-history.ts` - Tenant-aware schema/index/write contract.
- `dashboard/server/api/history.ts` - Tenant-filtered canonical economics source path.
- `dashboard/server/api/metrics.ts` - Tenant-aware aggregate metrics composition.
- `dashboard/server/api/metrics/dashboard.ts` - Tenant-aware dashboard metrics composition.
- `dashboard/server/api/control/history.get.ts` - Tenant-filtered history reads and tenant-aware persistence backfill.
- `dashboard/server/api/control/status.get.ts` - Tenant-filtered fallback status view.
- `dashboard/server/api/control/scheduled.get.ts` - Tenant-filtered scheduled command listings.
- `dashboard/server/api/control/execute.post.ts` - Tenant-aware command execution and canonical write payload.
- `dashboard/server/api/control/schedule.post.ts` - Tenant-aware schedule intent persistence.
- `dashboard/server/api/settings/load.ts` - Tenant-partitioned settings reads.
- `dashboard/server/api/settings/save.ts` - Tenant-partitioned settings writes.
- `dashboard/server/api/settings/import.ts` - Tenant-partitioned import and backups.
- `dashboard/server/api/settings/export.ts` - Tenant-partitioned export.
- `dashboard/server/utils/battery.ts` - Tenant-partitioned battery state helpers.
- `dashboard/server/api/battery/status.ts` - Tenant-aware battery status handling.
- `dashboard/server/api/battery.ts` - Tenant-aware battery aggregate API.
- `dashboard/server/api/battery/simulate.ts` - Tenant-aware simulator control API.
- `dashboard/server/api/retraining/start.ts` - Tenant-partitioned retraining runtime files and tenant-keyed in-memory jobs.
- `dashboard/server/api/retraining/progress.ts` - Tenant-partitioned retraining progress reads.
- `dashboard/server/api/retraining/cancel.ts` - Tenant-partitioned retraining cancellation.
- `dashboard/server/api/config/current.get.ts` - Tenant-scoped config path resolution.
- `dashboard/app/stores/metricsStore.ts` - Tenant request propagation.
- `dashboard/app/stores/batteryStore.ts` - Tenant request propagation.
- `dashboard/app/stores/pricesStore.ts` - Tenant request propagation.
- `dashboard/app/stores/retrainingStore.ts` - Tenant request propagation.
- `dashboard/app/stores/settingsStore.ts` - Tenant-scoped backend persistence integration.
- `dashboard/stores/batteryPhysicsStore.ts` - Tenant request propagation for simulator actions.
- `dashboard/app/pages/index.vue` - Tenant selector and refresh on tenant switch.
- `dashboard/app/pages/control.vue` - Tenant selector and tenant-scoped control operations.
- `dashboard/app/pages/analytics.vue` - Tenant selector and tenant-scoped analytics refresh.
- `dashboard/app/pages/settings.vue` - Tenant selector and tenant-scoped settings reload.
- `tests/test_dashboard_economics_api.py` - Tenant assertions and invalid-tenant checks.
- `tests/e2e/test_dashboard_e2e.py` - Port update and tenant switch persistence test.
- `dashboard/scripts/api_smoke_test.ps1` - Tenant-parameterized smoke assertions.

### Files Removed

- None.

### Dependencies & Infrastructure

- **New Dependencies**: None.
- **Updated Dependencies**: None.
- **Infrastructure Changes**: Added tenant-scoped runtime state directory convention under `dashboard/data/tenants/<tenantId>/`.
- **Configuration Updates**: Dashboard APIs now include tenant metadata and tenant-filter assertions in key responses.

### Deployment Notes

Run `npm --prefix dashboard run build` to verify Nuxt production build integrity, and run `pytest tests/test_dashboard_economics_api.py tests/test_dashboard_tenant_isolation.py -q` plus `dashboard/scripts/api_smoke_test.ps1 -BaseUrl http://127.0.0.1:3600` to validate tenant-isolation checks.
