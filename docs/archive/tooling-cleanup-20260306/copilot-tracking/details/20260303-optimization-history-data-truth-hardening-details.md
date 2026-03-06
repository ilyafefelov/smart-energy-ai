<!-- markdownlint-disable-file -->

# Task Details: Optimization History Data Truth Hardening

## Research Reference

**Source Research**: #file:../research/20260303-optimization-history-data-truth-hardening-research.md

## Phase 1: Canonical Write Contract

### Task 1.1: Harden optimization_history write semantics

Define an idempotent and atomic persistence contract for `optimization_history` so command retries and dual execution paths do not create inconsistent economics rows.

- **Files**:
  - `dashboard/server/utils/optimization-history.ts` - Add deterministic write key strategy and `INSERT ... ON CONFLICT` semantics.
  - `dashboard/server/api/control/execute.post.ts` - Attach stable command execution identifiers and pass contract-complete payloads.
  - `src/models.py` - Confirm ORM schema compatibility with enforced uniqueness/index requirements.
- **Success**:
  - Writes are idempotent for repeated execution attempts.
  - SQL operations remain parameterized and safe.
  - Row-level insert outcomes are observable (success/failure counters or structured logs).
- **Research References**:
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 11-14) - Existing write path and persistence helper behavior.
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 45-52) - PostgreSQL `INSERT ... ON CONFLICT` and parameterization guidance.
  - #githubRepo:"brianc/node-postgres parameterized query pool" - Safe pooling and query pattern alignment.
- **Dependencies**:
  - PostgreSQL role with permissions to create index/constraints where required.
  - Task owner access to control execution API paths.

### Task 1.2: Expand canonical writes to all execution pathways

Ensure non-dashboard execution routes (Python controller results, scheduled commands, and fallback history sources) feed the same canonical economics table.

- **Files**:
  - `dashboard/server/api/control/schedule.post.ts` - Persist scheduled command intent or execution linkage metadata.
  - `dashboard/server/api/control/history.get.ts` - Normalize Python/in-memory history mapping to shared execution identifiers.
  - `dashboard/server/api/control/execute.post.ts` - Complete parity mapping for both `source=python_controller` and `source=simulation`.
- **Success**:
  - Command lineage is traceable across schedule, execution, and history APIs.
  - Canonical table receives entries regardless of execution source.
- **Research References**:
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 16-20) - Current fallback behavior in control history.
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 84-98) - Current command-to-row mapping example.
- **Dependencies**:
  - Task 1.1 completion.
  - Stable command ID strategy shared between scheduling and execution APIs.

## Phase 2: Canonical Economics Computation

### Task 2.1: Replace heuristic baseline/optimized cost math with canonical interval inputs

Shift economics computation from fixed multipliers to deterministic tariff and measured execution intervals while preserving current response contracts.

- **Files**:
  - `dashboard/server/api/control/execute.post.ts` - Replace `optimizationMultiplier` heuristic with explicit pricing interval logic.
  - `dashboard/server/api/prices/current.ts` - Expose required interval/time-window fields for economics calculation.
  - `dashboard/server/utils/optimization-history.ts` - Store source fields required for reproducible economics recomputation.
- **Success**:
  - `cost_baseline` and `cost_rl` are reproducible from persisted price/interval data.
  - Heuristic-only fallback path is isolated and explicitly marked.
- **Research References**:
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 12-14) - Heuristic math currently in write path.
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 27-28) - Current prices source and fallback behavior.
  - #fetch:https://node-postgres.com/features/queries - Parameterized query and type handling constraints.
- **Dependencies**:
  - Phase 1 completion.
  - Availability of reliable price values for each persisted command window.

### Task 2.2: Implement reconciliation/backfill for recent economics history

Create a deterministic repair process that backfills or recomputes recent rows when canonical data becomes available or corrections are needed.

- **Files**:
  - `scripts/reconcile_optimization_history.py` - Backfill/recompute utility for a bounded window (for example, last 7-30 days).
  - `dashboard/server/api/history.ts` - Add source metadata fields for reconciliation provenance if backfilled rows are present.
  - `dashboard/server/api/metrics.ts` - Ensure aggregate calculations remain consistent after reconciliation runs.
- **Success**:
  - Recent history can be recomputed without manual SQL edits.
  - Post-reconcile drift between history totals and metrics is within defined tolerance.
- **Research References**:
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 15-17) - Existing read hierarchy and fallback chain.
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 61-71) - Current fallback artifact dependencies.
- **Dependencies**:
  - Task 2.1 completion.
  - Access to canonical price and command intervals for target backfill window.

## Phase 3: Validation and Guardrails

### Task 3.1: Add source-truth validation tests and API assertions

Expand automated checks to validate provenance and economics consistency across APIs.

- **Files**:
  - `dashboard/scripts/api_smoke_test.ps1` - Add assertions for `source.economics_source` and basic value sanity.
  - `tests/` (new or existing API tests) - Add endpoint-level assertions for history/metrics consistency.
  - `dashboard/server/api/history.ts` - Surface explicit fallback reason codes for failed canonical reads.
- **Success**:
  - Automated smoke/test run fails on provenance regressions.
  - Canonical source coverage is visible in test output.
- **Research References**:
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 21-22) - Existing smoke harness coverage.
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 105-111) - Technical requirement to preserve contract while removing heuristic dependence.
- **Dependencies**:
  - Phase 2 completion.

### Task 3.2: Define operational success thresholds and rollback criteria

Document and enforce measurable thresholds for canonical-source reliability and acceptable fallback behavior.

- **Files**:
  - `dashboard/CODEX_MCP_GUIDE.md` or dedicated runbook doc - Add runbook section for economics-source health checks.
  - `.copilot-tracking/changes/20260303-optimization-history-data-truth-hardening-changes.md` - Track thresholds and validation outcomes.
- **Success**:
  - Clear SLO-style targets exist (for example, `% of requests using optimization_history_db`).
  - Rollback/fallback escalation path is documented.
- **Research References**:
  - #file:../research/20260303-optimization-history-data-truth-hardening-research.md (Lines 113-120) - Recommended approach and success criteria.
- **Dependencies**:
  - Task 3.1 completion.

## Dependencies

- PostgreSQL availability with create/index privileges in deployment targets.
- Stable API access to `prices/current`, `control/execute`, `history`, and `metrics`.
- Existing smoke harness (`dashboard/scripts/api_smoke_test.ps1`) as quality gate.

## Success Criteria

- `/api/history` uses `optimization_history_db` as normal-state economics source.
- `optimization_history` writes are idempotent and traceable across execution pathways.
- Fallback sources remain available but are not primary during healthy operation.
- Automated validation detects provenance regressions and aggregate drift.
