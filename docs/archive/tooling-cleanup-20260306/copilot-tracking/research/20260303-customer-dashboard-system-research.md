<!-- markdownlint-disable-file -->

# Task Research Notes: Customer Dashboard System

## Research Executed

### File Analysis

- `dashboard/nuxt.config.ts`
  - Nuxt runs with `srcDir: 'app'` and `storesDirs: ['./app/stores/**']` (`dashboard/nuxt.config.ts:5`, `dashboard/nuxt.config.ts:16`), so tenant context propagation must start in `dashboard/app/*`.
- `dashboard/app/pages/control.vue`
  - Control UI calls unscoped APIs (`/api/control/status`, `/api/control/history`) and sends static `user_id: 'dashboard_user'` (`dashboard/app/pages/control.vue:629`, `dashboard/app/pages/control.vue:657`, `dashboard/app/pages/control.vue:683`).
- `dashboard/app/stores/metricsStore.ts`
  - Dashboard metrics are fetched from a tenant-agnostic endpoint (`dashboard/app/stores/metricsStore.ts:157`).
- `dashboard/app/stores/batteryStore.ts`
  - Battery status fetch uses a shared endpoint with no tenant selector (`dashboard/app/stores/batteryStore.ts:87`).
- `dashboard/app/stores/pricesStore.ts`
  - Price feed is fetched globally via `/api/prices/current` (`dashboard/app/stores/pricesStore.ts:105`).
- `dashboard/app/stores/mlStore.ts`
  - ML recommendation fetch is global (`dashboard/app/stores/mlStore.ts:38`).
- `dashboard/app/stores/settingsStore.ts`
  - Settings are persisted in one localStorage key (`energy_settings_v1`) without tenant partitioning (`dashboard/app/stores/settingsStore.ts:95`, `dashboard/app/stores/settingsStore.ts:135`).
- `dashboard/server/api/metrics/dashboard.ts`
  - Metrics endpoint composes unscoped internal calls (`/api/metrics`, `/api/prices/current`, `/api/battery/status`, `/api/ml/recommendation`) (`dashboard/server/api/metrics/dashboard.ts:9`, `dashboard/server/api/metrics/dashboard.ts:10`, `dashboard/server/api/metrics/dashboard.ts:11`, `dashboard/server/api/metrics/dashboard.ts:12`).
- `dashboard/server/api/history.ts`
  - SQL aggregation is by timestamp only (no tenant predicate): `FROM optimization_history WHERE timestamp >= NOW() - INTERVAL '45 days' GROUP BY DATE(timestamp)` (`dashboard/server/api/history.ts:61`, `dashboard/server/api/history.ts:62`, `dashboard/server/api/history.ts:63`).
- `dashboard/server/utils/optimization-history.ts`
  - `optimization_history` schema includes operational/economics fields but no `tenant_id` field (`dashboard/server/utils/optimization-history.ts:153`, `dashboard/server/utils/optimization-history.ts:155`, `dashboard/server/utils/optimization-history.ts:162`, `dashboard/server/utils/optimization-history.ts:163`).
- `dashboard/server/api/control/execute.post.ts`
  - In-memory history fallback uses process-global arrays (`globalThis.commandHistory`) before persistence (`dashboard/server/api/control/execute.post.ts:123`, `dashboard/server/api/control/execute.post.ts:124`, `dashboard/server/api/control/execute.post.ts:134`).
- `dashboard/server/api/control/status.get.ts`
  - Control status reads process-global schedules/history (`dashboard/server/api/control/status.get.ts:31`, `dashboard/server/api/control/status.get.ts:37`).
- `dashboard/server/api/control/scheduled.get.ts`
  - Scheduled commands are loaded from `globalThis.scheduledCommands` fallback (`dashboard/server/api/control/scheduled.get.ts:30`).
- `dashboard/server/api/settings/load.ts`
  - Settings are loaded from a single file `data/settings.json` (`dashboard/server/api/settings/load.ts:17`).
- `dashboard/server/api/settings/save.ts`
  - Settings writes target one shared file (`dashboard/server/api/settings/save.ts:17`).
- `dashboard/server/api/settings/import.ts`
  - Import endpoint overwrites shared `data/settings.json` and creates global backups (`dashboard/server/api/settings/import.ts:6`, `dashboard/server/api/settings/import.ts:52`, `dashboard/server/api/settings/import.ts:59`).
- `dashboard/server/api/settings/export.ts`
  - Export endpoint reads shared `data/settings.json` (`dashboard/server/api/settings/export.ts:6`, `dashboard/server/api/settings/export.ts:11`).
- `dashboard/server/utils/battery.ts`
  - Battery state is globally persisted in `data/battery_state.json` (`dashboard/server/utils/battery.ts:4`).
- `dashboard/server/api/config/current.get.ts`
  - Current config endpoint reads one global config file `../energy_ml/configs/user_config.json` (`dashboard/server/api/config/current.get.ts:10`).
- `dashboard/server/api/dagster/assets.get.ts`
  - Asset result listing is global (`FROM asset_results ORDER BY materialization_time DESC LIMIT 50`) without tenant filtering (`dashboard/server/api/dagster/assets.get.ts:43`, `dashboard/server/api/dagster/assets.get.ts:44`, `dashboard/server/api/dagster/assets.get.ts:45`).
- `dashboard/server/api/retraining/start.ts`
  - Retraining jobs are tracked in process-global `activeJobs` and file paths in `data/retraining` keyed only by generated `jobId` (`dashboard/server/api/retraining/start.ts:17`, `dashboard/server/api/retraining/start.ts:35`).
- `dashboard/server/api/retraining/progress.ts`
  - Progress lookup is `jobId`-based file read, not tenant-scoped (`dashboard/server/api/retraining/progress.ts:12`, `dashboard/server/api/retraining/progress.ts:21`).
- `src/assets/multi_tenant/asset_factory.py`
  - Existing tenant-isolation pattern is explicit: normalized tenant IDs, tenant namespace/storage namespace, and leakage guard (`src/assets/multi_tenant/asset_factory.py:21`, `src/assets/multi_tenant/asset_factory.py:34`, `src/assets/multi_tenant/asset_factory.py:35`, `src/assets/multi_tenant/asset_factory.py:143`, `src/assets/multi_tenant/asset_factory.py:144`).
- `src/assets/core/client_state.py`
  - Core data generation already standardizes `tenant_id`, `tenant_namespace`, `storage_namespace` (`src/assets/core/client_state.py:151`, `src/assets/core/client_state.py:152`, `src/assets/core/client_state.py:153`, `src/assets/core/client_state.py:257`, `src/assets/core/client_state.py:258`, `src/assets/core/client_state.py:259`).
- `tests/test_multi_tenant_asset_isolation.py`
  - Test coverage exists for asset-layer tenant isolation, not dashboard API-level scoping (`tests/test_multi_tenant_asset_isolation.py:1`, `tests/test_multi_tenant_asset_isolation.py:44`, `tests/test_multi_tenant_asset_isolation.py:68`, `tests/test_multi_tenant_asset_isolation.py:82`).
- `tests/test_dashboard_economics_api.py`
  - Dashboard API tests validate economics/source alignment but do not validate tenant boundaries.
- `tests/e2e/test_dashboard_e2e.py`
  - E2E tests validate navigation/workflows but contain no tenant-aware assertions.

### Code Search Results

- `tenant|client_id|tenant_id` in `dashboard/server/api/**/*.ts`
  - No tenant markers found in dashboard API handlers (verified grep result), indicating tenant resolution/filtering is not implemented in route layer.
- `globalThis.scheduledCommands|globalThis.commandHistory`
  - Found in control status/history/scheduled/execute/delete handlers, confirming process-global state sharing across requests.
- `data/settings.json|battery_state.json|data/retraining`
  - Found across settings, battery, and retraining handlers, confirming shared file-backed state with no tenant partition.
- `FROM optimization_history` and `GROUP BY DATE(timestamp)`
  - Found in `dashboard/server/api/history.ts` with no tenant predicate.
- `CREATE TABLE IF NOT EXISTS optimization_history`
  - Found in `dashboard/server/utils/optimization-history.ts`; schema has no tenant key.
- Tool usage note
  - `search_subagent` initially returned unresolved absolute file paths for snippets; all final findings in this note were re-verified via direct `read_file`, `grep_search`, and `file_search` evidence.

### External Research

- #githubRepo:"nuxt/nuxt server directory api routes defineEventHandler"
  - Nuxt route file conventions were confirmed from `docs/2.directory-structure/1.server.md` in `nuxt/nuxt` (`4.x`): `server/api` auto-prefixing, method-suffixed files, route params via `getRouterParam`, and query/body helpers.
- #githubRepo:"microsoft/api-guidelines azure api idempotency error schema collections filtering"
  - Azure API guidelines provide concrete contract patterns for idempotency, consistent error envelopes, action routes, filtering, and list responses.
- #fetch:https://nuxt.com/docs/4.x/guide/directory-structure/server
  - Practical Nuxt server examples confirm `defineEventHandler`, method-specific handlers (`.get/.post`), `readBody`, `getQuery`, `createError`, and API namespacing patterns.
- #fetch:https://raw.githubusercontent.com/nuxt/nuxt/4.x/docs/2.directory-structure/1.server.md
  - Source-markdown examples confirm route parameter access and method mapping behavior applicable to tenant route design.
- #fetch:https://h3.dev/guide/basics/handler
  - h3 handler guidance confirms event/context-based middleware patterns that can attach tenant context before route logic.
- #fetch:https://www.postgresql.org/docs/current/ddl-rowsecurity.html
  - PostgreSQL RLS reference confirms policy-based row isolation (`ENABLE ROW LEVEL SECURITY`, `CREATE POLICY`) for shared-table multitenancy.
- #fetch:https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/map-requests
  - Tenant mapping strategies are documented for domain, path/query/header, token claims, and request validation.
- #fetch:https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/approaches/storage-data
  - Multitenant storage guidance highlights shared-table risks, recommends tenant identifier partitioning, and calls out isolation trade-offs.
- #fetch:https://raw.githubusercontent.com/microsoft/api-guidelines/vNext/azure/Guidelines.md
  - API contract guidance includes idempotency, HTTP status discipline, list+filter patterns, and formal error schema shape.
- #fetch:https://raw.githubusercontent.com/microsoft/api-guidelines/vNext/azure/ConsiderationsForServiceDesign.md
  - Design guidance reinforces pagination/filtering consistency, error stability, and change-safe API evolution.

### Project Conventions

- Standards referenced: `AGENTS.md`, `c:\Users\ilyaf\AppData\Roaming\Code - Insiders\User\prompts\vuejs3.instructions.md`, `c:\Users\ilyaf\AppData\Roaming\Code - Insiders\User\prompts\task-implementation.instructions.md`.
- Instructions followed: Beads-first workflow (`bd ready --json`, issue claimed/in-progress), research-only mode constraints, and dashboard Nuxt/Vue conventions.
- Convention check result: `.github/instructions/**` and `copilot/**` were not found in this workspace during file search.

## Key Discoveries

### Project Structure

Dashboard implementation is split into:

- Frontend routes in `dashboard/app/pages/*.vue` (`index.vue`, `analytics.vue`, `control.vue`, `configuration.vue`, `settings.vue`, `monitoring.vue`, `renewable.vue`), all using global stores and tenant-agnostic endpoint paths.
- State stores in `dashboard/app/stores/*.ts` (`metricsStore.ts`, `batteryStore.ts`, `pricesStore.ts`, `mlStore.ts`, `retrainingStore.ts`, `settingsStore.ts`, `mlPipelineStore.ts`, `batteryPhysicsStore.ts`).
- API handlers in `dashboard/server/api/**` (metrics/history/control/settings/config/ml/dagster/retraining/etc.).
- Shared server utilities in `dashboard/server/utils/*.ts` (notably `optimization-history.ts`, `battery.ts`).
- Existing backend tenant-aware generation in `src/assets/core/*.py` and `src/assets/multi_tenant/*.py`.
- Test coverage in `tests/` validates asset-layer isolation but not dashboard/API tenant isolation.

No `dashboard/app/composables` directory currently exists; tenant context composables are not yet implemented.

### Implementation Patterns

Current dashboard is effectively single-tenant at runtime:

- File-backed singleton state is used for settings and battery.
- In-memory singleton state is used for command/schedule/retraining fallbacks.
- SQL queries aggregate across all history rows without tenant filters.
- API handlers do not parse or validate tenant selectors (query/header/path/token).
- Frontend requests do not attach tenant context.

At the same time, backend data generation already has robust tenant metadata patterns (`tenant_id`, namespaces, deterministic normalization, leakage guards). The key gap is contract propagation from dashboard request -> API handler -> storage query/write.

### Complete Examples

```typescript
// Current unscoped history query (cross-tenant risk in shared table)
// dashboard/server/api/history.ts
SELECT
  DATE(timestamp) AS day,
  SUM(COALESCE(cost_baseline, 0)) AS baseline_cost,
  SUM(COALESCE(cost_rl, 0)) AS optimized_cost
FROM optimization_history
WHERE timestamp >= NOW() - INTERVAL '45 days'
GROUP BY DATE(timestamp)
ORDER BY day DESC
LIMIT $1
```

```python
# Existing tenant isolation guard pattern already used in asset factory
# src/assets/multi_tenant/asset_factory.py
if "client_id" in client_df.columns:
    leakage_count = client_df.filter(pl.col("client_id") != client_id).height
    if leakage_count > 0:
        raise ValueError(
            f"Tenant isolation breach: found {leakage_count} rows outside tenant '{client_id}'"
        )
```

```http
GET /api/metrics/dashboard?tenantId=client_001_kyiv_mall HTTP/1.1
Host: localhost:3600
X-Tenant-Id: client_001_kyiv_mall
```

```json
{
  "success": true,
  "tenant": {
    "id": "client_001_kyiv_mall",
    "source": "query_or_header",
    "validated": true
  },
  "metrics": {
    "savingsToday": 1240.45,
    "savingsTrend": "up",
    "savingsTrendValue": 8.2,
    "savingsMonth": 31120.0,
    "forecastAccuracy": 87.1,
    "batteryHealth": 96.3,
    "nextCycleIn": "2h 0m",
    "averagePrice": 10.8,
    "peakPrice": 14.2,
    "offPeakPrice": 7.6,
    "modelVersion": "Phase4F-v1.0",
    "trainingStatus": "active",
    "lastTrainedAt": "2026-03-03T11:14:00Z"
  },
  "source": {
    "economics_source": "optimization_history_db",
    "tenant_filter_applied": true
  }
}
```

```http
POST /api/control/execute HTTP/1.1
Host: localhost:3600
Content-Type: application/json

{
  "tenantId": "client_001_kyiv_mall",
  "command": "charge",
  "power_kw": 3.0,
  "reason": "manual_charge",
  "user_id": "dashboard_user"
}
```

```json
{
  "success": true,
  "tenant": {
    "id": "client_001_kyiv_mall",
    "validated": true
  },
  "command_id": "cmd_1741000000000_1",
  "executed_at": "2026-03-03T14:25:21.330Z",
  "result": {
    "success": true,
    "soc_before": 0.52,
    "new_soc": 0.54,
    "power_kw": 3,
    "estimated_completion": "2026-03-03T15:25:21.330Z"
  },
  "source": "python_controller"
}
```

### API and Schema Documentation

- Current dashboard API contract style
  - Most endpoints return `{ success, ...payload }` with route-specific fields.
  - Error handling is mixed: some handlers return `{ success: false, error }`; others throw `createError`.
- Current storage/query behavior relevant to tenant scope
  - `optimization_history` has no tenant key, and read aggregations are global.
  - `asset_results` list endpoint returns latest materials globally.
  - Settings/battery/retraining use shared files and process-wide maps.
- Existing tenant-aware contract source of truth
  - Asset layer already emits tenant metadata columns and checks for leakage.
- Gap to close
  - Dashboard/API/storage contracts must carry the same tenant keys used in asset generation (`tenant_id` + namespaces).

### Configuration Examples

```text
Current shared state paths (single global namespace):
- dashboard/data/settings.json
- dashboard/data/battery_state.json
- dashboard/data/retraining/<jobId>.json
- energy_ml/configs/user_config.json

Recommended tenant-partitioned path pattern:
- dashboard/data/tenants/<tenantId>/settings.json
- dashboard/data/tenants/<tenantId>/battery_state.json
- dashboard/data/tenants/<tenantId>/retraining/<jobId>.json
- energy_ml/configs/tenants/<tenantId>/user_config.json
```

```sql
-- Optional shared-table hardening (derived from PostgreSQL RLS policy model)
ALTER TABLE optimization_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_rows_only ON optimization_history
USING (tenant_id = current_setting('app.tenant_id', true));
```

### Technical Requirements

- Add tenant resolution contract to dashboard API requests.
- Validate tenant against configured customers before query/write.
- Extend persistence schema/contracts with tenant key(s) for all mutable telemetry and control artifacts.
- Apply tenant filters to every read path that can aggregate shared data.
- Keep API envelopes stable while adding explicit tenant metadata in responses.
- Add tests for positive isolation and negative cross-tenant access attempts.
- Preserve current fallback behavior but make fallback state tenant-scoped.

## Recommended Approach

Implement a **tenant-context-first API boundary** for the dashboard:

1. Resolve tenant at request entry (query/header/path, with explicit validation against known customers).
2. Store tenant context in route-local execution context and require all route handlers to consume it.
3. Persist and query using tenant-keyed contracts (`tenant_id` minimum) for SQL rows and file-backed artifacts.
4. Return tenant metadata in API responses for auditability and smoke-test assertions.

Why this is the best fit for this repo:

- Reuses already-established tenant semantics in `src/assets/multi_tenant/asset_factory.py` and `src/assets/core/client_state.py`.
- Requires minimal frontend behavior change (attach tenant once; stores/pages continue existing patterns).
- Addresses all observed leak vectors (global SQL aggregation, shared files, process-global fallbacks) with one consistent contract.

## Implementation Guidance

- **Objectives**: Deliver tenant-scoped dashboard metrics and control flows for at least two customers with no cross-tenant data exposure.
- **Key Tasks**: Add tenant resolution middleware/utility; propagate tenant through store requests; update API handlers to filter by tenant; add tenant fields to persistence schema/writes; partition file-backed state by tenant; add tenant-isolation tests.
- **Dependencies**: `customers.yaml`/customer registry, dashboard server API handlers under `dashboard/server/api/**`, shared utilities under `dashboard/server/utils/**`, frontend stores/pages under `dashboard/app/**`.
- **Success Criteria**: Every dashboard data/control endpoint enforces tenant scope; no global shared reads without tenant filter; test suite includes cross-tenant denial checks; API smoke can assert tenant echo and source alignment.

Likely impacted files for implementation planning:

- `dashboard/app/pages/index.vue`
- `dashboard/app/pages/control.vue`
- `dashboard/app/pages/analytics.vue`
- `dashboard/app/pages/configuration.vue`
- `dashboard/app/pages/settings.vue`
- `dashboard/app/stores/metricsStore.ts`
- `dashboard/app/stores/batteryStore.ts`
- `dashboard/app/stores/pricesStore.ts`
- `dashboard/app/stores/mlStore.ts`
- `dashboard/app/stores/retrainingStore.ts`
- `dashboard/app/stores/settingsStore.ts`
- `dashboard/app/stores/mlPipelineStore.ts`
- `dashboard/app/composables/` (directory currently absent; likely add tenant context composable)
- `dashboard/server/api/metrics/dashboard.ts`
- `dashboard/server/api/metrics.ts`
- `dashboard/server/api/history.ts`
- `dashboard/server/api/control/status.get.ts`
- `dashboard/server/api/control/history.get.ts`
- `dashboard/server/api/control/scheduled.get.ts`
- `dashboard/server/api/control/schedule.post.ts`
- `dashboard/server/api/control/execute.post.ts`
- `dashboard/server/api/control/schedule/[id].delete.ts`
- `dashboard/server/api/config/current.get.ts`
- `dashboard/server/api/settings/load.ts`
- `dashboard/server/api/settings/save.ts`
- `dashboard/server/api/settings/import.ts`
- `dashboard/server/api/settings/export.ts`
- `dashboard/server/api/retraining/start.ts`
- `dashboard/server/api/retraining/progress.ts`
- `dashboard/server/api/retraining/cancel.ts`
- `dashboard/server/api/dagster/assets.get.ts`
- `dashboard/server/api/dagster/recommendation.ts`
- `dashboard/server/utils/optimization-history.ts`
- `dashboard/server/utils/battery.ts`
- `tests/test_dashboard_economics_api.py`
- `tests/e2e/test_dashboard_e2e.py`
- `tests/test_multi_tenant_asset_isolation.py`
- `tests/` new dashboard tenant-isolation tests (API + e2e)