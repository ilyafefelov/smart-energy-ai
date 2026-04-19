# Supervisor Thesis Appendix Export

This document is the thesis-appendix-ready export of the supervisor medallion package. It is written as a copy-ready appendix text that can be inserted into a diploma, thesis, or final report with minimal adaptation.

## How To Use This Export

- Keep the section numbering if the appendix is inserted directly.
- Replace repository-relative file names with figure or appendix references if the final document will be printed.
- Use the longer [SUPERVISOR_MEDALLION_REPORT.md](SUPERVISOR_MEDALLION_REPORT.md) as the master narrative if additional detail is needed.

## A.1 Active Dagster Runtime And Scope Guardrails

The Smart Energy AI system is currently implemented as a Dagster-centered operational and analytics pipeline rooted at `src/definitions.py`. For supervisor communication, the runtime is presented as a Bronze, Silver, and Gold architecture. This framing is a logical presentation overlay on the existing asset graph, storage surfaces, and benchmark outputs. It does not claim that the repository already uses a separate physical medallion warehouse layout.

The package remains explicit about provenance and maturity. Real-source, simulator-backed, benchmark-derived, and fallback-derived surfaces are distinguished rather than flattened into one generalized claim of operational readiness. Any future backend re-root or physical warehouse redesign remains outside the scope of the current appendix.

## A.2 Bronze, Silver, And Gold Dataset Inventory

The current package contains 13 documented datasets: 2 Bronze, 3 Silver, and 8 Gold. Bronze consists of `market_data_asset` and `weather_asset`, which provide source-facing ingest with explicit synthetic fallback behavior. Silver consists of `client_state_asset`, `feature_matrix_asset`, and dynamic tenant projections created by the multi-tenant asset factory. Gold consists of forecast, schedule, benchmark, model, and fleet-reporting outputs: `price_forecast_asset`, `optimization_schedule_asset`, `optimization_schedule_milp_asset`, `forecast_value_benchmark_asset`, `mlflow_tracking_asset`, `trained_model_asset`, `model_metadata_asset`, and `multi_client_analytics`.

This inventory is grounded in the canonical manifest at `artifacts/medallion/medallion_dataset_manifest.yaml` and rendered in the generated catalog. The package therefore maps the architectural narrative to specific current assets rather than to abstract layer names only.

## A.3 Dataset Contract And Gold Summary Model

The dataset contract posture is mixed by design. Some surfaces already expose explicit shared schema contracts, while others remain stable through asset behavior and validation logic. The strongest explicit contract in the current runtime is the schedule contract `OPTIMIZATION_SCHEDULE_SCHEMA`, defined in `src/assets/core/optimization_schedule.py`. The forecast benchmark lane is similarly formalized through `FORECAST_VALUE_SCORECARD_SCHEMA` in `src/data_pipeline/benchmark_helpers.py`.

The current Gold reporting mart for supervisor use is `artifacts/medallion/gold_experiment_summary.json`. This payload is rendered by `build_gold_summary()` in `src/data_pipeline/medallion_catalog.py` and acts as the machine-readable Gold summary contract for the report package. It includes layer coverage, fleet summary, case-study selection, model-vs-model state, MLflow tracking status, run-vs-run summary, optimizer comparison, model-artifact status, business metrics, and package limitations.

## A.4 Lineage, Freshness, And Fallback Posture

The runtime already exposes auditable lineage anchors. Forecast surfaces use `forecast_run_id`, optimization surfaces use `optimization_run_id`, and benchmark or model outputs expose MLflow identifiers such as `model_id`, `run_id`, and artifact paths where applicable. Freshness is represented through fields such as `forecast_freshness_minutes`, `benchmark_timestamp`, `analysis_timestamp`, and `battery_state_updated_at`.

The package also remains explicit about fallback behavior. Market and weather surfaces can degrade to synthetic data in local or impaired runs, and client-state can remain simulator-backed or configuration-backed in the absence of live telemetry. These conditions are presented as part of the contract rather than hidden from the appendix reader.

## A.5 API And Consumption Surface

The value of the package is not limited to offline materialization. The system already exposes an operator-facing API layer through the dashboard and backend route surfaces documented in `docs/API_REFERENCE.md`. These routes cover recommendation, schedule, configuration, control execution, and observability flows. As a result, the appendix can present the data products as consumable operational surfaces rather than as isolated analytical outputs.

## A.6 Experiments, Optimizer Comparison, And Business Metrics

The generated scorecard demonstrates four comparison families that are already available in the current runtime: model-vs-model, run-vs-run, optimizer-vs-optimizer, and business metrics. The benchmark lane currently shows one forecast candidate marked as `skipped` because an optional dependency is unavailable locally, which is an example of the package's honest status reporting. The optimizer comparison currently shows that the MILP schedule achieves a net-cost delta of `-0.68` EUR relative to the baseline dynamic-programming schedule. The business-metric lane currently reports daily PPO savings of `7902.38` EUR/day and a median daily arbitrage spread of `258.74` EUR/day.

These figures are reportable because the package reuses the existing benchmark, schedule, and reconciliation surfaces instead of inventing a separate summary plane.

## A.7 Fleet Summary And Case Study

The current package supports both breadth and one concrete operational story. The fleet view is anchored on `multi_client_analytics`, which provides a comparative slice across five clients. The default case study uses `client_001_kyiv_mall`, selected by the package's stable tenant rule. In the current local evidence, this tenant's market input mode is `fallback-derived`, weather input mode is `real`, and client-state mode is `simulated`. This combination illustrates the package's main methodological principle: the report remains useful even when not all lanes are equally mature, because provenance is surfaced explicitly.

## A.8 Limitations And Deferred Work

The current appendix should not be read as a claim that the runtime already implements a physical medallion warehouse. It should also not be read as a claim that all inputs are live field telemetry or that all MLflow and benchmark surfaces are always populated in local environments. The next runtime evolution, if approved, would be to introduce explicit cleaned Silver market and weather assets and to promote the current Gold experiment summary into a first-class Dagster asset. That future work is documented separately in [SUPERVISOR_MEDALLION_RUNTIME_ROADMAP.md](SUPERVISOR_MEDALLION_RUNTIME_ROADMAP.md) and remains outside the scope of the current appendix export.

## Appendix Figure And Table References

Use these supporting artifacts when formatting the final thesis appendix:

- Figure A.1: the Mermaid architecture diagram from [DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md](DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md)
- Table A.1: the layer inventory from [BRONZE_SILVER_GOLD_DATASET_CATALOG.md](BRONZE_SILVER_GOLD_DATASET_CATALOG.md)
- Table A.2: the Gold contract and field-family notes from [DATASET_MODEL_REFERENCE.md](DATASET_MODEL_REFERENCE.md)
- Table A.3: the optimizer and business-metric comparison tables from [EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md)
- Appendix data artifact: [artifacts/medallion/gold_experiment_summary.json](../../artifacts/medallion/gold_experiment_summary.json)