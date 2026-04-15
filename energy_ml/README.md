# Energy ML Runtime Surface

This directory is the active Python package for the Smart Energy AI domain logic.
Use it for reusable optimization, simulation, control, ML integration, and
pipeline orchestration code. The active Dagster runtime for the repository now
lives under `src/`, and the canonical operator scripts live under `scripts/`.

## What Lives Here

- `PipelineOrchestrator` in `pipeline.py` coordinates tariff, battery, load,
  renewable, and recommendation logic.
- `control/` contains inverter-control integration and CLI-facing helpers.
- `simulator/` contains detailed battery physics models and simulation support.
- `mlops/` contains production-oriented physics and prediction helpers.
- `optimizer/` contains optimization strategy components used by the pipeline.
- `assets/` contains package-local asset helpers that are still shared by tests
  and compatibility surfaces.

## Package Layout

```text
energy_ml/
├── control/
├── simulator/
├── mlops/
├── optimizer/
├── assets/
├── pipeline.py                # PipelineOrchestrator
├── ml_integration.py          # Shared ML integration helpers
├── ml_integration_api.py      # Compatibility wrapper for scripts/ml_integration_api.py
├── user_config.py             # ConfigurationManager
└── README.md
```

## Focused Validation

Run the narrowest checks that match the slice you changed:

```bash
python -m pytest tests/unit/test_optimizer_and_pipeline_surfaces.py -q
python -m pytest tests/unit/test_battery_physics.py -q
python -m pytest tests/unit/test_control_script_surfaces.py -q
```

## Runtime Notes

- Use `src/definitions.py` for the current Dagster definitions.
- Use top-level `scripts/` for operational entrypoints invoked by the dashboard
  or local tooling.
- Keep new reusable Python logic in the top-level `energy_ml/` package rather
  than adding new code under nested compatibility directories.

## Legacy Compatibility Surface

`energy_ml/energy_ml/` is a narrow legacy compatibility package retained only
for older imports that still expect `defs` or legacy helpers. Do not add new
jobs, resources, or IO managers there.
