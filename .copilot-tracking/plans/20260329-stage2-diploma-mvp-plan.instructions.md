---
applyTo: ".copilot-tracking/changes/20260329-stage2-diploma-mvp-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Stage 2 Diploma MVP

## Overview

Track the active Stage 2 diploma MVP workstream in one umbrella execution plan while keeping `docs/Stage 2/plan.md` as the human-readable narrative and the March 7 learned-policy tracker as precursor history.

## Current Status

- Completed: steps 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, and 11.
- In progress: step 13.
- Not started: step 12.

## Objectives

- Separate the active Stage 2 diploma MVP tracker from the March 7 learned-policy migration backlog.
- Preserve the March 29 completed Stage 2 slices as baseline context while making the remaining work explicit.
- Keep future implementation work targeted on the regime-aware optimizer, analytics, UI trace, validation, demo evidence, and final documentation slices.

## Research Summary

### Project Files

- docs/Stage 2/plan.md - Narrative Stage 2 plan that now needs to stay aligned with the execution tracker instead of pretending all steps are future work.
- dashboard/server/utils/market-policy.ts - Landed Stage 2 policy utility and compliance-rule vocabulary.
- dashboard/server/utils/optimization-history.ts - Landed `decision_snapshot_v1` and optimization-history reconciliation contract.
- dashboard/server/api/control/execute.post.ts - Executed-control surface already carrying policy-compliance and decision-snapshot data.
- dashboard/server/api/control/schedule.post.ts - Scheduled-control surface already carrying the same Stage 2 audit vocabulary.
- dashboard/server/api/control/history.get.ts - Active control-history API feeding the Stage 2 reasoning timeline.
- dashboard/server/api/history.ts - Canonical Stage 2 financial telemetry surface.
- dashboard/app/pages/analytics.vue - Active Stage 2 analytics UI consumer.
- dashboard/app/components/Battery/InteractiveIllustration.vue - Active control-history timeline UI with policy trace rendering.
- dashboard/app/components/Preferences/OptimizationProfile.vue - Active config-backed Stage 2 operator-input surface.
- src/assets/core/optimization_schedule.py - Remaining Step 4 optimizer gap with the fixed degradation placeholder.

### External References

- #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md - Verified March 29 status audit and implementation baseline for the active Stage 2 workstream.
- #file:../plans/20260307-learned-policy-migration-backlog-plan.instructions.md - Precursor learned-policy tracker that must remain separate from the current Stage 2 umbrella plan.
- #file:../details/20260307-decision-snapshot-history-contracts-details.md - Precursor details for the decision snapshot and optimization-history contract work that Stage 2 now builds on.
- #file:../changes/20260307-learned-policy-migration-backlog-changes.md - Precursor changes log showing why the March 7 tracker should not absorb March 29 Stage 2 work.

### Standards References

- #file:../../AGENTS.md - Beads-first workflow, runtime surface, and validation expectations.
- #file:../../.github/copilot-instructions.md - Repo guidance for `.copilot-tracking/` artifacts and iterative implementation work.

## Implementation Checklist

### [x] Phase 1: Lock the Completed Foundation Into the Stage 2 Baseline

- [x] Task 1.1: Freeze the active Stage 2 architecture on the current runtime surfaces (Step 1)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 19-38)

- [x] Task 1.2: Keep the typed policy and decision-contract layer as landed baseline work (Steps 2 and 3)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 19-38)

- [x] Task 1.3: Keep the post-optimizer compliance gate and hourly rolling-horizon assumption as landed baseline work (Steps 5 and 6)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 19-38)

- [x] Task 1.4: Keep decision snapshot persistence and optimization-history contracts as landed baseline work (Step 8)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 19-38)

### [x] Phase 2: Finish the Remaining Regime-Aware Optimizer and Financial Work

- [x] Task 2.1: Extend the deterministic optimizer with regime-aware inputs and config-driven degradation economics (Step 4, completed)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 63-80)

- [x] Task 2.2: Finish the dual-regime financial analytics story across API, UI, and narrative docs (Step 7, completed)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 82-98)

### [x] Phase 3: Finish the Dashboard Reasoning Timeline and Operator Controls

- [x] Task 3.1: Finish the Stage 2 reasoning timeline across schedule, execute, history, and UI surfaces (Step 9, completed)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 102-120)

- [x] Task 3.2: Finish Stage 2 operator-input propagation through the config-backed settings flow (Step 10, completed)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 122-140)

### [ ] Phase 4: Finish Validation, Demo Evidence, and Final Scope Framing

- [x] Task 4.1: Complete focused Stage 2 validation coverage for policy, history contracts, analytics, and schedule semantics (Step 11, completed)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 144-162)

- [ ] Task 4.2: Run the Stage 2 demo scenarios against the active runtime and capture evidence (Step 12, not started)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 164-180)

- [ ] Task 4.3: Keep Stage 2 docs truthful about the implemented MVP and deferred scope (Step 13, in progress)
  - Details: .copilot-tracking/details/20260329-stage2-diploma-mvp-details.md (Lines 184-200)

## Dependencies

- March 29 status-audit research in `.copilot-tracking/research/20260329-stage2-diploma-mvp-status-audit-research.md`
- March 7 learned-policy tracker set as precursor context rather than the active Stage 2 execution plan
- Active `dashboard/` runtime surfaces plus the deterministic optimizer asset in `src/assets/core/optimization_schedule.py`

## Success Criteria

- One authoritative Stage 2 umbrella tracker exists under `.copilot-tracking/` for the current diploma MVP workstream.
- The March 29 completed slices are preserved as baseline context instead of being lost inside the learned-policy backlog.
- Remaining Stage 2 work is explicit about what is in progress versus not started.
- `docs/Stage 2/plan.md` stays human-readable while pointing operators and implementers at the umbrella tracker.