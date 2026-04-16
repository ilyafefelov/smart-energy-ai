# Backend Package Convergence Plan

## Goal

Converge active backend logic toward a Docker-ready modular monolith with clear package ownership:

- `src/` owns Dagster orchestration, reusable ingestion helpers, and shared backend pipeline utilities.
- `energy_ml/` owns domain runtime code that is still used by the Python ML bridge and adjacent ML flows.
- `scripts/` stays limited to operator entrypoints, wrappers, and small task runners.

`dashboard/` is intentionally out of scope for this plan.

## Current Boundary

### Keep as active runtime surfaces

- `src/definitions.py` as the only active Dagster code location.
- `src/assets/core/` for Dagster asset orchestration.
- `src/data_pipeline/` for reusable data loading, validation, fallback, and transformation helpers.
- `energy_ml/` for ML/domain runtime code still used by the canonical Python bridge.
- `scripts/ml_integration_api.py` as the canonical backend Python ML bridge.

### Keep as compatibility or entrypoint surfaces

- `ml_integration_api.py` as a root compatibility wrapper.
- `energy_ml/ml_integration_api.py` as a package-relative compatibility wrapper.
- `scripts/` task runners that remain operational entrypoints rather than reusable libraries.

## Convergence Principles

1. Do not add new reusable backend logic to `scripts/`.
2. Do not re-embed helper logic back into Dagster asset modules once extracted to `src/data_pipeline/`.
3. Keep `energy_ml/` focused on domain/runtime code until a caller is ready to move with it.
4. Prefer compatibility wrappers during migration instead of broad import rewrites in one step.
5. Tie every stage to a narrow validation command before expanding scope.

## Stage Plan

### Stage 1: Finish thinning Dagster asset modules

Objective: keep `src/assets/core/` as orchestration-first modules.

Concrete moves:

- Continue extracting pure helper clusters from `src/assets/core/client_state.py` into `src/data_pipeline/`.
- Keep asset modules responsible for fallback choice, metadata emission, and Dagster-facing contracts.
- Avoid moving helper code into `scripts/` or `energy_ml/` when the caller is an asset module.

Primary file anchors:

- `src/assets/core/client_state.py`
- `src/data_pipeline/`

Validation:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_client_state_and_market_parsing.py -q
.venv\Scripts\python.exe -m pytest tests\unit\test_validation_and_asset_surfaces.py -q
```

### Stage 2: Audit and reduce script-root drift

Objective: make `scripts/` read as entrypoints instead of a second backend package.

Concrete moves:

- Audit Python files under `scripts/` for reusable logic that still belongs in `src/`.
- Move reusable helper code out of operational scripts into `src/` modules, leaving thin CLI/task wrappers behind.
- Keep `scripts/ml_integration_api.py` as the canonical bridge until all runtime consumers are ready for a package-native entrypoint.

Primary file anchors:

- `scripts/ml_integration_api.py`
- `scripts/recalculate_pipeline.py`
- `scripts/reconcile_optimization_history.py`
- `scripts/train_model.py`

Validation:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_tariff_and_root_ml_integration_surfaces.py -q
.venv\Scripts\python.exe -m pytest tests\unit\test_schedule_reconcile_and_test_runner_scripts.py -q
```

### Stage 3: Make package ownership explicit around `energy_ml/`

Objective: treat `energy_ml/` as domain/runtime code instead of a spillover namespace.

Concrete moves:

- Keep compatibility wrappers wrapper-only.
- Audit whether any surviving reusable helpers in `energy_ml/` are actually shared runtime entrypoint glue and should instead live under `src/`.
- Avoid moving stable ML/domain code out of `energy_ml/` unless a real consumer boundary is also moving.

Primary file anchors:

- `energy_ml/ml_integration_api.py`
- `energy_ml/ml_integration.py`
- `energy_ml/pipeline.py`
- `energy_ml/user_config.py`

Validation:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_ml_integration_surface.py -q
.venv\Scripts\python.exe -m pytest tests\unit\test_user_config_contracts.py -q
```

### Stage 4: Prepare container-facing entrypoints and build context

Objective: make Docker build inputs and runtime entrypoints obvious.

Concrete moves:

- Ensure the Docker build context excludes local state, caches, and ignored tooling artifacts.
- Keep entrypoints explicit: Dagster via `src.definitions`, ML bridge via `scripts/ml_integration_api.py`, local stack via `scripts/local/start-local-stack.ps1`.
- Avoid hidden import-time path rewrites in new code.

Primary file anchors:

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `scripts/local/start-local-stack.ps1`

Validation:

```powershell
docker compose config
```

### Stage 5: Retire compatibility surfaces only after import audits

Objective: remove wrappers only when runtime and tests no longer depend on them.

Concrete moves:

- Audit imports of `ml_integration_api.py` and `energy_ml/ml_integration_api.py`.
- Keep wrappers until callers are migrated and covered by focused tests.
- Remove the wrapper with the smaller live dependency surface first.

Primary file anchors:

- `ml_integration_api.py`
- `energy_ml/ml_integration_api.py`
- `tests/unit/test_ml_integration_surface.py`
- `tests/unit/test_tariff_and_root_ml_integration_surfaces.py`

Validation:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_ml_integration_surface.py tests\unit\test_tariff_and_root_ml_integration_surfaces.py -q
```

## Immediate Next Slice

The next implementation slice after this document should stay inside `src/assets/core/client_state.py` and `src/data_pipeline/` unless a focused import audit proves a higher-value script or wrapper cleanup can land safely with a smaller blast radius.

## Success Criteria

- `src/assets/core/` stays orchestration-oriented.
- `src/data_pipeline/` becomes the obvious home for reusable Dagster-adjacent helpers.
- `scripts/` trends toward entrypoint wrappers instead of library code.
- `energy_ml/` remains a deliberate domain/runtime package rather than a catch-all duplicate backend root.
- Docker entrypoints and build context stay explicit and small.