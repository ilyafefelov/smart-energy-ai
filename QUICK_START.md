# Smart Energy AI Quick Start

This is the current operator-facing quick start for local development and verification. Historical completion reports, session summaries, and legacy status documents have been moved under `docs/archive/`.

## Start The Local Stack

From the repository root:

```powershell
Set-Location D:\OpenClaw-Backup\clawd\projects\smart-energy-ai
.\scripts\local\start-local-stack.ps1 -Start both
```

Canonical local endpoints:

- Dagster UI: `http://127.0.0.1:3000`
- Dashboard: `http://127.0.0.1:3600`

Stop both services with:

```powershell
.\scripts\local\start-local-stack.ps1 -Stop both
```

## Primary Entry Points

- `README.md` - high-level system and deployment overview
- `docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md` - current Dagster asset graph, job boundaries, and Mermaid diagram
- `docs/deployment/EC2_DAGSTER_T3_MICRO_RUNBOOK.md` - EC2 Dagster deployment and service operations
- `docs/technical/TEST_PIPELINE_GUIDE.md` - pipeline testing and validation notes
- `docs/archive/` - historical reports and previously archived legacy artifacts

## Dagster Jobs

- `daily_data_refresh` - core ingestion, feature engineering, forecasting, optimization, and schedule-check flow
- `optimization_schedule_contract_checks` - upstream-aware optimization validation job for runtime contract checks
- `benchmark_engines` - benchmark and MLflow tracking branch
- `multi_tenant_analytics` - cross-tenant summary analytics

## Useful Commands

Run the focused optimization contract tests:

```powershell
pytest tests/unit/test_baseline_dp_optimizer.py tests/unit/test_optimization_schedule_asset_checks.py -q
```

Materialize the optimization chain:

```powershell
dagster asset materialize -m src.definitions --select "*optimization_schedule_asset"
```

Run the dedicated schedule contract-check job:

```powershell
dagster job execute -m src.definitions -j optimization_schedule_contract_checks
```

## Notes

- The active dashboard is the Nuxt application under `dashboard/`.
- Market and weather assets have synthetic fallbacks so local development remains runnable when external sources are unavailable.
- Benchmark assets and multi-tenant analytics are separate from the core daily recommendation path and can be run independently.
