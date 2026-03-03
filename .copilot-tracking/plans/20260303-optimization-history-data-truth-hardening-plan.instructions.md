---
applyTo: '.copilot-tracking/changes/20260303-optimization-history-data-truth-hardening-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Optimization History Data Truth Hardening

## Overview

Harden canonical economics persistence so `/api/history` and `/api/metrics` reliably use `optimization_history` as primary source with deterministic fallback behavior.

## Objectives

- Eliminate heuristic-only economics writes by enforcing a canonical, idempotent persistence contract for `optimization_history`.
- Ensure read-path provenance, reconciliation, and tests provide measurable confidence in backend-first economics.

## Research Summary

### Project Files

- `dashboard/server/api/control/execute.post.ts` - Current write entrypoint for command executions and economics persistence.
- `dashboard/server/utils/optimization-history.ts` - DB bootstrap and insert logic for canonical history rows.
- `dashboard/server/api/history.ts` - Source-priority read aggregation and economics provenance reporting.
- `dashboard/server/api/metrics.ts` - KPI rollups consuming history source and fallback artifacts.
- `src/models.py` - Canonical ORM table contract for `optimization_history`.

### External References

- #file:../research/20260303-optimization-history-data-truth-hardening-research.md - Verified evidence and selected approach for implementation.
- #githubRepo:"brianc/node-postgres parameterized query pool" - Pool/query safety patterns for robust persistence.
- #fetch:https://www.postgresql.org/docs/current/sql-insert.html - Atomic upsert semantics and conflict-handling guidance.

### Standards References

- #file:../../AGENTS.md - Beads-first workflow and session landing requirements.
- #file:../../dashboard/tsconfig.json - Dashboard TypeScript strictness and compilation expectations.
- #file:../../dashboard/CODEX_MCP_GUIDE.md - Dashboard operation and integration guidance reference.

## Implementation Checklist

### [x] Phase 1: Canonical Write Contract

- [x] Task 1.1: Harden optimization_history write semantics
  - Details: .copilot-tracking/details/20260303-optimization-history-data-truth-hardening-details.md (Lines 11-30)

- [x] Task 1.2: Expand canonical writes to all execution pathways
  - Details: .copilot-tracking/details/20260303-optimization-history-data-truth-hardening-details.md (Lines 31-47)

### [x] Phase 2: Canonical Economics Computation

- [x] Task 2.1: Replace heuristic baseline/optimized cost math with canonical interval inputs
  - Details: .copilot-tracking/details/20260303-optimization-history-data-truth-hardening-details.md (Lines 51-68)

- [x] Task 2.2: Implement reconciliation/backfill for recent economics history
  - Details: .copilot-tracking/details/20260303-optimization-history-data-truth-hardening-details.md (Lines 70-86)

### [x] Phase 3: Validation and Guardrails

- [x] Task 3.1: Add source-truth validation tests and API assertions
  - Details: .copilot-tracking/details/20260303-optimization-history-data-truth-hardening-details.md (Lines 90-105)

- [x] Task 3.2: Define operational success thresholds and rollback criteria
  - Details: .copilot-tracking/details/20260303-optimization-history-data-truth-hardening-details.md (Lines 107-120)

## Dependencies

- PostgreSQL connectivity and privileges for `CREATE DATABASE`/schema/index operations.
- Stable `prices/current` and control execution endpoints to support canonical economics derivation.
- Existing smoke infrastructure in `dashboard/scripts/api_smoke_test.ps1`.

## Success Criteria

- `optimization_history` becomes the normal-state economics source with idempotent writes across execution pathways.
- `/api/history` and `/api/metrics` preserve contract while reporting trustworthy source metadata.
- Reconciliation + tests detect and prevent provenance regressions.
