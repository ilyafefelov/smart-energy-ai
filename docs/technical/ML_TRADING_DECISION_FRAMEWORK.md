# ML Trading Decision Framework

This note describes the current trading-decision stack as implemented today. It is intended to separate active runtime behavior from older prototype or training-only paths, and to use consistent provenance language for price, weather, battery, and action history.

## Overview

The current system is a hybrid prototype:

- real external market and weather inputs are used where available
- simulator-backed battery and control state is used as the operational dashboard state
- the live BUY/SELL/HOLD outcome is produced by schedule optimization and heuristic decision logic, not by a trained action model running end to end
- older supervised ML assets still exist, but they depend on synthetic history, synthetic labels, placeholder profits, or mock-serving behavior and are not the current production decision path

The most important terminology rule is to avoid collapsing everything into "real" versus "synthetic". The repo currently uses four materially different data categories.

## Current User-Facing Decision Trace

The current user-facing path works in this order:

1. Dashboard auto mode asks `/api/dagster/recommendation` for the freshest schedule-backed recommendation.
2. Dagster builds that recommendation from market and weather inputs, a synthesized client state, a real price-forecast model, and schedule optimization.
3. Schedule output is normalized into BUY, SELL, or HOLD for dashboard use.
4. If the Dagster snapshot is stale, invalid, or unavailable, the dashboard falls back to `/api/ml/recommendation`.
5. `/api/ml/recommendation` uses live tenant config, current prices, current battery status, and weather context, then calls the Python bridge in `scripts/ml_integration_api.py`.
6. The Python path applies rule-based decision logic, heuristic optimization, renewable inference, and a live-price override.
7. When an operator executes a control command, the resulting battery-state effect is written back into persisted tenant battery state and becomes part of the next dashboard-control inference loop.

In short, the live recommendation story is forecast plus optimization plus heuristics around simulator-backed operational battery state. It is not a trained end-to-end trading policy.

## Data Provenance Model

### 1. Real external live data

These are live or near-live signals pulled from external systems during runtime:

- market prices from the dashboard price APIs and OREE-backed market data flows
- weather from Open-Meteo in the dashboard and Dagster weather path
- tenant configuration and control context stored by the application

### 2. Real external historical backfill

These are historically sourced datasets that can be imported or scraped from external providers with documented provenance:

- historical market price series
- historical weather series

This category is appropriate for building the market and weather side of training or evaluation datasets over the last two years, assuming source provenance is tracked.

### 3. Simulated operational telemetry

This is the current operational battery and control state used by the dashboard loop:

- per-tenant battery state persisted under the tenant data directory
- simulator-driven battery updates exposed by the battery APIs
- control-status fallbacks derived from persisted battery state and command history
- command execution that writes battery effects back into the same persisted loop

This data is operationally live inside the application, but it is still simulated telemetry. It should not be described as real plant or IoT telemetry.

### 4. Fabricated training scaffolding

This is the older prototype ML material that should be labeled explicitly when referenced:

- synthetic historical rows generated from current features plus noise and handcrafted patterns
- synthetic labels derived from thresholds instead of observed actions or realized outcomes
- placeholder expected profits and random confidence values in legacy recommendation paths
- mock MLflow behavior when no real model URI is supplied

This category is useful for experiments, but it should not be presented as evidence of production-grade training data.

## Historical Data Strategy

The current repo supports a stronger history story for external exogenous data than for operational battery behavior.

### Price and weather history

Price and weather history can be sourced or scraped for the last two years from external providers. When provenance is documented, that should be treated as real external historical backfill, not synthetic data.

### Battery, action, and outcome history

Battery state, executed actions, and realized outcomes cannot be honestly backfilled in the same way unless they were actually recorded from a running simulator loop or a real plant.

That means the history terminology should be:

- pre-test battery and action history: bootstrap or fabricated history
- post-start simulator recordings: operational simulator history
- real plant telemetry, if added later: real operational history

Simulator recordings are more credible than fabricated training rows because they come from the running control loop, but they still are not physical telemetry.

## Active Runtime Paths

### Dashboard battery and control telemetry loop

The dashboard already maintains a tenant-scoped operational state loop:

- `dashboard/server/utils/battery.ts` persists tenant battery state
- `dashboard/server/api/battery/status.ts` returns current battery state
- `dashboard/server/api/battery/simulate.ts` advances that state with tenant-aware simulation inputs
- `dashboard/server/api/control/status.get.ts` derives fallback control state from persisted battery and command history
- `dashboard/server/api/control/execute.post.ts` writes command effects back into battery state

This is the closest thing to the current operational telemetry source, and it is richer than the separate Stage 1 synthetic client-state asset used in Dagster.

### Dagster operational path

The active Dagster chain is documented in `src/definitions.py` and summarized in `DAGSTER_PIPELINE_DEPENDENCY_MAP.md`:

- `market_data_asset` ingests market prices, with local fallback behavior when upstream data is unavailable
- `weather_asset` ingests weather data and derived solar-relevant features
- `client_state_asset` synthesizes per-client battery, load, and solar state from configs plus market and weather inputs
- `price_forecast_asset` trains a `RandomForestRegressor` on market history and emits a forecast horizon
- `optimization_schedule_asset` and `optimization_schedule_milp_asset` compute schedule decisions over that forecast horizon
- `scripts/read_dagster_schedule.py` normalizes schedule power output into BUY, SELL, or HOLD for dashboard consumption

This is a real forecast-plus-optimizer path, but it still depends on a synthesized client state rather than the richer simulator-backed tenant loop already present in the dashboard.

### Dashboard ML fallback path

When Dagster output is unavailable or stale, the dashboard falls back to `dashboard/server/api/ml/recommendation.get.ts`:

- the endpoint gathers tenant config, live prices, battery state, and weather context
- it shells into `scripts/ml_integration_api.py` using the live context payload
- `energy_ml/pipeline.py` uses rule-based decision logic in `_make_decision`
- `energy_ml/mlops/optimization_engine.py` re-scores the action with static strategy weights and heuristic scores
- renewable and battery-physics helpers modify the result further
- a final live-price signal can override the action again

This path is valuable as a runtime fallback, but it is still heuristically composed logic rather than a trained action model.

## Legacy or Experimental Paths

Older supervised ML assets remain in the repository, especially under `energy_ml/energy_ml/assets` and the MLflow-facing integration surfaces. They are not the current end-to-end live decision engine.

The core reasons are:

- legacy training fabricates multi-year history from current rows plus noise and handcrafted patterns
- training labels are synthesized from thresholds instead of observed actions and realized outcomes
- some recommendation outputs use placeholder profit calculations or random confidence values
- `PredictionService` in `energy_ml/ml_integration.py` defaults to mock mode unless a real MLflow model URI is supplied

These assets can still be useful for experimentation or future cleanup, but they should be framed as prototype or legacy scope rather than the active production decision path.

## MLflow Dashboard Surfaces

The dashboard MLflow routes are diagnostic surfaces, not runtime-serving authority:

- `/api/mlflow/status` reports experiment and registry reachability plus recent run metadata when available.
- `/api/mlflow/log-metrics` captures local runtime diagnostics for operator visibility; it should not be described as guaranteed MLflow tracking unless a real backend logging path is wired.
- Live recommendation provenance should come from the serving contract and Dagster snapshot metadata first.

If learned-policy mode is activated with an explicit model URI, the authoritative runtime serving metadata lives in the Python `PredictionService` contract. MLflow remains a supporting registry or experiment surface rather than the public source of truth for action selection.

## Current Gaps And Terminology Fixes

The current architecture is serviceable, but the docs need to describe it more honestly.

The main gaps are:

- the live BUY, SELL, or HOLD result is not produced by a trained trading model
- the best current battery signal is simulator-backed application state, not real IoT telemetry
- Dagster still fabricates a weaker `client_state_asset` instead of consuming the richer simulator-backed tenant loop
- the legacy supervised ML stack overstates realism because both history and labels are synthetic
- some older architecture narratives still imply a more ML-driven and more real-telemetry-driven system than the code currently supports

The key terminology fix is:

- call market and weather backfill real external historical data when provenance is known
- call persisted dashboard battery state simulated operational telemetry
- call synthetic prebuilt ML rows fabricated training scaffolding

That wording is defensible and keeps planning discussions honest.

## Recommended Follow-up Direction

The cleanest next architectural direction is:

1. keep simulator-backed battery and control state as the current-stage operational source of truth
2. align Dagster state inputs with that simulator-backed loop where practical
3. document the live recommendation story as forecast plus optimization plus heuristics, not as a trained action model
4. quarantine legacy synthetic ML assets from the main production narrative until they train on credible state, action, and outcome history
5. if a learned action model is still a goal, combine backfilled market and weather history with forward-collected simulator battery, action, and outcome history rather than inventing retrospective battery labels

This yields the most accurate summary of the current system: real external market and weather signals, simulator-backed operational battery state, a real market forecast model, and heuristic or schedule-driven action selection.

## Related References

- `docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md`
- `docs/technical/ARCHITECTURE_V2.md`
- `dashboard/server/api/ml/recommendation.get.ts`
- `dashboard/server/utils/battery.ts`
- `src/assets/core/client_state.py`
- `src/assets/core/price_forecast.py`
- `src/assets/core/optimization_schedule.py`