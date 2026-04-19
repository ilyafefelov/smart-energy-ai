# Medallion Preview

Generated at 2026-04-19T12:07:48+00:00 from the supervisor medallion manifest.

## Layer Snapshot

| Layer | Datasets | Materialized | Latest Update |
| --- | ---: | ---: | --- |
| Bronze | 2 | 2 | 2026-04-24T23:00:00+00:00 |
| Silver | 3 | 2 | 2026-04-20T23:00:00+00:00 |
| Gold | 8 | 8 | 2026-04-20T23:00:00+00:00 |

## Provenance Snapshot

- Market input mode: `fallback-derived`
- Weather input mode: `real`
- Client-state mode: `simulated`

## Fleet And Case Study

- Fleet source: `multi_client_analytics` with status `materialized_asset` and 5 clients.
- Case study tenant: `client_001_kyiv_mall` (Kyiv Shopping Mall) via `manifest_default_first_customer`.

## Experiment Snapshot

- Model-vs-model status: `materialized` from `forecast_value_benchmark_asset`.
- Optimizer-vs-optimizer status: `comparable`.
- PPO validation status: `available`.
