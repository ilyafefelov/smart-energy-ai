# Smart Energy AI Quick Start

This is the current operator-facing quick start for local development and verification. Historical completion reports, session summaries, and legacy status documents have been moved under `docs/archive/`.

## Start The Local Stack

From the repository root:

```powershell
Set-Location D:\OpenClaw-Backup\clawd\projects\smart-energy-ai
.\scripts\local\start-local-stack.ps1 -Start both
```

`dashboard/` is the canonical Nuxt app used by the local launcher and runtime checks. The former `nuxt_dashboard/` tree has been archived to `archive/nuxt_dashboard_legacy_20260306/` and is not started by the root scripts.

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

Run the local MVP smoke path from the repository root:

```powershell
.\scripts\local\run-local-mvp-smoke.ps1
```

Run the focused Stage 2 evidence smoke command directly against a running dashboard:

```powershell
node dashboard/scripts/stage2_demo_evidence.mjs
```

`run-local-mvp-smoke.ps1` now includes both the dashboard API smoke checks and the Stage 2 evidence smoke step. Use the direct Node command when the local stack is already up and you only want the Stage 2 scenario gate. The dashboard package also exposes the same runner as `npm -C dashboard run smoke:stage2-evidence` when you prefer the npm alias.

## Notes

- The active dashboard is the Nuxt application under `dashboard/`.
- Market and weather assets have synthetic fallbacks so local development remains runnable when external sources are unavailable.
- Benchmark assets and multi-tenant analytics are separate from the core daily recommendation path and can be run independently.

## Working With Agents On Deliverables

This repo includes a recurring-deliverables instruction at [.github/instructions/recurring-deliverables.instructions.md](.github/instructions/recurring-deliverables.instructions.md) plus workspace slash prompts for weekly reports and supervisor-package refreshes:

- [.github/prompts/stage2-weekly-report.prompt.md](.github/prompts/stage2-weekly-report.prompt.md)
- [.github/prompts/stage2-weekly-report-from-commits.prompt.md](.github/prompts/stage2-weekly-report-from-commits.prompt.md)
- [.github/prompts/supervisor-package-refresh.prompt.md](.github/prompts/supervisor-package-refresh.prompt.md)

Example prompts you can give directly in chat:

```text
Update this week's Stage 2 report with the latest commits, tests, risks, and literature links.
```

```text
Start week 03 report from the existing template and prepare the matching artifacts folder.
```

```text
Extend the supervisor report package and keep the medallion manifest, scorecard, catalog, and indexes in sync.
```

```text
Refresh the defense brief and thesis appendix export after the latest supervisor-report changes.
```

How to use this as the repo owner:

- Name the exact week when you want a new weekly report created.
- If you do not name the week, the agent should ask which week to update before editing `docs/Stage 2/weekly_reports/`.
- Use the base weekly-report prompt when you want a structured drafting flow from explicit inputs.
- Use the commit-driven weekly-report prompt when you want the draft framed from recent git history, touched files, and validation evidence.
- Use the supervisor-package prompt when you want to refresh the medallion report package and its linked generated outputs.

How agents should use it:

- Treat weekly reports and supervisor docs as a linked deliverable package.
- Reuse the weekly template and artifact-folder conventions in `docs/Stage 2/weekly_reports/`.
- Keep evidence grounded in commits, tests, generated artifacts, and literature links.
- If `artifacts/medallion/medallion_dataset_manifest.yaml` changes, rerender the manifest-backed outputs.
