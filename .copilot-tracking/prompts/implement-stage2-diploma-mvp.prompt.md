---
agent: agent
model: Claude Sonnet 4
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Stage 2 Diploma MVP

## Task Overview

Implement the remaining Stage 2 diploma MVP work against the new umbrella tracker while preserving the March 29 baseline that is already landed in the active runtime.

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260329-stage2-diploma-mvp-changes.md` in #file:../changes/ if it does not already exist.

### Step 2: Execute the Remaining Stage 2 Work

You WILL follow #file:../plans/20260329-stage2-diploma-mvp-plan.instructions.md task-by-task

You WILL read #file:../details/20260329-stage2-diploma-mvp-details.md before starting each remaining task

You WILL update #file:../changes/20260329-stage2-diploma-mvp-changes.md after every completed task and keep the backfilled March 29 baseline intact

You WILL preserve these boundaries while implementing:

- Keep `docs/Stage 2/plan.md` as the human-readable narrative plan.
- Treat the March 7 learned-policy tracker set as precursor context, not as the active Stage 2 umbrella plan.
- Reuse the active `dashboard/` runtime surfaces and `src/assets/core/optimization_schedule.py` instead of creating parallel Stage 2 code paths.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.

**CRITICAL**: If ${input:taskStop:false} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When all remaining phases are complete and checked off, you WILL do the following:

1. Summarize the final implementation using #file:../changes/20260329-stage2-diploma-mvp-changes.md
2. Provide links to these supporting artifacts
	- #file:../plans/20260329-stage2-diploma-mvp-plan.instructions.md
	- #file:../details/20260329-stage2-diploma-mvp-details.md
	- #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md
3. Attempt to delete #file:../prompts/implement-stage2-diploma-mvp.prompt.md once implementation is fully complete

## Success Criteria

- [ ] The Stage 2 changes tracking file exists and stays current.
- [ ] Remaining plan items are implemented against the active Stage 2 umbrella tracker.
- [ ] The March 29 Stage 2 baseline remains preserved in the changes log.
- [ ] The narrative Stage 2 plan and `.copilot-tracking` execution artifacts stay aligned.