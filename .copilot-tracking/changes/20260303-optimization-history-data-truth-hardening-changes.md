<!-- markdownlint-disable-file -->
# Release Changes: Optimization History Data Truth Hardening

**Related Plan**: `.copilot-tracking/plans/20260303-optimization-history-data-truth-hardening-plan.instructions.md`
**Implementation Date**: 2026-03-03

## Summary

Implementing optimization history data-truth hardening across canonical write semantics, deterministic economics computation, reconciliation tooling, and provenance guardrails.

## Changes

### Added

- `scripts/reconcile_optimization_history.py` - Added deterministic bounded-window reconciliation utility to recompute canonical economics and mark reconciled rows.
- `tests/test_dashboard_economics_api.py` - Added endpoint-level assertions for history/metrics economics source alignment and canonical value sanity checks.

### Modified

- `.copilot-tracking/plans/20260303-optimization-history-data-truth-hardening-plan.instructions.md` - Marked all implementation phases and tasks complete after code validation.
- `dashboard/server/api/control/execute.post.ts` - Added stable command identifiers, source-aware execution-key mapping, and contract-complete persistence payloads for both python and simulation flows.
- `dashboard/server/api/control/schedule.post.ts` - Added schedule/command lineage IDs and persistence of scheduled intent metadata into canonical optimization history.
- `dashboard/server/api/control/history.get.ts` - Normalized python/memory history entries to shared command lineage and backfilled canonical stub rows for non-dashboard history sources.
- `dashboard/server/utils/optimization-history.ts` - Added deterministic execution key helper, expanded economics lineage schema, and atomic upsert semantics with persisted insert/update outcomes.
- `src/models.py` - Aligned `OptimizationHistory` ORM model with canonical write-contract fields, uniqueness key, lineage metadata, and reconciliation columns.
- `dashboard/server/api/prices/current.ts` - Exposed current interval boundaries and tariff-window metadata required for deterministic economics computation.
- `dashboard/server/api/history.ts` - Added reconciliation counters and explicit fallback reason codes in source metadata for canonical read observability.
- `dashboard/server/api/metrics.ts` - Propagated history fallback/reconciliation metadata to metrics source diagnostics for consistency checks.
- `dashboard/scripts/api_smoke_test.ps1` - Added strict provenance assertions, savings sanity checks, switched default local dashboard base URL to port 3600, and fixed economics-source extraction for PowerShell object compatibility.
- `dashboard/CODEX_MCP_GUIDE.md` - Documented economics-source SLO targets, validation commands, and rollback criteria/actions.

### Removed

- None.

## Release Summary

**Total Files Affected**: 12

### Files Created (2)

- `scripts/reconcile_optimization_history.py` - Bounded-window reconciliation utility for canonical economics recomputation.
- `tests/test_dashboard_economics_api.py` - Endpoint-level provenance and value-sanity checks.

### Files Modified (10)

- `.copilot-tracking/plans/20260303-optimization-history-data-truth-hardening-plan.instructions.md` - Implementation checklist completion updates.
- `dashboard/server/utils/optimization-history.ts` - Idempotent upsert contract, expanded schema, and persistence outcomes.
- `dashboard/server/api/control/execute.post.ts` - Deterministic command IDs, tariff-interval economics, and canonical persistence payload.
- `dashboard/server/api/control/schedule.post.ts` - Scheduled intent lineage and canonical persistence feed.
- `dashboard/server/api/control/history.get.ts` - Shared command lineage normalization and history backfill stubs.
- `dashboard/server/api/prices/current.ts` - Current interval and tariff window metadata surfaced for economics derivation.
- `dashboard/server/api/history.ts` - Reconciliation/fallback provenance fields added and DB config resolution aligned with canonical writer config.
- `dashboard/server/api/metrics.ts` - History provenance propagation for metrics consistency checks.
- `dashboard/scripts/api_smoke_test.ps1` - Canonical economics assertions and API sanity checks (port 3600 default) with resilient source extraction logic.
- `dashboard/CODEX_MCP_GUIDE.md` - Economics source operational SLO and rollback runbook.

### Files Removed (0)

- None.

### Dependencies & Infrastructure

- **New Dependencies**: None.
- **Updated Dependencies**: None.
- **Infrastructure Changes**: `optimization_history` schema now includes execution key, lineage fields, interval metadata, and reconciliation columns.
- **Configuration Updates**: Smoke test default dashboard URL updated to `http://127.0.0.1:3600` to match current runtime context.

### Deployment Notes

- Validation completed with smoke + pytest and canonical economics assertions now pass on port `3600` after restoring local PostgreSQL availability and aligning read/write DB config.
- **Outside original plan scope**: Additional runtime operational hardening was implemented under `smart-energy-ai-g9l` because canonical-source validation exposed environment-level DB unavailability (`ECONNREFUSED` on `localhost:5432`).
