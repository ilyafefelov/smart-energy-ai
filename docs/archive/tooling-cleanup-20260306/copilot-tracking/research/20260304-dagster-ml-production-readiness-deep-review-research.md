<!-- markdownlint-disable-file -->

# Task Research Notes: Dagster ML Production Readiness Deep Review

## Research Executed

### File Analysis

- `dashboard/app/pages/index.vue`
  - Main 24h table renders `HOLD` as `—` in Action column (`line 391`), which appears as missing recommendation to users.
  - Main table consumes `timeLabel` from API (`line 608`), so minute offsets from backend (`02:38`) are displayed directly.
- `dashboard/app/components/ML/ForecastChart.vue`
  - Forecast card correctly shows explicit `BUY/SELL/HOLD` labels and summary counts, proving UI can show holds when not masked.
- `dashboard/app/stores/mlPipelineStore.ts`
  - Dagster schedule is the priority source and mapped to `recommended_action`, confirming no local heuristic override when schedule exists.
- `dashboard/server/api/dagster/schedule-24h.ts`
  - API returns schedule from `/api/dagster/recommendation` and summary counts for `BUY/SELL/DISCHARGE/HOLD`.
- `dashboard/server/api/dagster/recommendation.ts`
  - Source preference is `postgres snapshot -> file snapshot -> ml fallback`; latest snapshot is selected by `ORDER BY materialization_time DESC` without freshness gate.
  - `buildScheduleFromDagsterAsset` maps schedule rows by `hour` against price forecast `hour`; this assumes hour semantics are identical.
- `scripts/read_dagster_schedule.py`
  - `_normalize_action` maps positive `action_kw` to `BUY` and negative to `SELL`.
  - Recommendation row selection uses wall-clock hour (`datetime.now().hour`) against schedule `hour` field.
- `src/optimization/milp_scheduler.py`
  - Scheduler emits `action_kw = discharge - charge` (`line 275`), so positive values represent discharge (sell direction), not buy.
- `src/assets/core/optimization_schedule.py`
  - Baseline optimizer also emits horizon-indexed `hour` values (0..23) tied to optimization timestep, not absolute wall-clock hour.
- `src/assets/core/optimization_schedule_milp.py`
  - MILP asset writes `hour` and `action_kw` from optimization result; no explicit absolute timestamp field is persisted.
- `src/definitions.py`
  - Only two schedules exist: daily refresh at `0 6 * * *` and weekly benchmark at `0 3 * * 0`; no sensor/declarative automation for intra-day live updates.
- `dashboard/server/api/prices/current.ts`
  - Forecast timestamps are generated from `new Date(now.getTime() + i * 3600000)`; minute component follows current runtime minute, which propagates to UI labels.
- `dashboard/data/api_smoke_test_report.json`
  - Recent smoke report shows MLflow endpoint degraded/offline characteristics while API still reports success payloads.

### Code Search Results

- `def _normalize_action|action_kw > 0.05|action_kw < -0.05`
  - Found in `scripts/read_dagster_schedule.py` lines `59-63`; sign-to-action mapping is inverted relative to optimizer output semantics.
- `"action_kw": float((discharge[t] - charge[t])`
  - Found in `src/optimization/milp_scheduler.py:275`; positive means discharge.
- `current_hour = datetime.now().hour` and row match by `hour`
  - Found in `scripts/read_dagster_schedule.py:124-125`; wall-clock match is performed on horizon-indexed schedule.
- `text-lg">—`
  - Found in `dashboard/app/pages/index.vue:391`; HOLD is visually suppressed in the main dashboard action column.
- `timeLabel: String(row.time || ... )`
  - Found in `dashboard/app/pages/index.vue:608`; API-provided minute-bearing labels are reused directly.
- `ORDER BY materialization_time DESC`
  - Found in `dashboard/server/api/dagster/recommendation.ts:117`; latest snapshot chosen without staleness threshold.
- `cron_schedule="0 6 * * *"`
  - Found in `src/definitions.py:75`; only daily refresh cadence is configured for core pipeline.

### External Research

- #githubRepo:"dagster-io/dagster-open-platform production architecture patterns"
  - Reference repo positions a full-sized Dagster project as production best-practice structure and operations example.
- #githubRepo:"mlflow/mlflow model registry and deployment lifecycle"
  - Official MLflow repo emphasizes model lifecycle controls (tracking, registry, deployment) as production baseline.
- #fetch:https://docs.dagster.io/deployment/oss/oss-deployment-architecture
  - Dagster OSS production architecture requires long-running services and explicitly calls out daemon role for schedules/sensors/run queue.
- #fetch:https://docs.dagster.io/guides/automate/schedules
  - Schedules are first-class automation for recurring runs; timezone and cadence are explicit and must match operational needs.
- #fetch:https://docs.dagster.io/guides/automate/sensors
  - Sensors support event-driven orchestration, run keys/cursors, and deduplication for reliable live updates.
- #fetch:https://docs.dagster.io/guides/test/asset-checks
  - Asset checks provide data-quality/freshness validation and can block downstream materialization.
- #fetch:https://mlflow.org/docs/latest/ml/tracking/
  - Production tracking setup recommends durable backend/artifact stores and tracking server for team workflows.
- #fetch:https://mlflow.org/docs/latest/ml/model-registry/
  - Model registry adds versioning, lineage, aliases, and governed promotion path (`staging`/`production`).
- #fetch:https://nuxt.com/docs/4.x/getting-started/deployment
  - Nuxt production guidance highlights rendering-mode tradeoffs and recommends targeted client-only patterns over blanket SPA when possible.

### Project Conventions

- Standards referenced: `AGENTS.md`, `vscode-userdata:/.../vuejs3.instructions.md`, `vscode-userdata:/.../task-implementation.instructions.md`, existing `.copilot-tracking/research/*.md` template style.
- Instructions followed: Beads-first workflow (`smart-energy-ai-9xp` claimed), evidence-backed findings only, research-only edits restricted to `.copilot-tracking/research/`.

## Key Discoveries

### Project Structure

The dashboard now correctly prioritizes Dagster schedule data in both the main page and ML forecast card, so the observed symptom is not primarily a stale frontend fallback. The dominant issue is a contract/semantic mismatch between optimization outputs and schedule interpretation, amplified by a UI presentation choice that hides HOLD actions.

Live runtime probe at `http://127.0.0.1:3600` returned:
- `status=success`, `rows=24`, `buy=1`, `sell=0`, `hold=23`
- `rec_source=dagster_postgres_snapshot`
- `selected_client=client_001_kyiv_mall`

This confirms recommendations exist but are sparse and mostly HOLD.

### Implementation Patterns

- Dashboard reads schedule from `/api/dagster/schedule-24h`, which is derived from `/api/dagster/recommendation`.
- Recommendation pipeline reads latest persisted asset snapshot first, then file snapshot, then ML fallback.
- Schedule transformation currently assumes optimizer `hour` values are wall-clock aligned and that `action_kw` sign maps directly to BUY/SELL in a specific direction.
- Orchestration cadence is batch-like (daily), not continuous intraday for live arbitrage.

### Complete Examples

```python
# scripts/read_dagster_schedule.py
# Current mapping inverts optimizer direction semantics.
def _normalize_action(action_kw: float) -> str:
    if action_kw > 0.05:
        return "BUY"
    if action_kw < -0.05:
        return "SELL"
    return "HOLD"
```

```python
# src/optimization/milp_scheduler.py
# Positive means discharge, negative means charge.
"action_kw": float((discharge[t] - charge[t]) / max(self.config.timestep_hours, 1e-9))
```

```typescript
// dashboard/app/pages/index.vue
// HOLD is currently hidden as a dash in the main action table.
<span v-if="price.action === 'BUY'" class="text-lg">Buy</span>
<span v-else-if="price.action === 'SELL'" class="text-lg">Sell</span>
<span v-else class="text-lg">—</span>
```

```python
# scripts/read_dagster_schedule.py
# Uses wall-clock hour against horizon-indexed schedule rows.
current_hour = datetime.now().hour
current_row = next((row for row in schedule if int(row.get("hour", -1)) == current_hour), None)
```

### API and Schema Documentation

- `GET /api/dagster/recommendation`
  - Returns `recommendation`, `schedule_24h`, `strategy_context`, and `source_metadata`.
  - Snapshot source selected from Postgres/file/ML fallback.
- `GET /api/dagster/schedule-24h`
  - Returns normalized `schedule` and summary counters (`buy_hours`, `sell_hours`, `hold_hours`).
- Snapshot persistence model (`asset_results`)
  - Queried by `asset_name`, `tenant_id`, and descending `materialization_time`.
  - Current contract lacks explicit staleness SLA enforcement and lacks explicit horizon-anchor timestamp used by readers.

### Configuration Examples

```python
# src/definitions.py
daily_refresh_schedule = ScheduleDefinition(
    job=daily_data_refresh_job,
    cron_schedule="0 6 * * *",
)

weekly_benchmark_schedule = ScheduleDefinition(
    job=benchmark_job,
    cron_schedule="0 3 * * 0",
)
```

```typescript
// dashboard/server/api/prices/current.ts
const ts = new Date(now.getTime() + i * 3600000)
# Minute component follows runtime minute and propagates to UI labels.
```

### Technical Requirements

- Fix action-direction semantics end-to-end (`action_kw` sign -> user-facing BUY/SELL).
- Introduce explicit schedule horizon anchor (`start_timestamp_utc`) and interpret hours as offsets, not wall-clock labels.
- Add freshness SLA checks for snapshot usage (`max_age_minutes`) with fallback/recompute policy.
- Add data-quality asset checks (nulls/range/monotonic horizon/cardinality of 24 rows/action distribution sanity).
- Add automation for intraday recompute (schedule + sensor/declarative triggers).
- Add contract tests for schedule semantics and UI rendering (`HOLD` visible, time labels normalized to intended display policy).

## Recommended Approach

Adopt a **Contract-First Live Schedule Hardening** approach and make it the single source of truth for production readiness:

1. Define and freeze the schedule contract (`hour_offset`, `start_timestamp_utc`, `action_semantics`, `units`).
2. Correct semantic adapters first (sign mapping + hour-anchor interpretation) before any model tuning.
3. Enforce freshness and quality gates in orchestration (asset checks + automation).
4. Only then tune optimization/ML policy behavior for action density and business performance.

Rationale for selection:
- It addresses both the current user-visible symptom and the highest-risk hidden defects (opposite-direction actions and temporal misalignment).
- It creates a stable substrate for future tuning and deployment scaling.
- It aligns with Dagster production guidance (daemon automation + checks) and MLflow lifecycle governance.

## Implementation Guidance

- **Objectives**: Ensure dashboard and control logic consume a semantically correct, fresh, and validated Dagster schedule in real time.
- **Key Tasks**: (1) Contract/spec + adapter fixes, (2) orchestration freshness + checks + alerting, (3) frontend clarity and contract tests, (4) MLflow governance and deployment hardening.
- **Dependencies**: Dagster daemon enabled in target runtime, Postgres availability for `asset_results`, MLflow tracking server + artifact store, CI pipeline for API/UI contract tests.
- **Success Criteria**: Schedule payload always includes explicit horizon anchor; BUY/SELL direction matches optimizer sign convention; stale snapshots are rejected or auto-refreshed; dashboard action column never appears empty for HOLD; production monitors expose freshness/action-distribution drift with alerting.
