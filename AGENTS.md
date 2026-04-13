# Smart Energy AI - Agent Instructions

This file is the workspace-level source of truth for repository workflow,
runtime truth, validation, and landing expectations. Other overlays should stay
narrow and defer to this file when guidance overlaps.

## Beads-First Workflow

This repo uses `bd` (Beads) for task tracking.

Before writing code, editing docs, or doing cleanup:

1. Run `bd ready --json`.
2. If there is no matching issue for the requested work, create one with `bd create ... --json`.
3. Claim the task with `bd update <id> --claim --json`.
4. Record discovered follow-up work with linked issues using `--deps discovered-from:<id>`.
5. Close the issue with `bd close <id> --reason "..." --json` only after validation.

Do not track work in markdown TODO lists or external trackers.

If `bd` or its Dolt backend is unavailable in the local environment, call out
the blocker explicitly and continue with scoped changes plus validation. Do not
invent an alternate tracker.

Useful commands:

```bash
bd ready --json
bd show <id> --json
bd update <id> --claim --json
bd close <id> --reason "Completed" --json
bd dolt remote list --json
pwsh ./scripts/local/bd-dolt-sync-safe.ps1
```

## Current Runtime Surface

- `dashboard/` is the canonical Nuxt application.
- `archive/nuxt_dashboard_legacy_20260306/` is legacy and should not be treated as active runtime code.
- `streamlit_dashboard/` still exists, but it is not the primary dashboard path for the active local stack.
- The main local operator flow is the Dagster + Nuxt stack started from the repository root.

Start the local stack:

```powershell
Set-Location D:\OpenClaw-Backup\clawd\projects\smart-energy-ai
.\scripts\local\start-local-stack.ps1 -Start both
```

Stop the local stack:

```powershell
.\scripts\local\start-local-stack.ps1 -Stop both
```

Canonical local endpoints:

- Dagster UI: `http://127.0.0.1:3000`
- Dashboard: `http://127.0.0.1:3600`

## Repo Facts That Matter

- Core orchestration and production-path work centers on Dagster, the `src/` assets, the `energy_ml/` runtime, and the Nuxt dashboard in `dashboard/`.
- Market and weather flows have synthetic fallbacks so local work can stay runnable when external services are unavailable.
- AWS Free Tier deployment is planned and documented, but it is a later stage after local/runtime hardening.

## Validation Expectations

- Prefer focused tests for the files you touch.
- If changing runtime behavior, validate the smallest relevant local path first.
- If a module is loaded directly by file path in tests, preserve that import pattern when refactoring.

Useful commands:

```bash
pytest tests/ -v
pytest tests/unit/<target_test>.py -q
dagster asset materialize -m src.definitions --select "*optimization_schedule_asset"
dagster job execute -m src.definitions -j optimization_schedule_contract_checks
```

## Execution Style

- Think before coding: state assumptions, surface ambiguity, and do not silently choose between multiple plausible interpretations when behavior would change.
- Simplicity first: prefer the minimum code that solves the task; avoid speculative abstractions, extra configurability, or broad refactors.
- Surgical changes: touch only the requested surface, remove only the orphans created by your own change, and leave unrelated cleanup for separate work unless explicitly asked.
- Goal-driven execution: define a concrete success check for each slice and validate the narrowest relevant path immediately after editing.

## Key References

- `README.md` - high-level system and deployment overview
- `QUICK_START.md` - current local development flow
- `docs/technical/TEST_PIPELINE_GUIDE.md` - validation notes
- `docs/API_DOCUMENTATION_IMPORT_EXPORT.md` - import/export API docs
- `docs/deployment/EC2_DAGSTER_T3_MICRO_RUNBOOK.md` - EC2 Dagster service runbook
- `docs/archive/` - historical reports and legacy status documents

## Landing Work Cleanly

When finishing a bounded task:

1. Validate the relevant code path.
2. Update the Beads issue status.
3. If your workflow includes landing the batch, run:

```bash
git pull --rebase
pwsh ./scripts/local/bd-dolt-sync-safe.ps1
git push
git status
```

4. If the task branch has been merged or superseded, delete or prune the stale
   branch after confirming the remote state is current and no follow-up work
   still depends on it.

The goal is to leave git and Beads in a clean, synchronized state without
stale task branches.
