---
description: "Use when refreshing, extending, or synchronizing the supervisor medallion package, defense brief, thesis appendix export, presentation appendix, dataset catalog, scorecard, or manifest-backed deliverables."
name: "Supervisor Package Refresh"
argument-hint: "What changed in the supervisor package and which deliverables should be refreshed"
agent: "agent"
model: "GPT-5 (copilot)"
---
Refresh the supervisor-facing medallion package using the repo's existing deliverable workflow.

Inputs from the user should include as many of these as available:

- which supervisor deliverable changed or needs to be added
- whether the change is report-only, package-wide, or manifest-driven
- any specific runtime evidence, commits, tests, screenshots, or thesis-facing claims to include
- whether the defense brief, appendix export, or presentation appendix should also be refreshed

Follow these repo rules and sources:

- The supervisor package index lives in [docs/technical/README.md](../../docs/technical/README.md).
- The main report is [docs/technical/SUPERVISOR_MEDALLION_REPORT.md](../../docs/technical/SUPERVISOR_MEDALLION_REPORT.md).
- Companion deliverables include [docs/technical/SUPERVISOR_DEFENSE_BRIEF.md](../../docs/technical/SUPERVISOR_DEFENSE_BRIEF.md), [docs/technical/SUPERVISOR_THESIS_APPENDIX_EXPORT.md](../../docs/technical/SUPERVISOR_THESIS_APPENDIX_EXPORT.md), and [docs/technical/SUPERVISOR_PRESENTATION_APPENDIX.md](../../docs/technical/SUPERVISOR_PRESENTATION_APPENDIX.md).
- The canonical manifest is [artifacts/medallion/medallion_dataset_manifest.yaml](../../artifacts/medallion/medallion_dataset_manifest.yaml).
- Generated deliverables include [docs/technical/BRONZE_SILVER_GOLD_DATASET_CATALOG.md](../../docs/technical/BRONZE_SILVER_GOLD_DATASET_CATALOG.md), [docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md](../../docs/technical/EXPERIMENTS_AND_RESULTS_SCORECARD.md), [data/results/medallion_preview.md](../../data/results/medallion_preview.md), and [artifacts/medallion/gold_experiment_summary.json](../../artifacts/medallion/gold_experiment_summary.json).
- Keep claims honest about what is implemented now versus what remains deferred in the roadmap.

Expected workflow:

1. Determine whether the task is a single-document refresh or a linked package refresh.
2. Update the directly affected supervisor docs first.
3. Refresh cross-links in [docs/README.md](../../docs/README.md) and [docs/technical/README.md](../../docs/technical/README.md) when package composition changed.
4. If `artifacts/medallion/medallion_dataset_manifest.yaml` changed, rerender the manifest-backed outputs so generated docs and JSON remain coherent.
5. Use focused validation for the touched slice, such as rerendering artifacts and rerunning medallion renderer tests when relevant.
6. In the final response, list the concrete supervisor deliverable files that were created or updated.

If the user request is too vague to know which deliverable should change, ask only for the missing scope needed to choose the correct package slice.