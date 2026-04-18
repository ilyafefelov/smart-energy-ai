# Dataset Model Reference

This document is the supervisor-facing dataset-model reference for the current Dagster runtime rooted at `src/definitions.py`.

It describes the existing system as a logical Bronze, Silver, and Gold presentation overlay. It does not claim a separate physical medallion warehouse, and it keeps the current mix of explicit schema contracts and implicit runtime contracts visible instead of flattening those differences.

## How To Read This Reference

- `Grain` describes the row-level business key or logical row scope.
- `Representative fields` lists the most important fields that are visible from current asset code or explicit schema constants.
- `Schema posture` distinguishes between explicitly centralized contracts and outputs that are still implicit in the asset implementation.
- `Fallback and provenance` makes current local and degraded-mode behavior explicit.

## Shared Contract Families

Common fields and field families that recur across the current runtime:

- Time anchors: `timestamp`, `forecast_timestamp`, `benchmark_timestamp`, `analysis_timestamp`
- Tenant and client identity: `client_id`, `tenant_id`, `tenant_namespace`, `storage_namespace`
- Operational provenance: `source`, `state_source`, `state_source_detail`, `telemetry_classification`
- Forecast lineage: `forecast_run_id`, `forecast_model_name`, `forecast_model_family`, `forecast_model_version`
- Optimization lineage: `optimization_run_id`, `algorithm`, `solver`
- MLflow lineage: `model_id`, `run_id`, `artifact_uri`
- Freshness anchors: `forecast_freshness_minutes`, `forecast_latency_ms`, `battery_state_updated_at`

## Layer Summary

| Layer | Primary role | Current storage surface | Typical consumer |
| --- | --- | --- | --- |
| Bronze | Source-facing ingest with explicit fallback behavior | `data/raw` | Validation, feature engineering, and ingest observability |
| Silver | Validated and enriched operational state | `data/processed` | Forecasting, optimization, and tenant projections |
| Gold | Decision-support, benchmark, model, and fleet outputs | `data/results` | Dashboard reporting, optimizer consumers, benchmark review, and supervisor evidence |

## Bronze Datasets

### `market_data_asset`

- Owner: `src/assets/core/market.py::market_data_asset`
- Grain: hourly price observation keyed by `timestamp`
- Representative fields: `timestamp`, `price_eur_mwh`, `price_uah_mwh`, `volume_mwh`, `source`
- Fallback and provenance: real OREE market data with explicit synthetic fallback when the external source is unavailable
- Downstream consumers: `price_forecast_asset`, optimization assets, benchmark scorecard flows, dashboard price surfaces
- Schema posture: mostly stable in practice, but documented through the asset and validator behavior rather than a standalone shared schema constant

### `weather_asset`

- Owner: `src/assets/core/weather.py::weather_asset`
- Grain: hourly weather observation keyed by `timestamp`
- Representative fields: `timestamp`, `temperature`, `solar_radiation`, `wind_speed`, `cloudcover`, `precipitation`, `pressure`, `humidity`, `source`
- Fallback and provenance: Open-Meteo forecast data with explicit synthetic-weather fallback for local and degraded operation
- Downstream consumers: `client_state_asset`, `feature_matrix_asset`, solar-aware optimization inputs, renewable forecast surfaces
- Schema posture: stable enough for downstream use, but the contract remains implicit in the asset and validation helpers rather than centralized in a shared schema definition

## Silver Datasets

### `client_state_asset`

- Owner: `src/assets/core/client_state.py::client_state_asset`
- Grain: hourly client state keyed by `timestamp` and `client_id`
- Representative fields: `timestamp`, `client_id`, `tenant_id`, `tenant_namespace`, `storage_namespace`, `battery_soc`, `battery_health`, `battery_cycles`, `battery_temp`, `battery_voltage`, `battery_current`, `solar_gen_actual`, `load_actual`, `grid_power`, `battery_power`, `inverter_status`, `system_efficiency`, `state_source`, `state_source_detail`, `battery_state_updated_at`, `telemetry_classification`
- Fallback and provenance: simulator-backed tenant battery state when available, with config-driven defaults and deterministic derived load and solar when live telemetry is incomplete
- Downstream consumers: `feature_matrix_asset`, both optimization schedule assets, dashboard battery and control views
- Schema posture: important and fairly stable, but still described through asset behavior and validator logic rather than a shared schema constant

### `feature_matrix_asset`

- Owner: `src/assets/core/feature_matrix.py::feature_matrix_asset`
- Grain: hourly feature row keyed by `timestamp` and `client_id`
- Representative fields: `timestamp`, `price_eur_mwh`, weather features such as `temperature`, `solar_radiation`, `cloudcover`, `humidity`, client-state features such as `battery_soc`, `solar_gen_actual`, `load_actual`, derived features such as `price_lag_1h`, `price_24h_avg`, `net_load`, plus `feature_engine` and `engine_fallback_reason`
- Fallback and provenance: derived from validated market, weather, and client-state surfaces; engine selection can fall back to the local Polars builder when a selected engine lacks the required interface
- Downstream consumers: `price_forecast_asset`, benchmark surfaces, feature-quality analysis
- Schema posture: partially dynamic because the feature set can vary with engine selection; document the representative families, not a frozen column list

### `tenant_asset_factory` dynamic projections

- Owner: `src/assets/multi_tenant/asset_factory.py::create_all_assets`
- Grain: tenant-projected operational rows derived from shared upstream assets and customer configuration
- Representative fields: `tenant_id`, `tenant_namespace`, `storage_namespace`, customer-specific configuration values, and tenant-projected operational joins over shared market and weather surfaces
- Fallback and provenance: driven by customer configuration and shared validated upstream assets
- Downstream consumers: `multi_client_analytics`, tenant-aware dashboard slices, fleet-level comparison views
- Schema posture: dynamic by design because the asset factory projects multiple tenant-specific assets rather than one fixed static table

## Gold Datasets

### `price_forecast_asset`

- Owner: `src/assets/core/price_forecast.py::price_forecast_asset`
- Grain: hourly forecast row keyed by `forecast_timestamp`
- Representative fields: `forecast_timestamp`, `predicted_price_eur_mwh`, scenario bounds such as `scenario_low_price_eur_mwh`, `scenario_base_price_eur_mwh`, `scenario_high_price_eur_mwh`, quantiles such as `quantile_p10_eur_mwh` through `quantile_p90_eur_mwh`, `model_name`, `model_family`, `eval_rmse`, `eval_mae`, `eval_value_capture_ratio`, `forecast_run_id`, `forecast_model_version`, `trained_at_utc`, `evaluation_folds`, `training_rows`, `promotion_active`, `promotion_source`
- Fallback and provenance: model-derived forecast with persistence or baseline behavior when training data is insufficient, plus promotion metadata when a candidate is selected as active
- Downstream consumers: both optimization schedule assets, benchmark scorecard, dashboard forecast views, recommendation surfaces
- Schema posture: contract is important but still implicit in the asset implementation; uncertainty columns and promotion metadata are especially important for documentation because they drive downstream reasoning and promotion logic

### `optimization_schedule_asset`

- Owner: `src/assets/core/optimization_schedule.py::optimization_schedule_asset`
- Grain: schedule row keyed by `client_id` and `hour` within the active forecast horizon
- Representative fields: `client_id`, `hour`, `action_kw`, `charge_kwh`, `discharge_kwh`, `soc_before_kwh`, `soc_after_kwh`, `throughput_total_kwh`, `price_eur_mwh`, `load_kwh`, `solar_kwh`, `grid_import_kwh`, `grid_export_kwh`, `purchase_cost_eur`, `export_revenue_eur`, `degradation_penalty_eur`, `net_cost_eur`, `forecast_run_id`, `optimization_run_id`, `forecast_model_version`, `rolling_horizon_enabled`, `rolling_window_index`, `rolling_window_start_hour`, `rolling_window_end_hour`, `rolling_window_horizon_hours`, `rolling_window_commit_hours`, `algorithm`, `solver`
- Fallback and provenance: forecast-driven baseline dynamic-programming schedule; returns an empty canonical schedule when forecast inputs are missing or unusable
- Downstream consumers: dashboard schedule views, optimization-history reconciliation, realized-value comparison, supervisor evidence pack
- Schema posture: explicit shared contract via `OPTIMIZATION_SCHEDULE_SCHEMA`

### `optimization_schedule_milp_asset`

- Owner: `src/assets/core/optimization_schedule_milp.py::optimization_schedule_milp_asset`
- Grain: schedule row keyed by `client_id` and `hour` within the same forecast horizon as the baseline schedule
- Representative fields: same shared schedule contract as `optimization_schedule_asset`, including economics, lineage, and rolling-metadata columns
- Fallback and provenance: MILP or LP-backed optimizer alternative over the same forecast horizon, including solver metadata and explicit contract alignment with the baseline schedule surface
- Downstream consumers: optimizer-vs-optimizer comparison, realized-value reconciliation, supervisor experiment comparisons
- Schema posture: explicit shared contract aligned to `OPTIMIZATION_SCHEDULE_SCHEMA`

### `forecast_value_benchmark_asset`

- Owner: `src/assets/benchmarks/performance.py::forecast_value_benchmark_asset`
- Grain: benchmark row keyed by `model_name` and `benchmark_timestamp`
- Representative fields: `model_name`, `model_family`, `forecast_horizon_hours`, `forecast_rows`, `training_rows`, `evaluation_folds`, `eval_rmse`, `eval_mae`, `eval_value_capture_ratio`, `benchmark_rmse`, `benchmark_mae`, `benchmark_value_capture_ratio`, `benchmark_conservative_value_capture_ratio`, `benchmark_realized_spread_eur_mwh`, `benchmark_optimal_spread_eur_mwh`, `benchmark_uncertainty_source`, `promotion_eligible`, `promotion_decision`, `promotion_decision_reason`, `benchmark_candidate_rank`, `benchmark_incumbent_baseline`, `benchmark_timestamp`
- Fallback and provenance: benchmark-derived scorecard driven by realized market data, forecast output, and promotion logic
- Downstream consumers: supervisor scorecard, model promotion review, MLflow logging, benchmark documentation
- Schema posture: explicit shared contract via `FORECAST_VALUE_SCORECARD_SCHEMA`

### `trained_model_asset`

- Owner: `src/assets/benchmarks/model_training.py::trained_model_asset`
- Grain: one row per trained model produced in the current run
- Representative fields: `model_id`, `model_name`, `model_family`, `model_version`, `params`, `run_id`, `artifact_uri`, `logged_at`, `rmse`, `mae`, `r2`
- Fallback and provenance: MLflow-backed training output; may legitimately materialize as an empty frame when training data is insufficient
- Downstream consumers: `model_metadata_asset`, supervisor evidence pack, future registry and promotion review surfaces
- Schema posture: explicit in the asset's returned DataFrame shape, though not factored into a separate shared schema module

### `model_metadata_asset`

- Owner: `src/assets/benchmarks/model_training.py::model_metadata_asset`
- Grain: one row per queried trained model record
- Representative fields: `model_id`, `model_name`, `params`, `metrics`, `fetched_at`, `status`
- Fallback and provenance: MLflow metadata lookup over the trained-model surface; error rows remain part of the honest contract when metadata fetch fails
- Downstream consumers: supervisor evidence pack, model introspection, future model retrieval surfaces
- Schema posture: explicit in the asset's returned DataFrame shape, but still closely coupled to MLflow query behavior

### `multi_client_analytics`

- Owner: `src/assets/multi_tenant/asset_factory.py::multi_client_analytics`
- Grain: one row per client
- Representative fields: `client_id`, `client_name`, `client_type`, `battery_capacity_kwh`, `solar_capacity_kw`, `peak_load_kw`, `storage_hours`, `solar_coverage_ratio`, `electricity_tariff`, `feed_in_tariff`, `location_lat`, `location_lon`, `storage_rank`, `solar_rank`, `tariff_rank`, `storage_class`, `solar_class`, `analysis_timestamp`
- Fallback and provenance: metadata-driven fleet analytics derived from `customers.yaml`, not from live telemetry
- Downstream consumers: fleet summary, supervisor case-study packaging, comparative dashboard views
- Schema posture: stable in practice, but generated from tenant metadata and ranking logic rather than a centralized schema constant

## Multi-Tenant Model Notes

The current multi-tenant model is part of the runtime, not a future architecture sketch. The important dataset-model rules are:

- `tenant_id` identifies the active tenant context used for dashboard and API resolution.
- `client_id` remains the key operational identity used in optimization and many analytic surfaces.
- `tenant_namespace` and `storage_namespace` are the main isolation anchors for tenant-projected assets and derived storage surfaces.
- The dynamic asset factory projects tenant-specific assets from shared upstream validated data rather than duplicating Bronze ingest per tenant.
- `multi_client_analytics` is the fleet summary surface and should be read as a Gold reporting layer over customer metadata and derived rankings, not as a raw telemetry table.

## Contract Caveats

- `optimization_schedule_asset`, `optimization_schedule_milp_asset`, and `forecast_value_benchmark_asset` have the strongest explicit schema posture today.
- `trained_model_asset` and `model_metadata_asset` have explicit returned-frame shapes, but their materialization can legitimately be empty or degraded when training or MLflow prerequisites are missing.
- `feature_matrix_asset`, `price_forecast_asset`, and parts of the tenant-projection surface still rely on implicit contracts documented by behavior and tests rather than a dedicated shared schema module.
- Supervisor-facing documentation should preserve those differences instead of overstating current schema formalization.