# Backend Stage 1: ML Bridge Consolidation

## Goal

Collapse duplicate ML bridge implementation code into one canonical module while preserving legacy invocation paths during migration.

## Canonical Runtime Surface

- `scripts/ml_integration_api.py` is the only implementation surface.

## Compatibility Surfaces

- `ml_integration_api.py` remains as a thin wrapper for legacy root invocations.
- `energy_ml/ml_integration_api.py` remains as a thin wrapper for legacy package-relative invocations.

## Keep / Change / Remove

- Keep `scripts/ml_integration_api.py` as the canonical bridge.
- Replace `ml_integration_api.py` implementation code with a wrapper that delegates to the canonical bridge.
- Keep `energy_ml/ml_integration_api.py` as a wrapper only; do not add new bridge logic there.
- Do not change dashboard code in this stage.

## Stage 1 Checklist

- Create and claim the Stage 1 tracking task in Beads.
- Replace the duplicate root bridge implementation with a compatibility wrapper.
- Preserve the public CLI entrypoint behavior for `python ml_integration_api.py`.
- Update focused tests to exercise the real root compatibility surface.
- Record the canonical bridge path in repo instructions.

## Focused Validation

Run the narrow validation set after the wrapper change:

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_ml_integration_surface.py -q
.venv\Scripts\python.exe -m pytest tests\unit\test_tariff_and_root_ml_integration_surfaces.py -q
```

Optional direct CLI smoke:

```powershell
.venv\Scripts\python.exe ml_integration_api.py --action get_status
```

## Exit Criteria

- `scripts/ml_integration_api.py` contains the only bridge implementation.
- Root and `energy_ml/` bridge files contain wrapper-only code.
- Focused unit tests pass.
- Repo instructions describe the canonical bridge path.