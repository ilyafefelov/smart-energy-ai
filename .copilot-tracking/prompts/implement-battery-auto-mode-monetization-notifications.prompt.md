---
agent: agent
model: Claude Sonnet 4
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Battery Auto Mode Monetization and Notifications

## Task Overview

Implement the battery auto-mode hardening plan so auto decisions are recommendation-driven, realized earnings are persisted and historically visible, and users receive deduped corner notifications on meaningful mode/action transitions.

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260303-battery-auto-mode-monetization-notifications-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../AGENTS.md
You WILL systematically implement #file:../plans/20260303-battery-auto-mode-monetization-notifications-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:false} is true, you WILL stop after each Task for user review.

### Step 3: Validation

You WILL validate after each task with targeted checks:

1. Control correctness checks:
   - Verify auto-mode transition states are consistent between `InteractiveIllustration` and `control.vue`.
   - Verify recommendation source marker is emitted (`ml|dagster|heuristic`).

2. Earnings/history checks:
   - Verify `optimization_history` writes include realized earnings + transition metadata.
   - Verify `/api/history` and `/api/metrics` reconcile daily/monthly totals from realized ledger rows.

3. Notification/reactivity checks:
   - Verify transition toasts include deterministic `id` and do not spam under polling.
   - Verify dashboard charts/cards react to canonical realized history updates.

### Step 4: Cleanup

When ALL phases are checked off (`[x]`) and completed:

1. Provide a markdown link and concise summary of all changes from `.copilot-tracking/changes/20260303-battery-auto-mode-monetization-notifications-changes.md`
2. Provide markdown links to:
   - #file:../plans/20260303-battery-auto-mode-monetization-notifications-plan.instructions.md
   - #file:../details/20260303-battery-auto-mode-monetization-notifications-details.md
   - #file:../research/20260303-battery-auto-mode-monetization-notifications-research.md
3. Recommend cleanup/archive of tracking files after user approval.
4. Attempt to delete this prompt file after successful handoff.

## Success Criteria

- [ ] Changes tracking file created
- [ ] Plan tasks implemented with working code
- [ ] Realized earnings persistence and API reconciliation verified
- [ ] Transition notifications deduped/debounced and preference-gated
- [ ] Dashboard graphs react to canonical realized history data
