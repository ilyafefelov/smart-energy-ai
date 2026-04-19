<!-- markdownlint-disable-file -->
# Release Changes: Supervisor-Facing Bronze/Silver/Gold Dagster ELT/ML Architecture

**Related Plan**: 20260419-supervisor-medallion-dagster-architecture-plan.instructions.md
**Implementation Date**: 2026-04-19

## Summary

Package the current Dagster runtime for diploma-supervisor presentation as a Bronze/Silver/Gold ELT/ML architecture using a supervisor-facing doc set, a medallion dataset manifest, a thin renderer, and reproducible Gold-layer summary outputs.

This release was later extended outside the original plan with a follow-up documentation slice because the user requested a fuller supervisor handoff package covering the full current API surface, the dataset model, and lineage or freshness operating guidance.

The release also received a small follow-up stabilization outside the original plan so the generated medallion preview now keys its timestamp from manifest state instead of the current wall clock, preventing no-op validation runs from creating timestamp-only churn.

## Changes

### Added

* docs/technical/DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md - Added the supervisor-facing Bronze/Silver/Gold narrative, Mermaid diagram, provenance framing, and deferred backend-layout note for the current Dagster runtime.
* artifacts/medallion/medallion_dataset_manifest.yaml - Added the canonical machine-readable medallion manifest that maps current Dagster datasets, storage surfaces, provenance classes, and experiment lanes.
* src/data_pipeline/medallion_catalog.py - Added the reusable medallion catalog owner that loads the manifest, inspects folder state and Dagster materializations, and renders catalog or scorecard payloads.
* scripts/render_medallion_catalog.py - Added the thin CLI wrapper that renders markdown or JSON artifacts from the canonical medallion manifest.
* tests/unit/test_medallion_catalog_module.py - Added focused tests for manifest loading, layer enrichment, scorecard summary assembly, and markdown or JSON rendering.
* data/results/medallion_preview.md - Generated a markdown preview from the medallion renderer as the Phase 1 validation artifact.
* docs/technical/BRONZE_SILVER_GOLD_DATASET_CATALOG.md - Generated the supervisor-facing dataset catalog with Bronze, Silver, and Gold sections, layer stats, and runtime-derived storage or materialization snapshots.
* artifacts/medallion/gold_experiment_summary.json - Generated the Gold summary artifact with fleet, case-study, optimizer, and business-metric evidence for the explicit `client_001_kyiv_mall` slice.
* docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md - Generated the supervisor-facing experiments scorecard with benchmark, MLflow, optimizer, business-metric, fleet, and case-study evidence from persisted Dagster surfaces.
* docs/API_REFERENCE.md - Added a consolidated API reference outside the original plan because the user requested the full current dashboard and backend API surface as part of the supervisor package.
* docs/technical/DATASET_MODEL_REFERENCE.md - Added a supervisor-facing dataset model reference outside the original plan because the user requested an explicit Bronze, Silver, Gold, and multi-tenant contract guide.
* docs/technical/DATASET_LINEAGE_AND_FRESHNESS_SLA.md - Added a lineage, freshness, fallback, and enforcement guide outside the original plan because the user requested fuller operational documentation for the dataset package.
* docs/technical/SUPERVISOR_PRESENTATION_APPENDIX.md - Added a presentation-outline and thesis-appendix packaging guide outside the original plan because the user requested a tighter supervisor-facing handoff artifact.

### Modified

* docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md - Extended the existing runtime dependency map with an explicit logical medallion-overlay section that links to the new supervisor architecture artifacts.
* docs/technical/DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md - Added explicit fleet-wide and case-study evidence sections that tag the current package metrics as simulated, real, or fallback-derived.
* docs/technical/BRONZE_SILVER_GOLD_DATASET_CATALOG.md - Regenerated the catalog with an explicit case-study tenant selection so the fleet and case-study slices match the Gold summary artifact.
* src/data_pipeline/medallion_catalog.py - Aligned the Gold summary and experiments renderer with persisted benchmark schemas and added MLflow plus model-artifact status reporting for honest supervisor evidence.
* artifacts/medallion/gold_experiment_summary.json - Refreshed the Gold summary from persisted `data/dagster_home` benchmark, MLflow, optimizer, and model-training surfaces so skipped candidates and empty model-artifact lanes are explicit.
* docs/technical/README.md - Added a supervisor medallion package section and refreshed the technical docs index so the new artifacts are discoverable with explicit deferred-scope framing.
* docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md - Expanded the logical medallion overlay cross-links to the generated dataset catalog and experiments scorecard for the final handoff slice.
* artifacts/medallion/medallion_dataset_manifest.yaml - Extended the medallion manifest artifact outputs to publish the follow-up API, dataset model, and lineage or freshness docs requested after the original plan landed.
* docs/README.md - Surfaced the new API reference and supervisor dataset docs in the main docs index so the extended package is discoverable outside the technical subfolder.
* docs/technical/README.md - Extended the technical docs index again to include the new dataset model and lineage or freshness references in the supervisor package section.
* data/results/medallion_preview.md - Regenerated the medallion preview after extending the manifest artifact outputs during the follow-up documentation slice.
* docs/API_REFERENCE.md - Extended the API reference with representative request and response payload examples for configuration, Dagster recommendation and schedule, ML recommendation, control execution, and battery simulator flows.
* artifacts/medallion/medallion_dataset_manifest.yaml - Extended the manifest again to publish the new supervisor presentation appendix as part of the canonical package metadata.
* docs/technical/README.md - Added the supervisor presentation appendix to the technical docs index and supervisor package section.
* docs/README.md - Added main-index discoverability for the supervisor presentation appendix.
* data/results/medallion_preview.md - Regenerated the medallion preview after adding the supervisor presentation appendix to the manifest outputs.
* src/data_pipeline/medallion_catalog.py - Stabilized generated artifact timestamps outside the original plan by deriving `generated_at_utc` from the manifest file modification time so re-renders do not create timestamp-only preview churn.
* tests/unit/test_medallion_catalog_module.py - Added focused coverage outside the original plan to verify the catalog payload uses the manifest's stored modification timestamp on Windows.
* data/results/medallion_preview.md - Regenerated the medallion preview once more after the renderer stabilization so the tracked preview reflects the manifest-derived timestamp.

### Removed

* None yet.

## Release Summary

**Total Files Affected**: 19

### Files Created (13)

* docs/technical/DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md - Supervisor-facing Bronze/Silver/Gold narrative for the active Dagster runtime.
* artifacts/medallion/medallion_dataset_manifest.yaml - Canonical medallion manifest mapping datasets, provenance, and experiment lanes.
* src/data_pipeline/medallion_catalog.py - Shared medallion artifact owner and renderer logic.
* scripts/render_medallion_catalog.py - Thin CLI entrypoint for regenerating medallion artifacts.
* tests/unit/test_medallion_catalog_module.py - Focused coverage for the medallion catalog module and renderers.
* data/results/medallion_preview.md - Generated preview artifact for the medallion package.
* docs/technical/BRONZE_SILVER_GOLD_DATASET_CATALOG.md - Generated dataset catalog with layer, fleet, and case-study evidence.
* artifacts/medallion/gold_experiment_summary.json - Generated Gold summary JSON for benchmark, optimizer, and business-metric evidence.
* docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md - Generated experiments and results scorecard for supervisor-facing review.
* docs/API_REFERENCE.md - Consolidated API inventory and contract guide for the current dashboard and backend surface.
* docs/technical/DATASET_MODEL_REFERENCE.md - Supervisor-facing dataset model reference for Bronze, Silver, Gold, and multi-tenant surfaces.
* docs/technical/DATASET_LINEAGE_AND_FRESHNESS_SLA.md - Supervisor-facing lineage, freshness, fallback, and enforcement guide.
* docs/technical/SUPERVISOR_PRESENTATION_APPENDIX.md - Supervisor-facing presentation-outline and thesis-appendix packaging guide.

### Files Modified (6)

* docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md - Added logical medallion overlay guidance and final cross-links to the generated artifacts.
* docs/technical/DAGSTER_BRONZE_SILVER_GOLD_SUPERVISOR_ARCHITECTURE.md - Extended the narrative with explicit fleet, case-study, provenance, and deferral framing.
* docs/technical/README.md - Added discoverability links and scope guardrails for the supervisor medallion package, then extended it again with the follow-up dataset-model and lineage docs.
* artifacts/medallion/medallion_dataset_manifest.yaml - Extended artifact outputs so the follow-up documentation slice is part of the canonical supervisor package metadata.
* docs/README.md - Added main-index discoverability for the API and supervisor dataset docs.
* data/results/medallion_preview.md - Regenerated the preview after the follow-up manifest extension.

### Files Removed (0)

* None.

### Dependencies & Infrastructure

* **New Dependencies**: None.
* **Updated Dependencies**: None.
* **Infrastructure Changes**: Supervisor artifacts now reuse persisted Dagster evidence in `data/dagster_home` for benchmark, MLflow, optimizer, and model-training slices, and the follow-up documentation slice exposes the runtime API and data-contract surfaces without changing backend topology.
* **Configuration Updates**: No committed config changes; validation runs set `DAGSTER_HOME` to `data/dagster_home` when persisting final evidence.

### Deployment Notes

Regenerate the final Gold summary and scorecard after rerunning `benchmark_engines`, `optimization_schedule_contract_checks`, and the model-training materialization with `DAGSTER_HOME` pointed at `data/dagster_home` so the renderer can reuse the latest persisted Dagster evidence.