# Codebase Implementation Roadmap

This roadmap turns the current Stage 2 literature work into a phased implementation plan for the active Smart Energy AI codebase.

It belongs in `docs/Stage 2/` because this repository already treats that folder as the canonical workspace for MVP literature planning, bibliography curation, and diploma-facing implementation framing. Unlike the older `plan.md` snapshot, this document is grounded in code that exists locally in the current workspace.

## Current Baseline

The current implementation anchors are already in place, but they are still closer to a baseline than to the literature-backed target architecture.

- `src/assets/core/price_forecast.py` trains and serves a 24-hour baseline `RandomForestRegressor` forecaster.
- `src/assets/core/optimization_schedule.py` builds a deterministic schedule with dynamic programming and a baseline economic objective.
- `scripts/ml_integration_api.py` resolves the current recommendation, applies incumbent enhancements, and builds the Python-side recommendation contract.
- `energy_ml/pipeline.py` still holds the simpler rule-driven recommendation and status surfaces that back part of the user-facing behavior.
- `dashboard/server/utils/recommendation-contract.ts` and `dashboard/server/api/ml/recommendation.get.ts` normalize and expose the recommendation contract to the active dashboard.
- `src/assets/benchmarks/performance.py` and `src/data_pipeline/benchmark_helpers.py` already give the repo a benchmark lane that can be extended instead of reinvented.
- Active forecast runtime selection is now benchmark-backed: only validated promotion metadata emitted from `benchmark_engines` is allowed to change the model selected by `src/assets/core/price_forecast.py`.
- Household EMS expansion, demand response, learned-policy or RL control, and dashboard redesign remain deferred until the bridge, lineage, and benchmark promotion program stay trustworthy under the backend validation path.

## Roadmap Principles

- Upgrade the active Dagster plus dashboard runtime instead of building a parallel research-only stack.
- Keep the deterministic path as the production default until a stronger experiment lane proves a learned policy is worth serving.
- Judge forecasting changes by downstream schedule value, not only by point-error metrics.
- Treat validated promotion metadata from the benchmark lane as the only active runtime control plane for forecast model selection; do not rely on ad hoc toggles.
- Prefer new modules under `src/data_pipeline/` or adjacent owning assets instead of spreading forecasting and optimizer logic across unrelated roots.
- Keep user-facing contract changes explicit and stable through the existing recommendation normalization surfaces.

## Phase 0. Evaluation Foundation and Model Abstraction

### Goal

Make forecast upgrades measurable in terms the arbitrage MVP actually cares about, and remove the hard coupling between the forecast asset and the current RandomForest baseline.

### Literature Drivers

- `Lago2021ForecastingDayAhead`
- `Smets2025ValueOrientedPriceForecasting`
- `Sang2022DecisionFocusedArbitrage`
- `ElmachtoubGrigas2022SmartPredictThenOptimize`

### Code Anchors

- `src/assets/core/price_forecast.py`
- `src/data_pipeline/price_forecast_features.py`
- `src/train_baseline.py`
- `src/assets/benchmarks/performance.py`
- `src/data_pipeline/benchmark_helpers.py`
- `src/definitions.py`

### Implementation Work

1. Extract the model-specific parts of `price_forecast_asset` into a small forecasting-model registry or adapter layer under `src/data_pipeline/`.
2. Keep the existing RandomForest implementation as the incumbent baseline, but stop hardcoding it as the only model family.
3. Extend the benchmark path so forecast candidates are ranked on both forecast error and downstream economic value.
4. Add a leakage-safe walk-forward evaluation routine that the benchmark asset or helper path can reuse.
5. Standardize model metadata so every candidate records `model_name`, training rows, forecast horizon, and the evaluation metrics used for promotion.

### Exit Criteria

- The repo can benchmark more than one forecast family without rewriting `price_forecast_asset`.
- Model comparison includes at least one value-oriented metric in addition to RMSE and MAE.
- The RandomForest path remains runnable as the baseline.

### Validation

- `pytest tests/unit/test_train_baseline.py -q`
- Focused unit tests for the model registry or benchmark helper additions.
- `dagster asset materialize -m src.definitions --select price_forecast_asset`

### Concrete Task Breakdown

1. Forecast registry foundation.
Files: `src/data_pipeline/forecast_model_registry.py`, `src/assets/core/price_forecast.py`.
Tests: `tests/unit/test_forecast_model_registry.py`, `tests/unit/test_core_forecast_and_weather_assets.py::test_price_forecast_asset_resolves_model_from_registry`.

2. Walk-forward and value-scoring helpers.
Files: `src/data_pipeline/price_forecast_features.py`, `src/assets/core/price_forecast.py`.
Tests: `tests/unit/test_price_forecast_features_module.py`, `tests/unit/test_core_forecast_and_weather_assets.py::test_price_forecast_asset_resolves_model_from_registry`.

3. Benchmark scorecard hookup.
Files: `src/assets/benchmarks/performance.py`, `src/data_pipeline/benchmark_helpers.py`.
Tests: a focused benchmark-helper test slice plus the existing benchmark asset path once value metrics are surfaced in reports.

4. Baseline training metadata alignment.
Files: `src/train_baseline.py`, `src/data_pipeline/forecast_model_registry.py`.
Tests: `tests/unit/test_train_baseline.py`.

5. Promotion and runtime selection wiring.
Files: `src/assets/core/price_forecast.py`, `src/definitions.py`.
Tests: focused forecast asset tests plus `dagster asset materialize -m src.definitions --select price_forecast_asset`.

## Phase 1. First Forecast Replacements

### Goal

Land the first serious replacements for the current RandomForest baseline without destabilizing the rest of the pipeline.

### Literature Drivers

- `OConnor2025ElectricityPriceForecastingReview`
- `Olivares2023NBEATSx`

### Code Anchors

- `src/assets/core/price_forecast.py`
- `src/data_pipeline/price_forecast_features.py`
- `src/assets/benchmarks/performance.py`
- `src/data_pipeline/benchmark_helpers.py`

### Implementation Work

1. Add the first two forecast candidates behind the model abstraction layer.
2. Keep one candidate simple and tabular-friendly and one candidate neural, with NBEATSx as the first deep model target.
3. Preserve the current forecast output contract so downstream optimization does not need a full rewrite in the same slice.
4. Add benchmark reporting that compares incumbent RandomForest versus the new candidates on the same backtest windows.
5. Make model promotion explicit: the best candidate becomes active only after the shared benchmark says it wins on the chosen scorecard.

### Exit Criteria

- The codebase can run the incumbent and at least one literature-backed replacement through the same forecast asset path.
- Benchmarks produce a promotion decision with traceable metrics.
- Downstream optimization still receives the existing forecast columns.

### Validation

- Extend the forecast unit-test slice introduced in Phase 0.
- Run the relevant benchmark asset path.
- Confirm the output still materializes through `src.definitions.py`.

## Phase 2. Probabilistic and Risk-Aware Forecasting

### Goal

Move from point forecasts plus residual bands toward uncertainty-aware forecasts that the optimizer can actually use.

### Literature Drivers

- `Jiang2024ProbabilisticTFT`
- `Weber2024OpenSourceEnergyArbitrage`

### Code Anchors

- `src/assets/core/price_forecast.py`
- `src/data_pipeline/price_forecast_features.py`
- `src/assets/core/optimization_schedule.py`
- `src/data_pipeline/optimization_schedule_inputs.py`
- `src/assets/benchmarks/performance.py`

### Implementation Work

1. Replace the residual-std heuristic bands with quantile or scenario-aware forecast outputs.
2. Extend the forecast contract to carry explicit uncertainty information that downstream code can consume without guessing.
3. Teach the optimizer input layer to derive scenario bands or conservative/export-aware price horizons.
4. Add benchmark cases that compare pure point-forecast dispatch against risk-aware dispatch.
5. Keep the default production behavior conservative: if probabilistic data is missing, the current deterministic path still runs.

### Exit Criteria

- The forecast asset emits explicit uncertainty outputs instead of only a symmetric residual spread.
- The optimization layer can consume those outputs without breaking the baseline deterministic path.
- The benchmark path can show whether uncertainty-aware scheduling improves economic outcomes.

### Validation

- New unit tests for probabilistic contract columns and scenario extraction.
- `dagster asset materialize -m src.definitions --select price_forecast_asset`
- `dagster asset materialize -m src.definitions --select optimization_schedule_asset`

## Phase 3. Rolling-Horizon and Economic Objective Upgrade

### Goal

Replace the current single-pass deterministic schedule with a richer rolling-horizon scheduler that reflects degradation and real economic tradeoffs more honestly.

### Literature Drivers

- `Finhold2023OptimizingMarketingFlexibility`
- `Kampker2025BatteryEnergyStorageModelling`
- `Zhang2025BatteryStateEstimationReview`

### Code Anchors

- `src/assets/core/optimization_schedule.py`
- `src/data_pipeline/optimization_schedule_inputs.py`
- `src/physics/economics.py`
- `src/assets/core/client_state.py`
- `src/data_pipeline/battery_state_loader.py`

### Implementation Work

1. Wrap the existing schedule generation in a rolling-horizon recomputation pattern rather than a single static optimization pass.
2. Replace remaining placeholder economics with configuration-driven degradation and throughput costs wherever the baseline still simplifies too aggressively.
3. Extend schedule outputs with the objective breakdown needed for comparison and debugging.
4. Keep hourly resolution as the active target until the data and validation surfaces support finer granularity.
5. Preserve the canonical schedule schema discipline while extending it; do not fork a second schedule contract.

### Exit Criteria

- The optimizer recomputes over a moving horizon rather than behaving like a one-shot schedule generator.
- Degradation and cost terms are traceable in the output.
- The schedule remains compatible with existing downstream contract checks.

### Validation

- Add narrow optimizer tests around objective decomposition and rolling-horizon state transitions.
- `dagster asset materialize -m src.definitions --select optimization_schedule_asset`
- `dagster job execute -m src.definitions -j optimization_schedule_contract_checks`

## Phase 4. Recommendation Contract and Dashboard Enrichment

### Goal

Surface the richer forecast and optimization decisions through the active recommendation and dashboard paths without breaking the normalized action contract.

### Literature Drivers

- `Mischos2023IntelligentEMSReview`
- `Smets2025ValueOrientedPriceForecasting`
- `Finhold2023OptimizingMarketingFlexibility`

### Code Anchors

- `scripts/ml_integration_api.py`
- `energy_ml/pipeline.py`
- `dashboard/server/utils/recommendation-contract.ts`
- `dashboard/server/api/ml/recommendation.get.ts`
- `dashboard/app/components/ML/ForecastChart.vue`
- `dashboard/app/components/ML/RecommendationCard.vue`
- `dashboard/pages/control.vue`

### Implementation Work

1. Extend the Python recommendation payload with forecast-model identity, value-oriented reasoning, and optimizer objective breakdown.
2. Keep `normalized_action` and provenance stable while expanding optional detail fields.
3. Make the dashboard show why the action was chosen in terms of price signal, confidence, objective tradeoff, and fallback mode.
4. Reuse the existing contract utilities rather than creating a second API shape for the richer explanation path.
5. Align `energy_ml/pipeline.py` and `scripts/ml_integration_api.py` so the user sees one provenance vocabulary across rule-engine and Dagster-backed results.

### Exit Criteria

- The active dashboard can display richer reasoning without changing the canonical BUY/SELL/HOLD interface.
- Recommendation provenance remains normalized through the existing TypeScript utilities.
- The Python and dashboard layers agree on the same action and reason vocabulary.

### Validation

- `pytest tests/unit/test_optimizer_and_pipeline_surfaces.py -q`
- Narrow contract tests for the dashboard recommendation normalization utilities.
- Smoke `/api/ml/recommendation` with incumbent and fallback cases.

## Phase 5. Household EMS and Demand-Response Objective Expansion

### Goal

Upgrade the deterministic optimizer from pure battery arbitrage toward a more realistic household EMS objective with comfort, appliance, and incentive-aware behavior.

### Literature Drivers

- `Kwon2022AIBasedHomeEMS`
- `Hu2024IncentiveBasedIntegratedDemandResponse`
- `Liu2025DistributedSmartHomeNILM`
- `Ikram2024SmartHomeLoadScheduling`

### Code Anchors

- `src/assets/core/optimization_schedule.py`
- `src/data_pipeline/optimization_schedule_inputs.py`
- `src/assets/core/client_state.py`
- `src/data_pipeline/client_load_solar_simulation.py`
- `scripts/ml_integration_api.py`
- `dashboard/server/api/ml/recommendation.get.ts`

### Implementation Work

1. Add optimizer inputs for comfort penalties, appliance or load categories, and demand-response event signals.
2. Extend the objective from pure price arbitrage to a configurable multi-objective household EMS function.
3. Add scenario paths for incentive-aware scheduling and household export restrictions.
4. Keep the first version deterministic and explainable; this phase is about objective realism, not policy learning.
5. Expand the user-facing reasoning so the recommendation can explain tradeoffs between savings, comfort, and reserve preservation.

### Exit Criteria

- The optimizer can score more than pure arbitrage revenue and cost.
- Demand-response or household-comfort scenarios are represented in code and tests.
- The dashboard can explain why a lower-profit action was still chosen.

### Validation

- New unit tests for objective weighting and demand-response constraints.
- `dagster asset materialize -m src.definitions --select optimization_schedule_asset`
- Targeted API smoke tests for household-context recommendation outputs.

## Phase 6. Offline Learned-Policy Experiment Lane

### Goal

Add an experimental RL or learned-policy comparison lane without replacing the deterministic production path prematurely.

### Literature Drivers

- `Wei2023DeepReinforcementLearningSmartHome`
- `Sang2022DecisionFocusedArbitrage`

### Code Anchors

- `src/rl_training.py`
- `scripts/ml_integration_api.py`
- `dashboard/server/api/ml/recommendation.get.ts`
- any decision-history persistence path produced by earlier phases

### Implementation Work

1. Reuse the decision and forecast history produced by earlier phases as offline training data.
2. Keep the learned-policy path behind the existing serving-mode boundary in `scripts/ml_integration_api.py`.
3. Compare the learned-policy lane against the deterministic incumbent on the same scenarios and economic scorecard.
4. Do not switch live serving by default until the experiment lane is measurably better and operationally inspectable.
5. Keep the recommendation contract stable so the dashboard does not need a separate rendering path for learned-policy experiments.

### Exit Criteria

- The repo can evaluate a learned-policy recommendation path offline against the deterministic baseline.
- The serving-mode fallback remains safe and explicit.
- No live product claim depends on RL before the evidence exists.

### Validation

- Offline evaluation tests and experiment reports.
- Focused serving-mode tests in the Python bridge.
- Manual API smoke with learned-policy mode enabled and disabled.

## Deferred Scope

These items stay explicitly outside the near-term roadmap unless the codebase, data, and evaluation surfaces mature enough first:

- full production RL control as the default decision maker
- NVIDIA Modulus or other separate physics-stack integration
- quarter-hour settlement optimization before the data model supports it
- real hardware execution or live autonomous market trading claims
- VPP aggregation beyond the single-site or household optimization scope

## Recommended Delivery Order

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6

That order keeps the repo honest: first measurement, then better forecasts, then optimizer upgrades, then richer user-facing contracts, then household-objective realism, and only then a learned-policy experiment lane.

## Appendix: energy_ml/mlops/ Analysis (2026-04-18)

The `energy_ml/mlops/` folder contains isolated ML infrastructure assessed on 2026-04-18.

### Files

| File | Lines | Status | Notes |
|------|-------|--------|-------|
| `battery_physics.py` | 510 | Useful | Multi-chemistry (LFP, Lead-Acid, VRFB) with degradation physics |
| `feature_store.py` | 416 | Useful | Polars-based feature serving with batch/online stores |
| `model_registry.py` | 420 | Obsolete | Uses old pickle/joblib; should migrate to MLflow LoggedModel API |
| `monitoring_dashboard.py` | 437 | Useful | Alert manager, drift detection, A/B testing |
| `optimization_engine.py` | 325 | Useful | Strategy-based optimization (max_earn, max_battery_health) |
| `renewable_forecasting.py` | 272 | Useful | Solar/wind forecasting with Open-Meteo integration |
| `retraining_pipeline.py` | 465 | Useful | Automated retraining with drift detection |

### Key Findings

1. **No `*_support.py` duplicates** - All 7 support files verified functional
2. **Model registry uses deprecated patterns** - `joblib.dump/load` vs MLflow LoggedModel API
3. **Hardcoded model name** - `"energy_optimizer"` should be configurable
4. **No active imports from `src/`** - `energy_ml/mlops/` is isolated from Dagster pipeline

### Recommendations

- Phase 0-2 work (forecasting, benchmarking) continues using `src/` patterns
- Consider migrating `energy_ml/mlops/` components to `src/` once Phase 4-5 surfaces
- Battery physics and renewable forecasting are candidates for `src/physics/` and `src/data_pipeline/`
