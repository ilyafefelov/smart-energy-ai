# Supervisor Medallion Runtime Roadmap

This document is the deferred implementation roadmap for the next runtime step beyond the current supervisor report. It does not describe current runtime state. It describes the intended evolution if the team decides to make the logical Bronze, Silver, and Gold framing more explicit in the Dagster asset graph.

## Goal

Move from a documentation-only medallion overlay toward a more physically explicit asset topology by:

1. keeping the existing Bronze market and weather assets as source-facing raw ingest
2. introducing explicit cleaned Silver market and weather assets
3. rewiring downstream Silver and Gold consumers to depend on those cleaned assets
4. promoting the current Gold experiment summary into a first-class Dagster-owned Gold dataset

## Current State Versus Target State

| Area | Current runtime | Target runtime |
| --- | --- | --- |
| Market lane | Bronze ingest in `market_data_asset` feeds forecast and downstream consumers directly | Bronze raw ingest plus explicit Silver curated market asset |
| Weather lane | Bronze ingest in `weather_asset` feeds client state and features directly | Bronze raw ingest plus explicit Silver curated weather asset |
| Downstream Silver | `client_state_asset` and `feature_matrix_asset` consume Bronze surfaces directly | `client_state_asset` and `feature_matrix_asset` consume curated Silver market and weather assets |
| Gold reporting summary | `gold_experiment_summary.json` is a rendered supervisor payload | `gold_experiment_summary_asset` becomes a first-class Gold dataset |
| Docs and manifest | medallion framing is logical only | medallion framing becomes closer to the physical asset topology |

## Proposed Target Asset Topology

| Proposed asset | Layer | Intended owner | Intended role |
| --- | --- | --- | --- |
| `market_data_asset` | Bronze | `src/assets/core/market.py` | raw OREE or synthetic fallback ingest |
| `weather_asset` | Bronze | `src/assets/core/weather.py` | raw Open-Meteo or synthetic fallback ingest |
| `market_data_curated_asset` | Silver | `src/assets/core/market.py` or sibling market-cleaning module | validated and normalized market history for forecasting and reporting |
| `weather_curated_asset` | Silver | `src/assets/core/weather.py` or sibling weather-cleaning module | validated and normalized weather forecast for client state and feature engineering |
| `client_state_asset` | Silver | existing owner | consume curated weather and market surfaces plus tenant state |
| `feature_matrix_asset` | Silver | existing owner | consume curated market and weather plus client state |
| `price_forecast_asset` | Gold | existing owner | forecast output over curated Silver features |
| `optimization_schedule_asset` | Gold | existing owner | baseline schedule over forecast horizon |
| `optimization_schedule_milp_asset` | Gold | existing owner | MILP alternative schedule over forecast horizon |
| `gold_experiment_summary_asset` | Gold | new reporting owner under `src/assets/benchmarks/` or `src/assets/core/` | first-class Gold dataset for the current JSON experiment summary contract |

## Recommended Implementation Phases

### Phase 1: Introduce Silver market and weather assets

- Reuse the existing validation helpers in `src/data_pipeline/market_validation.py` and `src/data_pipeline/weather_validation.py`.
- Keep Bronze assets as the raw source owners.
- Add explicit Silver curated assets that output the normalized tables currently implied by the validation path.
- Do not rewire downstream consumers yet.

### Phase 2: Rewire downstream Silver and Gold consumers

- Update `client_state_asset` to consume curated market and weather rather than raw Bronze surfaces directly.
- Update `feature_matrix_asset` to consume curated market and weather rather than raw Bronze surfaces directly.
- Ensure `price_forecast_asset` uses the same curated Silver lineage through feature generation.
- Keep output contracts unchanged during the rewiring phase.

### Phase 3: Promote the Gold experiment summary to a first-class asset

- Convert the current `build_gold_summary()` logic in [src/data_pipeline/medallion_catalog.py](../../src/data_pipeline/medallion_catalog.py#L613) into a Dagster-owned output surface.
- Preserve the current JSON contract shape from [artifacts/medallion/gold_experiment_summary.json](../../artifacts/medallion/gold_experiment_summary.json).
- Expose the new asset in [src/definitions.py](../../src/definitions.py) and in the supervisor manifest.
- Keep the renderer as a packaging layer over the asset rather than the only producer.

### Phase 4: Refresh package and validation surfaces

- Update [artifacts/medallion/medallion_dataset_manifest.yaml](../../artifacts/medallion/medallion_dataset_manifest.yaml) to reflect the new physical Silver assets and Gold summary asset.
- Update the architecture, catalog, and dataset-contract docs to match the new topology.
- Extend focused tests and any direct-file smoke tests that assert current asset ownership.

## Validation Strategy

| Phase | Minimum validation |
| --- | --- |
| Phase 1 | materialize Bronze plus new Silver curated assets and verify row counts, timestamps, and fallback semantics |
| Phase 2 | materialize `client_state_asset`, `feature_matrix_asset`, and `price_forecast_asset` over the curated Silver sources and compare contract continuity |
| Phase 3 | materialize `gold_experiment_summary_asset` and compare its payload to the current JSON contract |
| Phase 4 | rerender the supervisor package and rerun focused medallion tests plus the asset-level smoke tests that cover market, weather, optimization, and benchmark surfaces |

## Risks And Constraints

- The current runtime already works for supervisor reporting, so this roadmap should not be treated as a blocker for the report package.
- Market and weather asset changes could ripple into `client_state_asset`, `feature_matrix_asset`, and forecast training if contract continuity is not preserved carefully.
- The Gold experiment summary currently composes multiple optional local surfaces, so promoting it to a first-class asset requires explicit handling of `materialized_empty` and `not_materialized` states.
- Dashboard work should remain out of scope unless a concrete API or consumption contract changes.

## Recommendation

Keep this roadmap deferred until there is explicit approval to do runtime work. The current report package already does its job. If the next task is implementation, start with Phase 1 only and keep the output contracts stable until the Silver asset split has been validated.