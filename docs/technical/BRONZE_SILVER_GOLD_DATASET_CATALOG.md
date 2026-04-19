# Bronze/Silver/Gold Dataset Catalog

Generated from the medallion manifest and current local runtime surfaces at 2026-04-19T12:07:48+00:00.

This catalog is rendered from the canonical manifest, current folder state, and the latest Dagster materializations when they are available locally.

## Layer Summary

| Layer | Datasets | Materialized | Storage Present | Files | Size | Latest Observed Update |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Bronze | 2 | 2 | 2 | 2 | 20.4 KB | 2026-04-24T23:00:00+00:00 |
| Silver | 3 | 2 | 3 | 21 | 21.4 KB | 2026-04-20T23:00:00+00:00 |
| Gold | 8 | 8 | 7 | 148 | 92.3 MB | 2026-04-20T23:00:00+00:00 |

## Bronze

Source-facing ingest and raw retention with explicit fallback handling.

| Dataset | Dagster Asset | Source Kind | Fallback Mode | Freshness Field | Quality Owner | Storage Path | Runtime Snapshot |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OREE market price ingest | market_data_asset | real_with_synthetic_fallback | synthetic_market_on_source_failure | timestamp | src/data_pipeline/market_validation.py::_validate_market_data | data/raw/oree_historical_prices.parquet | storage=present (1 files, 18.0 KB); asset_rows=48; latest_row=2026-04-19T23:00:00+00:00 |
| Open-Meteo weather forecast ingest | weather_asset | real_with_synthetic_fallback | synthetic_weather_on_source_failure | timestamp | src/data_pipeline/weather_validation.py::_validate_weather_data | data/raw/weather_forecast.csv | storage=present (1 files, 2.4 KB); asset_rows=168; latest_row=2026-04-24T23:00:00+00:00 |

## Silver

Validated, normalized, and enriched operational data used by tenant and ML flows.

| Dataset | Dagster Asset | Source Kind | Fallback Mode | Freshness Field | Quality Owner | Storage Path | Runtime Snapshot |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Client operational state | client_state_asset | simulator_backed_with_config_fallback | config_default_state | battery_state_updated_at | src/data_pipeline/client_state_validation.py::_validate_client_data | data/processed | storage=present (7 files, 7.1 KB); asset_rows=240; latest_row=2026-04-19T23:00:00+00:00 |
| Forecast and optimization feature matrix | feature_matrix_asset | validated_enriched | upstream_dependent | timestamp | src/data_pipeline/feature_matrix_builder.py | data/processed | storage=present (7 files, 7.1 KB); asset_rows=240; latest_row=2026-04-20T23:00:00+00:00 |
| Dynamic tenant projections | create_all_assets | tenant_projected | customer_config_dependent | analysis_timestamp | src/assets/multi_tenant/asset_factory.py | data/processed | storage=present (7 files, 7.1 KB); asset_status=not_applicable |

## Gold

Business-facing forecasting, optimization, benchmark, model, and fleet analytics outputs.

| Dataset | Dagster Asset | Source Kind | Fallback Mode | Freshness Field | Quality Owner | Storage Path | Runtime Snapshot |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gold price forecast horizon | price_forecast_asset | ml_forecast_output | baseline_model_and_runtime_selection_controls | forecast_freshness_minutes | src/assets/core/price_forecast.py | data/results | storage=present (4 files, 7.5 KB); asset_rows=24; latest_row=2026-04-20T23:00:00+00:00 |
| Baseline optimization schedule | optimization_schedule_asset | optimization_output | empty_schedule_when_forecast_missing | forecast_freshness_minutes | src/assets/core/optimization_schedule_checks.py | data/results/optimization_results.csv | storage=missing (0 files, 0 B); asset_rows=120 |
| MILP optimization schedule | optimization_schedule_milp_asset | optimizer_alternative_output | solver_fallback_behavior | forecast_freshness_minutes | src/assets/core/optimization_schedule_checks.py | data/results | storage=present (4 files, 7.5 KB); asset_rows=120 |
| Forecast benchmark scorecard | forecast_value_benchmark_asset | benchmark_derived | optional_candidates_may_be_skipped_when_dependencies_missing | benchmark_timestamp | src/assets/benchmarks/performance.py | data/results/arbitrage_ranges.json | storage=present (1 files, 2.7 KB); asset_rows=1; latest_row=2026-04-19T06:01:03+00:00 |
| MLflow experiment tracking export | mlflow_tracking_asset | experiment_tracking | local_mlflow_optional | fetched_at | src/assets/benchmarks/performance.py | data/results | storage=present (4 files, 7.5 KB); asset_rows=8; latest_row=2026-04-19T06:01:03+00:00 |
| Trained forecast model artifact | trained_model_asset | model_artifact | empty_frame_when_training_data_is_insufficient | logged_at | src/assets/benchmarks/model_training.py | models | storage=present (67 files, 46.2 MB); asset_rows=0 |
| Logged model metadata lookup | model_metadata_asset | model_metadata | status_error_on_lookup_failure | fetched_at | src/assets/benchmarks/model_training.py | models | storage=present (67 files, 46.2 MB); asset_rows=0 |
| Fleet analytics summary | multi_client_analytics | fleet_analytics | empty_frame_when_no_customer_configs | analysis_timestamp | src/assets/multi_tenant/asset_factory.py | customers.yaml | storage=present (1 files, 2.6 KB); asset_rows=5; latest_row=2026-04-17T23:21:03+00:00 |

## Fleet View

- Source surface: multi_client_analytics
- Status: materialized_asset
- Client count: 5
- Top storage client: client_001_kyiv_mall (simulated)
- Top solar client: client_001_kyiv_mall (simulated)

## Case Study View

Selected tenant: `client_001_kyiv_mall` (Kyiv Shopping Mall) via `manifest_default_first_customer`.

| Metric | Value | Provenance | Surface |
| --- | ---: | --- | --- |
| battery_capacity_kwh | 280.000 | simulated | customers.yaml |
| solar_capacity_kw | 150.000 | simulated | customers.yaml |
| peak_load_kw | 200.000 | simulated | customers.yaml |
| storage_hours | 1.400 | simulated | multi_client_analytics |
| solar_coverage_ratio | 0.750 | simulated | multi_client_analytics |
| market_input_mode | fallback-derived | fallback-derived | market_data_asset |
| weather_input_mode | real | real | weather_asset |
| client_state_mode | simulated | simulated | client_state_asset |

## Limitations

- This catalog is a logical overlay on the current Dagster runtime, not a physical medallion warehouse rewrite.
- Storage paths are presentation anchors; actual Dagster materialization can still route through the configured IO manager.
- Missing Dagster materializations are rendered honestly as absent local evidence rather than backfilled with invented numbers.
