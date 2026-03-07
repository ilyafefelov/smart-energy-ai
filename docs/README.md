# Docs Index

This directory now keeps only active reference and runbook material in the main documentation surface. Historical plans, completion reports, phase status notes, and outdated implementation memory have been moved under `docs/archive/`.

## Active Docs

- `technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md` - current Dagster asset graph, job boundaries, and Mermaid diagram
- `technical/ML_TRADING_DECISION_FRAMEWORK.md` - current trading decision flow, data provenance, and history posture
- `technical/ARCHITECTURE_V2.md` - architecture overview worth keeping as background context
- `technical/DEPLOYMENT_GUIDE.md` - deployment guidance
- `technical/TEST_PIPELINE_GUIDE.md` - test and validation guidance
- `deployment/EC2_DAGSTER_T3_MICRO_RUNBOOK.md` - EC2 Dagster operations runbook
- `API_DOCUMENTATION_IMPORT_EXPORT.md` - API reference material
- `POSTGRES_SETUP.md` and `S3_PICKLE_IO_MANAGER.md` - supporting infrastructure notes

## Archived Docs

- `archive/root-cleanup-20260302/` - first root cleanup archive
- `archive/tooling-cleanup-20260306/` - generated tooling and dashboard report cleanup archive
- `archive/reports-cleanup-20260306/` - former `docs/reports/` bundle
- `archive/docs-cleanup-20260306/` - legacy phase plans, status notes, and outdated technical planning docs

If a file reads like a dated plan, completion report, or “ready to start” note for an earlier architecture snapshot, it belongs in `docs/archive/`, not in the active docs surface.