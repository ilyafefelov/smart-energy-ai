# Dataset Lineage And Freshness SLA

This document defines the current supervisor-facing lineage and freshness expectations for the Bronze, Silver, and Gold dataset package.

These are operating targets and contract notes for the current local and development runtime. They are not external service-level guarantees, and they intentionally distinguish between code-enforced checks, Dagster asset-check enforcement, and presentation-level expectations documented for review and supervision.

## Lineage Principles

The current runtime already exposes several strong lineage anchors:

- Forecast lineage: `forecast_run_id`, `forecast_model_name`, `forecast_model_family`, `forecast_model_version`, `forecast_window_start_utc`, `forecast_window_end_utc`
- Optimization lineage: `optimization_run_id`, `algorithm`, `solver`, plus rolling-window metadata for bounded recomputation
- MLflow lineage: `model_id`, `run_id`, `artifact_uri`, model metrics, and logged timestamps
- Promotion lineage: `promotion_active`, `promotion_source`, `promotion_eligible`, `promotion_decision`, `promotion_decision_reason`
- Tenant lineage: `client_id`, `tenant_id`, `tenant_namespace`, `storage_namespace`
- State provenance: `state_source`, `state_source_detail`, `telemetry_classification`
- Fallback visibility: `source`, synthetic-fallback notes, degraded MLflow state, and empty-frame behaviors where dependencies are unavailable

## Enforcement Levels

| Level | Meaning | Current examples |
| --- | --- | --- |
| Code-enforced | The runtime explicitly rejects or routes around stale or missing inputs. | 15-minute Dagster snapshot freshness gate in the recommendation path, explicit synthetic fallbacks, empty canonical schedule when forecast inputs are missing. |
| Asset-check enforced | Dagster asset checks validate the contract after materialization. | `optimization_schedule_contract_checks` validates schedule lineage and rolling-horizon metadata. |
| Presentation target | The field exists and should be reviewed, but there is no hard runtime gate yet. | Many Bronze and Silver freshness fields, benchmark recency, model metadata availability. |

## Freshness And Lineage Matrix

| Dataset | Freshness anchor | Current operating target | Enforcement posture | Main lineage fields |
| --- | --- | --- | --- | --- |
| `market_data_asset` | `timestamp` | Latest successful `daily_data_refresh` cycle with most recent available market data or explicit synthetic fallback | Presentation target plus fallback behavior | `source` and Bronze ingest provenance |
| `weather_asset` | `timestamp` | Latest successful `daily_data_refresh` cycle with most recent available weather forecast or explicit synthetic fallback | Presentation target plus fallback behavior | `source` and Bronze ingest provenance |
| `client_state_asset` | `battery_state_updated_at` | Fresh within the active operational refresh cycle for the selected tenant, with degraded config-backed fallback made explicit | Presentation target with explicit source visibility | `client_id`, `tenant_id`, `tenant_namespace`, `storage_namespace`, `state_source`, `state_source_detail`, `telemetry_classification` |
| `feature_matrix_asset` | `timestamp` | Built from the most recent validated Bronze and Silver inputs in the active refresh cycle | Presentation target | upstream time anchors and engine selection metadata |
| `tenant_asset_factory` outputs | `analysis_timestamp` | Refreshed on the relevant tenant-analytics cycle or customer-config change | Presentation target | tenant namespace and asset-factory projection lineage |
| `price_forecast_asset` | `forecast_freshness_minutes` and `forecast_latency_ms` | Fresh forecast horizon from the latest successful forecast materialization used by recommendation and optimization flows | Presentation target with strong field-level observability | `forecast_run_id`, `forecast_model_version`, promotion metadata |
| `optimization_schedule_asset` | `forecast_freshness_minutes` plus schedule lineage checks | Fresh Gold schedule from the latest forecast used for active optimization review | Asset-check enforced for lineage and rolling metadata | `forecast_run_id`, `optimization_run_id`, `algorithm`, `solver`, rolling-window fields |
| `optimization_schedule_milp_asset` | `forecast_freshness_minutes` plus schedule lineage checks | Fresh alternative optimizer schedule aligned to the same forecast horizon as the baseline schedule | Asset-check enforced for lineage alignment | `forecast_run_id`, `optimization_run_id`, `algorithm`, `solver` |
| `forecast_value_benchmark_asset` | `benchmark_timestamp` | Latest successful benchmark run for forecast comparison and promotion review | Presentation target with explicit promotion fields | benchmark fields, promotion fields, model identity |
| `trained_model_asset` | `logged_at` | Latest successful model-training run when sufficient training data exists | Presentation target, may legitimately be empty | `model_id`, `run_id`, `artifact_uri` |
| `model_metadata_asset` | `fetched_at` | Latest successful MLflow metadata retrieval for available trained-model rows | Presentation target, may degrade to error rows | `model_id`, `status`, fetched metadata |
| `multi_client_analytics` | `analysis_timestamp` | Latest multi-tenant analytics materialization over current customer metadata | Presentation target | `client_id`, ranking fields, customer-derived metadata lineage |

## Concrete Freshness Gates Already In Code

### Dagster recommendation snapshot gate

Current location:
`dashboard/server/api/dagster/recommendation.ts`

Current threshold:
`MAX_SNAPSHOT_AGE_MINUTES = 15`

Operational meaning:

- The dashboard recommendation path only treats a Dagster snapshot as fresh when it is at most 15 minutes old.
- Older snapshots are treated as stale and trigger fallback recommendation behavior rather than silent reuse.
- This is the strongest currently documented cross-layer freshness gate in the dashboard-facing runtime.

### Optimization schedule contract checks

Current location:
`src/assets/core/optimization_schedule_checks.py`

Operational meaning:

- Baseline and MILP schedule assets are validated through Dagster-owned asset checks.
- The current check path verifies forecast lineage, rolling-window metadata consistency, and realized-value reconciliation surfaces.
- This is contract enforcement after materialization rather than an API-time freshness gate.

## Fallback And Degraded-Mode Rules

Freshness documentation is incomplete without degraded-mode visibility. The current runtime deliberately makes these cases explicit:

- Bronze ingest can fall back to synthetic market or synthetic weather data when external sources are unavailable.
- Client operational state can fall back to configuration defaults when live or simulator-backed telemetry is incomplete.
- Forecast outputs can fall back to baseline or persistence behavior when training data is insufficient.
- Optimization assets can return empty canonical schedules when forecast inputs are missing.
- MLflow-facing surfaces can remain available in degraded mode, including the dashboard status route returning success with a disconnected MLflow flag.
- `trained_model_asset` and `model_metadata_asset` can truthfully materialize as empty or error-bearing frames; those are valid outcomes, not documentation failures.

## Review Guidance

When presenting the supervisor package:

- Treat explicit run identifiers and promotion fields as the strongest evidence of end-to-end lineage.
- Treat the 15-minute Dagster recommendation gate as the main user-facing freshness guarantee already enforced in code.
- Treat asset checks as the strongest Gold-layer contract enforcement for optimization outputs.
- Treat Bronze and Silver freshness values as monitored operating targets unless and until additional hard gates are added.
- Keep fallback and degraded-mode behavior explicit in all presentations rather than describing the pipeline as if every dependency were always live.