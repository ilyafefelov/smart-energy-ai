<!-- markdownlint-disable-file -->

# Task Details: Customer Dashboard System

## Research Reference

**Source Research**: #file:../research/20260303-customer-dashboard-system-research.md

## Phase 1: Tenant Context and API Boundary

### Task 1.1: Add tenant resolution and validation contract

Introduce a shared tenant-context utility that resolves tenant from query/header/body, validates against `customers.yaml`, and returns normalized tenant metadata for API handlers.

- **Files**:
  - `dashboard/server/utils/tenant-context.ts` - Create tenant resolution + validation utilities and normalized tenant descriptor helpers.
  - `customers.yaml` - Confirm active tenant IDs used for validation and default tenant handling.
  - `dashboard/server/api/**` - Apply shared tenant resolver at route boundaries that mutate/read tenant-sensitive data.
- **Success**:
  - Tenant context is resolved consistently for dashboard API handlers.
  - Invalid or unknown tenant requests fail with stable error envelope.
  - Response payloads include tenant metadata (`tenant.id`, `tenant.validated`).
- **Research References**:
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 66-67) - No existing tenant markers in API handlers.
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 281-286) - Recommended tenant-context-first API boundary.
  - #fetch:https://nuxt.com/docs/4.x/guide/directory-structure/server - Nuxt server route and handler conventions.
- **Dependencies**:
  - `customers.yaml` availability and consistency with generated tenant IDs.
  - Existing Nuxt/h3 server route patterns in `dashboard/server/api/**`.

### Task 1.2: Enforce tenant scoping for metrics/history/control reads

Apply tenant filtering across dashboard-facing metrics/history/control API handlers and remove shared unscoped read behavior.

- **Files**:
  - `dashboard/server/api/metrics/dashboard.ts` - Pass tenant context into internal metrics dependencies.
  - `dashboard/server/api/metrics.ts` - Enforce tenant-aware aggregation and source metadata.
  - `dashboard/server/api/history.ts` - Add tenant predicate to `optimization_history` reads.
  - `dashboard/server/api/control/history.get.ts` - Scope history reads/fallback by tenant.
  - `dashboard/server/api/control/status.get.ts` - Scope status and queue summaries by tenant.
  - `dashboard/server/api/control/scheduled.get.ts` - Scope scheduled command listings by tenant.
- **Success**:
  - Metrics/history/control endpoints return only tenant-scoped data.
  - Source metadata reports tenant filter application status.
  - No cross-tenant rows are returned for shared DB datasets.
- **Research References**:
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 23-34) - Unscoped metrics/control endpoint behavior.
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 72-75) - Unscoped SQL patterns and missing tenant key in schema.
  - #githubRepo:"microsoft/api-guidelines azure api idempotency error schema collections filtering" - Stable list/filter contract patterns.
- **Dependencies**:
  - Task 1.1 completion.
  - Tenant metadata available in storage/query layer.

## Phase 2: Tenant-Scoped Persistence and State

### Task 2.1: Add tenant key to optimization history contract

Extend optimization history writes/reads so every persisted control/economics record carries `tenant_id` and reads enforce tenant predicate.

- **Files**:
  - `dashboard/server/utils/optimization-history.ts` - Add `tenant_id` column, index, and persistence payload field.
  - `dashboard/server/api/control/execute.post.ts` - Persist tenant-aware execution records.
  - `dashboard/server/api/control/schedule.post.ts` - Persist tenant-aware schedule intent metadata.
  - `dashboard/server/api/history.ts` - Filter on `tenant_id` and preserve economics provenance contract.
  - `src/models.py` - Align ORM schema for `optimization_history.tenant_id`.
- **Success**:
  - New and upserted `optimization_history` rows include `tenant_id`.
  - Tenant-scoped query path uses `WHERE tenant_id = $n`.
  - Existing API contracts remain backward-compatible with added tenant metadata.
- **Research References**:
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 25-29) - Current global history query and schema gap.
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 237-244) - API/schema gap to close.
  - #fetch:https://www.postgresql.org/docs/current/ddl-rowsecurity.html - Optional RLS hardening path.
- **Dependencies**:
  - Task 1.1 completion.
  - Existing canonical write contract from `smart-energy-ai-jj7`.

### Task 2.2: Partition file-backed runtime state by tenant

Move shared file-backed settings/battery/retraining/config state into tenant namespaced paths to avoid cross-tenant leakage.

- **Files**:
  - `dashboard/server/api/settings/load.ts` - Read from tenant path under `dashboard/data/tenants/<tenantId>/`.
  - `dashboard/server/api/settings/save.ts` - Write tenant-specific settings file.
  - `dashboard/server/api/settings/import.ts` - Import/export using tenant-specific paths and backups.
  - `dashboard/server/api/settings/export.ts` - Export tenant-specific settings snapshot.
  - `dashboard/server/utils/battery.ts` - Read/write tenant-specific battery state file.
  - `dashboard/server/api/retraining/start.ts` - Scope retraining state files by tenant.
  - `dashboard/server/api/retraining/progress.ts` - Resolve progress from tenant namespace.
  - `dashboard/server/api/retraining/cancel.ts` - Cancel scoped jobs safely by tenant.
  - `dashboard/server/api/config/current.get.ts` - Resolve tenant-specific config path.
- **Success**:
  - Runtime state files are isolated per tenant path.
  - Fallback in-memory structures are tenant-keyed maps, not process-global shared arrays.
  - File import/export actions never overwrite another tenant's state.
- **Research References**:
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 35-52) - Shared-file and global-state risk map.
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 248-259) - Tenant-partitioned path recommendation.
  - #fetch:https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data - Multitenant storage isolation guidance.
- **Dependencies**:
  - Task 1.1 completion.
  - Existing dashboard data directory write permissions.

## Phase 3: Tenant-Aware Dashboard UX and Guardrails

### Task 3.1: Add frontend tenant selector and request propagation

Introduce tenant selection at dashboard UI/store level and append tenant context to metrics/control/settings/retraining API requests.

- **Files**:
  - `dashboard/app/composables/useTenantContext.ts` - New tenant context composable for selected tenant state.
  - `dashboard/app/pages/index.vue` - Add tenant selector UI and bind dashboard cards to selected tenant.
  - `dashboard/app/pages/control.vue` - Send tenant context with control operations and polling.
  - `dashboard/app/pages/analytics.vue` - Scope analytics requests by tenant.
  - `dashboard/app/pages/settings.vue` - Scope load/save/import/export by tenant.
  - `dashboard/app/stores/metricsStore.ts` - Include tenant query/header in metrics fetches.
  - `dashboard/app/stores/batteryStore.ts` - Scope battery status requests.
  - `dashboard/app/stores/retrainingStore.ts` - Scope retraining start/progress/cancel by tenant.
- **Success**:
  - Dashboard can switch between at least two tenants.
  - API requests from stores/pages consistently include tenant context.
  - Tenant shown in UI matches tenant returned by API metadata.
- **Research References**:
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 112-121) - Current dashboard structure and missing composables.
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 303-315) - Likely impacted frontend files.
  - #fetch:https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/map-requests - Tenant mapping strategies.
- **Dependencies**:
  - Phases 1 and 2 completion.
  - Stable tenant resolver behavior in API layer.

### Task 3.2: Add tenant isolation tests and smoke assertions

Expand API/e2e/smoke validation to assert no cross-tenant leakage and verify tenant echo/source metadata.

- **Files**:
  - `tests/test_dashboard_economics_api.py` - Add tenant-scoped endpoint assertions and cross-tenant mismatch checks.
  - `tests/e2e/test_dashboard_e2e.py` - Add tenant switch flow assertions for dashboard views.
  - `dashboard/scripts/api_smoke_test.ps1` - Add tenant parameterized checks and no-leakage assertions.
  - `tests/` (new `test_dashboard_tenant_isolation.py`) - API-level negative/positive tenant isolation test matrix.
- **Success**:
  - Automated tests fail on cross-tenant leakage.
  - Smoke output reports tenant assertion pass/fail explicitly.
  - Acceptance criteria validated for at least two tenants.
- **Research References**:
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 57-62) - Current test gap.
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 276-277) - Required tenant isolation assertions.
  - #file:../research/20260303-customer-dashboard-system-research.md (Lines 337-340) - Impacted test files.
- **Dependencies**:
  - Phase 3.1 completion.

## Dependencies

- Claimed Beads issue: `smart-energy-ai-djb`.
- Tenant registry source: `customers.yaml`.
- Dashboard runtime on port `3600` and Dagster coexistence on `3000`.
- PostgreSQL availability for tenant-scoped `optimization_history` reads/writes.

## Success Criteria

- Dashboard renders tenant-scoped KPIs and control data for at least two configured tenants.
- API/storage/query layers enforce tenant boundaries with no cross-tenant leakage.
- Automated API/e2e/smoke validation includes tenant-scoping assertions and passes.
