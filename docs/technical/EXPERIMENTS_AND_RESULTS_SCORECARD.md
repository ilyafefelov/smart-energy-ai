# Experiments And Results Scorecard

Generated from current runtime evidence at 2026-04-18T21:57:13+00:00.

This scorecard reuses existing Dagster benchmark, MLflow, optimization lineage, reconciliation, and fleet-analytics surfaces instead of creating a second observability plane.

## Model-vs-Model

- System of record: `forecast_value_benchmark_asset`
- Status: `materialized`
- Provenance: `benchmarked`
- Candidate rows: `1` total, `0` evaluated, `1` skipped.
- MLflow tracking surface: `materialized` with `8` logged runs and latest timestamp `2026-04-19T00:52:57+00:00`.

| Model | Family | Candidate Status | RMSE | MAE | Value Capture | Conservative Value Capture | Promotion | Reason |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| nbeatsx_dam_24h | nbeatsx_neuralforecast | skipped | n/a | n/a | n/a | n/a | skipped | The 'nbeatsx_dam_24h' forecast candidate requires the optional 'neuralforecast' dependency. Install it before selecting this model. |

### MLflow Support

| Run | Experiment | Model | RMSE | MAE | Value Capture | Promotion |
| --- | --- | --- | ---: | ---: | ---: | --- |
| forecast_value_nbeatsx_dam_24h | forecast_value_benchmarks | nbeatsx_dam_24h | n/a | n/a | n/a | skipped |

## Run-vs-Run

- Forecast status: `materialized` with 24 rows and latest timestamp `2026-04-20T23:00:00+00:00`.
- Baseline schedule status: `materialized` with forecast runs ['forecast-bcfa3fbe846fa963'].
- MILP schedule status: `materialized` with forecast runs ['forecast-bcfa3fbe846fa963'].
- Trained model surface: `materialized_empty` with `0` rows and latest logged-at `n/a`.
- Model metadata surface: `materialized_empty` with `0` rows and latest fetched-at `n/a`.

## Optimizer-vs-Optimizer

- Comparison status: `comparable`
- Provenance: `fallback-derived`

| Optimizer | Clients | Rows | Purchase Cost EUR | Export Revenue EUR | Degradation Penalty EUR | Net Cost EUR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline DP | 5 | 120 | 819.73 | 0.00 | 1.36 | 821.09 |
| MILP | 5 | 120 | 819.77 | 0.00 | 0.64 | 820.40 |

Net-cost delta (MILP - Baseline): `-0.68` EUR.

## Business Metrics

- PPO validation status: `available` with daily savings `7902.38` and improvement `57.90`%.
- Arbitrage range status: `available` with median daily spread `258.74` EUR.
- Reconciliation status source: `optimization_schedule_contract_checks` (dagster_asset_check_surface).

## Fleet View

- Source surface: `multi_client_analytics`
- Status: `materialized_asset`
- Client count: `5`
- Top storage client: `client_001_kyiv_mall` tagged `simulated`.
- Top solar client: `client_001_kyiv_mall` tagged `simulated`.

## Case Study View

Selected tenant `client_001_kyiv_mall` (Kyiv Shopping Mall) using `explicit_cli_selection`.

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

## Limitations And Deferrals

- This scorecard packages current runtime evidence; it does not claim a production warehouse or a completed backend re-root.
- Synthetic market or weather fallback can legitimately affect Gold outputs during local runs, and that provenance is surfaced instead of hidden.
- MLflow-backed and benchmark-backed evidence can be absent locally if those Dagster jobs have not been materialized in the current environment.
