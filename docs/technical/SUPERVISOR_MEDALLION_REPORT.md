# Supervisor Medallion Report

This report is the single supervisor-facing handoff for the current Dagster runtime rooted at [src/definitions.py](../../src/definitions.py). It consolidates the existing medallion package into one narrative artifact without changing runtime behavior, data ownership, or repository topology.

The report treats Bronze, Silver, and Gold as a logical presentation overlay on the active asset graph. It does not claim that the repository already uses a physical medallion warehouse, and it preserves the current mix of real, simulator-backed, benchmark-derived, and fallback-derived evidence instead of flattening those differences.

## Executive Summary

- The current runtime already supports a credible Bronze, Silver, and Gold supervisor story over the live Dagster system.
- The exact current package inventory is 13 datasets: 2 Bronze, 3 Silver, and 8 Gold.
- The current Gold experiment-summary mart is [artifacts/medallion/gold_experiment_summary.json](../../artifacts/medallion/gold_experiment_summary.json), rendered from persisted Dagster and benchmark evidence by [src/data_pipeline/medallion_catalog.py](../../src/data_pipeline/medallion_catalog.py#L613).
- The package already includes model, run, optimizer, and business-metric comparison surfaces through [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md).
- The honest posture is that some Gold evidence remains optional locally, some inputs are simulator-backed, and a future Bronze-to-Silver asset split remains deferred architecture work rather than current runtime state.

## Scope And Evidence Sources

| Artifact | Role in this report | System of record |
| --- | --- | --- |
| [artifacts/medallion/medallion_dataset_manifest.yaml](../../artifacts/medallion/medallion_dataset_manifest.yaml) | Exact logical dataset inventory and package metadata | canonical manifest |
| [docs/technical/DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md](DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md) | Architecture narrative and scope guardrails | current Dagster runtime |
| [docs/technical/BRONZE_SILVER_GOLD_DATASET_CATALOG.md](BRONZE_SILVER_GOLD_DATASET_CATALOG.md) | Layer-by-layer dataset inventory and runtime snapshot | renderer plus persisted assets |
| [docs/technical/DATASET_MODEL_REFERENCE.md](DATASET_MODEL_REFERENCE.md) | Dataset grain, field families, schema posture, and Gold mart contract | asset code and explicit schema constants |
| [docs/technical/DATASET_LINEAGE_AND_FRESHNESS_SLA.md](DATASET_LINEAGE_AND_FRESHNESS_SLA.md) | Lineage, freshness, fallback, and enforcement posture | runtime checks and documented SLAs |
| [docs/API_REFERENCE.md](../API_REFERENCE.md) | Operator-facing consumption surface | dashboard and backend routes |
| [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md) | Model, run, optimizer, and business-metric comparison pack | benchmark, MLflow, schedule, and reconciliation surfaces |
| [artifacts/medallion/gold_experiment_summary.json](../../artifacts/medallion/gold_experiment_summary.json) | Machine-readable Gold mart for fleet and case-study packaging | rendered supervisor snapshot |

## Current Architecture In One View

| Layer | Current datasets | Main jobs and checks | Presentation surface |
| --- | --- | --- | --- |
| Bronze | `market_data_asset`, `weather_asset` | `daily_data_refresh` | `data/raw/` |
| Silver | `client_state_asset`, `feature_matrix_asset`, dynamic tenant projections | `daily_data_refresh`, `multi_tenant_analytics` | `data/processed/` |
| Gold | `price_forecast_asset`, `optimization_schedule_asset`, `optimization_schedule_milp_asset`, `forecast_value_benchmark_asset`, `mlflow_tracking_asset`, `trained_model_asset`, `model_metadata_asset`, `multi_client_analytics` | `daily_data_refresh`, `benchmark_engines`, `model_training`, `optimization_schedule_contract_checks`, `multi_tenant_analytics` | `data/results/`, `artifacts/medallion/` |

This architecture is already detailed in [docs/technical/DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md](DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md). The key supervisor message is that the runtime already has source ingest, operational enrichment, forecast and optimization outputs, benchmark evidence, and fleet analytics. The medallion framing is a documentation overlay for those existing owners.

## Exact Current Dataset Inventory

The current authoritative layer inventory comes from [artifacts/medallion/medallion_dataset_manifest.yaml](../../artifacts/medallion/medallion_dataset_manifest.yaml).

| Layer | Dataset ID | Current owner | Source kind | Main role |
| --- | --- | --- | --- | --- |
| Bronze | `market_data_asset` | `src/assets/core/market.py::market_data_asset` | `real_with_synthetic_fallback` | Source-facing OREE market ingest |
| Bronze | `weather_asset` | `src/assets/core/weather.py::weather_asset` | `real_with_synthetic_fallback` | Source-facing Open-Meteo weather ingest |
| Silver | `client_state_asset` | `src/assets/core/client_state.py::client_state_asset` | `simulator_backed_with_config_fallback` | Operational tenant state |
| Silver | `feature_matrix_asset` | `src/assets/core/feature_matrix.py::feature_matrix_asset` | `validated_enriched` | Forecast and optimization features |
| Silver | `tenant_asset_factory` | `src/assets/multi_tenant/asset_factory.py::create_all_assets` | `tenant_projected` | Dynamic per-tenant projections |
| Gold | `price_forecast_asset` | `src/assets/core/price_forecast.py::price_forecast_asset` | `ml_forecast_output` | Forecast horizon and uncertainty contract |
| Gold | `optimization_schedule_asset` | `src/assets/core/optimization_schedule.py::optimization_schedule_asset` | `optimization_output` | Baseline charge or discharge schedule |
| Gold | `optimization_schedule_milp_asset` | `src/assets/core/optimization_schedule_milp.py::optimization_schedule_milp_asset` | `optimizer_alternative_output` | MILP alternative schedule |
| Gold | `forecast_value_benchmark_asset` | `src/assets/benchmarks/performance.py::forecast_value_benchmark_asset` | `benchmark_derived` | Model-vs-model benchmark scorecard |
| Gold | `mlflow_tracking_asset` | `src/assets/benchmarks/performance.py::mlflow_tracking_asset` | `experiment_tracking` | MLflow benchmark export |
| Gold | `trained_model_asset` | `src/assets/benchmarks/model_training.py::trained_model_asset` | `model_artifact` | Trained-model artifact lane |
| Gold | `model_metadata_asset` | `src/assets/benchmarks/model_training.py::model_metadata_asset` | `model_metadata` | Logged-model metadata lookup |
| Gold | `multi_client_analytics` | `src/assets/multi_tenant/asset_factory.py::multi_client_analytics` | `fleet_analytics` | Fleet-wide comparative summary |

## Gold Experiment Summary Mart Contract

The current Gold mart contract for supervisor reporting is [artifacts/medallion/gold_experiment_summary.json](../../artifacts/medallion/gold_experiment_summary.json). It is rendered by [build_gold_summary()](../../src/data_pipeline/medallion_catalog.py#L613) and is the machine-readable summary behind the supervisor package.

**Current contract shape**

- Grain: one rendered supervisor snapshot per package generation
- Selection rule: first stable tenant from `customers.yaml` unless the renderer uses `--case-study-tenant`
- Status semantics: `materialized`, `materialized_empty`, `not_materialized`, `dagster_asset_check_surface`
- Evidence posture: derived from persisted Dagster assets, benchmark outputs, MLflow exports, and case-study selection metadata

| Contract block | Meaning | Primary sources |
| --- | --- | --- |
| `layer_summary` | dataset counts, materialization coverage, and freshness by logical layer | manifest plus current materializations |
| `fleet_view` | fleet-wide comparative summary | `multi_client_analytics` |
| `case_study` | one tenant slice with provenance-tagged metrics | `customers.yaml`, `multi_client_analytics`, source-mode resolution |
| `model_vs_model` | benchmark candidate and promotion results | `forecast_value_benchmark_asset` |
| `mlflow_tracking` | MLflow-backed benchmark logging status | `mlflow_tracking_asset` |
| `run_vs_run` | forecast, schedule, and model-artifact run surfaces | `price_forecast_asset`, schedule assets, trained-model assets |
| `optimizer_vs_optimizer` | baseline DP versus MILP economics | baseline and MILP schedule assets |
| `model_artifacts` | trained-model and metadata lookup status | `trained_model_asset`, `model_metadata_asset` |
| `business_metrics` | PPO validation, arbitrage spread, schedule totals, reconciliation | benchmark outputs and schedule checks |
| `limitations` | package caveats and deferred-work flags | manifest presentation defaults |

## Comparison Results Pack

The reusable comparison-results pack is generated at [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md). It now exposes four report-ready table families that can be reused for each supervisor update.

| Table family | System of record | Report purpose | Current artifact |
| --- | --- | --- | --- |
| Model-vs-model | `forecast_value_benchmark_asset` and `mlflow_tracking_asset` | compare forecast candidates, promotion decisions, and benchmark quality | [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md) |
| Run-vs-run | forecast, schedule, and model-artifact surfaces | compare current forecast, schedule, and model-output states across runs | [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md) |
| Optimizer-vs-optimizer | baseline and MILP schedule assets | compare economics and row coverage across optimizer strategies | [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md) |
| Business metrics | persisted benchmark outputs and contract checks | show savings, spreads, net costs, and reconciliation posture | [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md) |

## Current Snapshot Highlights

These are the main points visible in the currently rendered artifacts:

- The current model-vs-model surface has one benchmark candidate, and it is marked `skipped` because the optional `neuralforecast` dependency is unavailable locally.
- The optimizer comparison currently shows a MILP net-cost delta of `-0.68` EUR relative to the baseline DP schedule.
- The business-metric lane currently exposes PPO validation savings of `7902.38` EUR/day and a median daily arbitrage spread of `258.74` EUR.
- The default case-study tenant is `client_001_kyiv_mall`, and the current package correctly marks the market lane as `fallback-derived`, the weather lane as `real`, and the client-state lane as `simulated`.

## Deferred Implementation Roadmap

The current package documents the runtime as it exists today. The following changes are future implementation work only.

| Future change | Intended effect | Why it is deferred now |
| --- | --- | --- |
| Add dedicated Silver market curation asset | Separate raw Bronze market ingest from cleaned or validated Silver market history | current runtime already supports the supervisor narrative without changing asset ownership |
| Add dedicated Silver weather curation asset | Separate raw Bronze weather ingest from cleaned or feature-ready Silver weather data | current runtime already exposes weather provenance honestly through the Bronze and Silver chain |
| Promote the Gold experiment summary into a Dagster-owned dataset | Turn `gold_experiment_summary.json` into a first-class Gold asset instead of a rendered supervisor payload | the current JSON mart is sufficient for supervisor review and does not justify a runtime refactor yet |
| Rewire the feature and reporting chain after those new Silver assets exist | Make the pipeline physically closer to the logical medallion story | this is an architecture and runtime change, not a documentation completion task |

The practical next runtime plan, if requested later, is: keep Bronze source assets as the raw ingest layer, add explicit cleaned Silver market and weather assets, keep `client_state_asset` and `feature_matrix_asset` downstream of those cleaned assets, and then promote the Gold experiment summary into a materialized Gold dataset.

## Deliverables For This Report

The report package to hand to a supervisor now consists of these deliverables:

- [docs/technical/SUPERVISOR_MEDALLION_REPORT.md](SUPERVISOR_MEDALLION_REPORT.md) - consolidated supervisor report and handoff narrative
- [docs/technical/SUPERVISOR_DEFENSE_BRIEF.md](SUPERVISOR_DEFENSE_BRIEF.md) - shortest defense-ready version for an oral diploma review
- [docs/technical/SUPERVISOR_MEDALLION_RUNTIME_ROADMAP.md](SUPERVISOR_MEDALLION_RUNTIME_ROADMAP.md) - deferred runtime implementation roadmap for explicit Silver assets and a first-class Gold summary asset
- [docs/technical/SUPERVISOR_THESIS_APPENDIX_EXPORT.md](SUPERVISOR_THESIS_APPENDIX_EXPORT.md) - thesis-appendix-ready export text for written submission
- [docs/technical/DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md](DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md) - architecture narrative and Mermaid diagram
- [docs/technical/BRONZE_SILVER_GOLD_DATASET_CATALOG.md](BRONZE_SILVER_GOLD_DATASET_CATALOG.md) - exact dataset inventory with runtime snapshot evidence
- [docs/technical/DATASET_MODEL_REFERENCE.md](DATASET_MODEL_REFERENCE.md) - dataset contract and Gold mart schema reference
- [docs/technical/DATASET_LINEAGE_AND_FRESHNESS_SLA.md](DATASET_LINEAGE_AND_FRESHNESS_SLA.md) - lineage, freshness, and fallback posture
- [docs/API_REFERENCE.md](../API_REFERENCE.md) - dashboard and backend consumption surface
- [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](EXPERIMENTS_AND_RESULTS_SCORECARD.md) - reusable comparison tables for model, run, optimizer, and business metrics
- [artifacts/medallion/gold_experiment_summary.json](../../artifacts/medallion/gold_experiment_summary.json) - machine-readable Gold experiment-summary mart
- [docs/technical/SUPERVISOR_PRESENTATION_APPENDIX.md](SUPERVISOR_PRESENTATION_APPENDIX.md) - slide and thesis-appendix packaging layer

## Closing Position

The current package is ready for supervisor review because it already ties the active Dagster runtime to a clear Bronze, Silver, and Gold story, it names the exact current dataset set, it documents the Gold experiment-summary mart contract, and it provides reusable comparison tables. The remaining market and weather split belongs to a later runtime refactor plan, not to this report delivery.