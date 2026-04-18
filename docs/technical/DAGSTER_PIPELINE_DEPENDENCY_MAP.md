# Dagster Pipeline Dependency Map

This document describes the current Dagster ML pipeline as it exists in `src/definitions.py`, with explicit asset dependencies, job boundaries, and runtime responsibilities.

## Pipeline Shape

The active pipeline is a linear core with two optimization branches and two side paths:

- Ingestion: `market_data_asset` and `weather_asset`
- State synthesis: `client_state_asset`
- Feature building: `feature_matrix_asset`
- Forecasting: `price_forecast_asset`
- Scheduling: `optimization_schedule_asset` and `optimization_schedule_milp_asset`
- Validation: schedule contract checks for both schedule assets
- Side paths: benchmark assets and dynamic tenant assets from the asset factory

## Asset Dependency Walkthrough

### Core operational chain

1. `market_data_asset`
   Pulls OREE market prices and falls back to synthetic hourly price series when upstream data is unavailable.
2. `weather_asset`
   Pulls Open-Meteo weather forecasts and derives solar-relevant weather features, with synthetic fallback for local runs.
3. `client_state_asset`
   Uses weather, market data, and `customers.yaml` to synthesize per-client battery state, solar generation, load, and tenant metadata.
4. `feature_matrix_asset`
   Joins market, weather, and client state into an ML-ready feature table using the selected feature engine.
5. `price_forecast_asset`
   Trains a baseline 24-hour day-ahead price forecaster from market history and emits a 24-hour prediction horizon.
6. `optimization_schedule_asset`
   Runs the baseline DP optimizer for each client using forecast prices plus the latest client load and solar series.
7. `optimization_schedule_milp_asset`
   Runs the MILP scheduler over the same forecast horizon and client state.
8. `optimization_schedule_contract_checks`
   Evaluates row completeness, numeric field validity, and action-balance semantics for both schedule outputs.

### Side paths

- `engine_benchmark_asset`, `accuracy_benchmark_asset`, `mlflow_tracking_asset`
  Support benchmarking and experiment tracking rather than the live recommendation path.
- `create_all_assets()` generated tenant assets
  Project shared market and weather inputs into isolated per-tenant asset namespaces.
- `multi_client_analytics`
  Aggregates customer configuration into fleet-level comparison metrics.

## Job Boundaries

### `daily_data_refresh`

Materializes the full operational chain:

- `market_data_asset`
- `weather_asset`
- `client_state_asset`
- `feature_matrix_asset`
- `price_forecast_asset`
- `optimization_schedule_asset`
- `optimization_schedule_milp_asset`
- all optimization schedule contract checks

This is the closest thing to the end-to-end daily recommendation job.

### `optimization_schedule_contract_checks`

Materializes the optimization schedule assets together with all required upstream dependencies and then runs the asset checks. This job is designed to work on a fresh persistent Dagster instance and is the right contract-validation entry point for runtime verification.

### `benchmark_engines`

Runs only the benchmark/MLflow branch. It is operationally separate from the recommendation path.

### `multi_tenant_analytics`

Runs only the aggregated multi-tenant analytics asset.

## Mermaid View

```mermaid
flowchart TD
    subgraph DailyJob[daily_data_refresh]
        M[market_data_asset]
        W[weather_asset]
        C[client_state_asset]
        F[feature_matrix_asset]
        P[price_forecast_asset]
        O1[optimization_schedule_asset\nBaseline DP]
        O2[optimization_schedule_milp_asset\nMILP]
        CK1[schedule checks\nBaseline]
        CK2[schedule checks\nMILP]
    end

    M --> C
    W --> C
    M --> F
    W --> F
    C --> F
    M --> P
    C --> O1
    P --> O1
    C --> O2
    P --> O2
    O1 --> CK1
    O2 --> CK2

    subgraph ContractsJob[optimization_schedule_contract_checks]
        CJ[Re-materialize upstream + schedules + checks]
    end

    M -. included upstream .-> CJ
    W -. included upstream .-> CJ
    C -. included upstream .-> CJ
    P -. included upstream .-> CJ
    O1 -. checked .-> CJ
    O2 -. checked .-> CJ
    CK1 -. results .-> CJ
    CK2 -. results .-> CJ

    subgraph BenchmarkJob[benchmark_engines]
        B1[engine_benchmark_asset]
        B2[accuracy_benchmark_asset]
        B3[mlflow_tracking_asset]
    end

    subgraph MultiTenantJob[multi_tenant_analytics]
        A1[dynamic tenant assets\nfrom create_all_assets()]
        A2[multi_client_analytics]
    end

    M --> A1
    W --> A1
    M --> B1
    W --> B1
```

## Operational Interpretation

- Live recommendations are driven by the market -> weather -> client state -> forecast -> schedule chain.
- The baseline and MILP assets are parallel schedule producers over the same forecast horizon.
- Asset checks are first-class runtime gates, not external scripts.
- Benchmark and multi-tenant analytics jobs are intentionally outside the core daily recommendation job so they do not slow or destabilize operational runs.

## Logical Medallion Overlay

For supervisor-facing documentation, the current runtime can also be read as a logical Bronze/Silver/Gold architecture without changing the physical runtime topology.

- Bronze: `market_data_asset`, `weather_asset`, and the source-facing `data/raw/` surface.
- Silver: `client_state_asset`, `feature_matrix_asset`, and the validated intermediate `data/processed/` surface.
- Gold: `price_forecast_asset`, both optimization schedule assets, schedule asset checks, benchmark/MLflow/model assets, `multi_client_analytics`, and the presentation-facing `data/results/` plus `artifacts/medallion/` surfaces.

This framing is a presentation overlay only. It does not imply that the repository already uses a physical medallion warehouse layout, and it does not replace the active runtime rooted at `src/definitions.py`.

See [DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md](DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md) for the supervisor-facing narrative, [BRONZE_SILVER_GOLD_DATASET_CATALOG.md](BRONZE_SILVER_GOLD_DATASET_CATALOG.md) for the generated dataset catalog, [EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md) for benchmark and optimizer evidence, and [../../artifacts/medallion/medallion_dataset_manifest.yaml](../../artifacts/medallion/medallion_dataset_manifest.yaml) for the machine-readable catalog foundation.