<!-- markdownlint-disable-file -->

# Task Research Notes: Optimization History Data Truth Hardening

## Research Executed

### File Analysis

- `dashboard/server/api/control/execute.post.ts`
  - Current write path persists rows for both Python and simulation execution, but economics are still derived via `resolveCurrentPriceKwh + durationHours + optimizationMultiplier`.
- `dashboard/server/utils/optimization-history.ts`
  - Runtime helper creates DB/schema if missing and inserts rows with parameterized SQL; no upsert/idempotency key exists.
- `dashboard/server/api/history.ts`
  - Read priority is `optimization_history_db -> dagster.asset_results -> ppo_validation_artifact -> analytics_cache_fallback`.
- `dashboard/server/api/metrics.ts`
  - Metrics aggregate `/api/history` and fallback to PPO artifact/analytics cache when needed.
- `dashboard/server/api/control/history.get.ts`
  - Control history still falls back to in-memory command history when Python history script is unavailable.
- `src/models.py`
  - Canonical ORM schema defines `optimization_history` columns (`predicted_action`, `actual_action`, `cost_baseline`, `cost_rl`, SOC/load/solar fields).
- `data/results/ppo_validation_feb2026.json`
  - Artifact provides fixed baseline/optimized/savings numbers currently used as economics fallback.
- `dashboard/scripts/api_smoke_test.ps1`
  - Existing smoke harness already validates `/api/control/execute`, `/api/history`, `/api/metrics` and can be reused as gate.

### Code Search Results

- `optimization_history|cost_rl|cost_baseline|predicted_action`
  - Found in `dashboard/server/utils/optimization-history.ts`, `dashboard/server/api/history.ts`, `src/models.py` with aligned schema intent.
- `economics_source|backend_priority`
  - Found in `dashboard/server/api/history.ts` and `dashboard/server/api/metrics.ts`, confirming provenance signaling is already part of API contract.
- `job-*.json|model_job-*.pkl`
  - Generated runtime artifacts are excluded by updated gitignore and should not be part of canonical economics storage.

### External Research

- #githubRepo:"brianc/node-postgres parameterized query pool"
  - Pooling should reuse a bounded `Pool`; parameterized statements (`$1..$n`) are preferred for safety and consistency.
- #fetch:https://node-postgres.com/features/pooling
  - Reuse one pool per process; avoid leaked clients; use `pool.query` for simple statements and `pool.end()` on shutdown.
- #fetch:https://node-postgres.com/features/queries
  - Use parameterized queries for values; identifiers cannot be parameterized and must be sanitized/whitelisted.
- #fetch:https://www.postgresql.org/docs/current/sql-createdatabase.html
  - `CREATE DATABASE` cannot run inside transaction blocks and needs elevated privileges/`CREATEDB`.
- #fetch:https://www.postgresql.org/docs/current/sql-insert.html
  - `INSERT ... ON CONFLICT` provides atomic upsert semantics and allows `RETURNING` for deterministic write confirmation.
- #fetch:https://h3.dev/guide/basics/handler
  - Event handlers can be plain async functions or typed handlers; middleware and context-driven behavior are standard patterns.

### Project Conventions

- Standards referenced: `AGENTS.md`, `vscode-userdata:/.../vuejs3.instructions.md`, `vscode-userdata:/.../task-implementation.instructions.md`.
- Instructions followed: Beads-first tracking, backend-first deterministic sourcing, contract-preserving API evolution, explicit source metadata.

## Key Discoveries

### Project Structure

The dashboard server is already split into control-write and metrics-read boundaries. `execute.post.ts` writes operational rows; `history.ts` and `metrics.ts` aggregate and expose economics with source metadata. ML recalculation writes cache artifacts (`latest_ml_results.json`, `analytics_cache.json`) that currently remain fallback sources.

### Implementation Patterns

The repository uses runtime-safe fallbacks when dependencies fail (Python scripts, DB availability). Current persistence bootstraps DB/schema on demand in Node, while ORM schema in `src/models.py` defines equivalent structure in Python services. This duality is functional but risks drift without a reconciliation plan.

### Complete Examples

```typescript
// Current read priority in history API (verified pattern)
const appDbRows = await fetchAppDbHistory(limitDays)
const dagsterRows = appDbRows ? null : await fetchDagsterAssetHistory(limitDays)
const ppoRows = appDbRows || dagsterRows ? null : buildRowsFromPpoValidation(ppoValidation, limitDays)

const economicsSource = appDbRows
  ? 'optimization_history_db'
  : dagsterRows
    ? 'dagster_asset_results'
    : ppoRows
      ? 'ppo_validation_artifact'
      : 'analytics_cache_fallback'
```

```typescript
// Current write in execute path (verified pattern)
await persistOptimizationHistory({
  timestamp: command.timestamp,
  predicted_action: mapCommandToAction(command.command),
  actual_action: mapCommandToAction(command.command),
  cost_baseline: Number.isFinite(baselineCost) ? baselineCost : null,
  cost_rl: Number.isFinite(optimizedCost) ? optimizedCost : null,
  battery_soc_start: Number.isFinite(socBefore) ? socBefore : null,
  battery_soc_end: Number.isFinite(socAfter) ? socAfter : null,
  solar_actual: null,
  load_actual: null,
})
```

### API and Schema Documentation

- `POST /api/control/execute`
  - Accepts command payload (`charge|discharge|hold|auto`, `power_kw`, `duration_minutes`) and now triggers DB persistence.
- `GET /api/history`
  - Returns 7-day rows (`cost_baseline`, `cost_optimized`, `savings`, `battery_actions`) with provenance in `source.economics_source`.
- `GET /api/metrics`
  - Aggregates totals/averages from `/api/history` and exposes ROI/forecast with fallback metadata.
- `optimization_history` schema (ORM + Node SQL)
  - Columns: `timestamp`, `predicted_action`, `actual_action`, `cost_baseline`, `cost_rl`, `battery_soc_start`, `battery_soc_end`, `solar_actual`, `load_actual`.

### Configuration Examples

```text
# Effective DB config precedence currently in writer
APP_DB_NAME -> OPTIMIZATION_DB_NAME -> smart_energy_ai
APP_DB_HOST -> DB_HOST -> localhost
APP_DB_PORT -> DB_PORT -> 5432
APP_DB_USER -> DB_USER -> dagster
APP_DB_PASSWORD -> DB_PASSWORD -> dagster
DATABASE_URL is parsed when present
```

### Technical Requirements

- Preserve API response contracts while replacing heuristic cost calculations with canonical inputs.
- Add idempotent/atomic write behavior to prevent duplicate economics rows from retries/replays.
- Align Python-controller paths and scheduler execution with the same persistence contract.
- Add reconciliation/backfill flow to correct historical rows when more accurate telemetry becomes available.
- Keep smoke validation (`dashboard/scripts/api_smoke_test.ps1`) green after each phase.

## Recommended Approach

Use a **single-source economics write contract** centered on `optimization_history` with atomic/idempotent inserts and telemetry-backed cost computation, then treat artifact sources as emergency fallback only. This approach keeps existing API contracts intact, leverages current provenance fields, and removes dependence on static PPO artifacts for normal operations.

## Implementation Guidance

- **Objectives**: Ensure `optimization_history` is continuously populated from real execution flows and becomes the normal source for `/api/history` and `/api/metrics`.
- **Key Tasks**: (1) Harden write semantics (idempotency/upsert/transaction boundaries), (2) Replace heuristic cost math with canonical interval inputs, (3) Add reconciliation/backfill + validation tests.
- **Dependencies**: PostgreSQL privileges for DB/schema operations, stable `prices/current` signal or equivalent canonical tariff source, Python control scripts and scheduler integration points.
- **Success Criteria**: `/api/history` consistently reports `optimization_history_db`; fallback usage is exceptional and observable; aggregate drift between DB rows and metrics output is within defined tolerance.
