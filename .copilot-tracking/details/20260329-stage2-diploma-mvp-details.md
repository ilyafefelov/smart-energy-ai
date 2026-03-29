<!-- markdownlint-disable-file -->

# Task Details: Stage 2 Diploma MVP

## Research Reference

**Primary Research**: #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md

**Narrative Plan**: #file:../../docs/Stage 2/plan.md

**Precursor Trackers**:

- #file:../plans/20260307-learned-policy-migration-backlog-plan.instructions.md
- #file:../details/20260307-decision-snapshot-history-contracts-details.md
- #file:../changes/20260307-learned-policy-migration-backlog-changes.md

## Completed Baseline Context

### Completed Context 0.1: Policy, contracts, and history baseline already landed

Treat steps 1, 2, 3, 5, 6, and 8 as completed Stage 2 baseline work. New execution work must build on these runtime surfaces instead of creating parallel Stage 2 paths.

- **Files**:
  - dashboard/server/utils/market-policy.ts - Canonical Stage 2 market-regime and compliance utility with silence-window, reserve-floor, and REMIT checks.
  - dashboard/server/utils/recommendation-contract.ts - Shared action and provenance vocabulary used by control and recommendation surfaces.
  - dashboard/server/api/control/execute.post.ts - Executed-control flow already attaches policy compliance and decision snapshot data.
  - dashboard/server/api/control/schedule.post.ts - Scheduled-control flow already persists the same decision snapshot contract.
  - dashboard/server/utils/optimization-history.ts - Canonical `decision_snapshot_v1` and optimization-history reconciliation contract already exist.
  - dashboard/server/api/control/history.get.ts - Control-history API already surfaces decision snapshot data to the active reasoning timeline.
- **Success**:
  - Remaining work reuses the existing Stage 2 policy and history contracts.
  - The March 7 learned-policy migration tracker stays as precursor context only, not the active Stage 2 umbrella plan.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 15-24) - File-level evidence for the landed policy, history, analytics, and operator-input slices.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 50-54) - Current implementation pattern is to extend the active `dashboard/` runtime instead of branching a parallel architecture.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 83-94) - Canonical Stage 2 policy, analytics, audit, and operator-input contracts already in the repo.
- **Dependencies**:
  - Preserve the March 7 learned-policy tracker as prerequisite history.

### Completed Context 0.2: Analytics and operator-input baseline already landed

Treat the current `/api/history`, analytics UI, control timeline, and config-backed Stage 2 settings flow as the active baseline for the remaining work in steps 7, 9, 10, 11, 12, and 13.

- **Files**:
  - dashboard/server/api/history.ts - Canonical Stage 2 financial telemetry surface with `stage2_financials`.
  - dashboard/app/pages/analytics.vue - Active dashboard consumer for saved-versus-earned funds and regime labels.
  - dashboard/app/components/Battery/InteractiveIllustration.vue - Active control-history timeline with policy trace and decision-source rendering.
  - dashboard/app/components/Preferences/OptimizationProfile.vue - Active settings form for `connected_power_kw` and `market_regime_override`.
  - dashboard/server/api/config/current.get.ts - Returns persisted Stage 2 operator-input defaults and normalized override values.
  - dashboard/server/api/config/save.post.ts - Validates and stores the Stage 2 operator-input contract.
- **Success**:
  - Remaining work extends the canonical analytics, UI trace, and config-backed settings surfaces already in production paths.
  - Future implementation continues to treat `/api/history` as the Stage 2 financial source of truth.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 19-24) - File-level evidence for analytics, preferences, and focused policy-test coverage.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 54-54) - The Stage 2 implementation pattern centers on shared server utilities, canonical APIs, and the active preferences panel.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 86-94) - `/api/history` and config endpoints already define the live Stage 2 telemetry and operator-input contracts.
- **Dependencies**:
  - Keep analytics and settings work scoped to the existing `dashboard/` app.

## Phase 1: Finish the Regime-Aware Optimization and Financial Story

### Task 1.1: Extend the deterministic optimization asset with Stage 2 regime-aware inputs

Step 4 remains not started. The active deterministic optimizer in `src/assets/core/optimization_schedule.py` still hardcodes `degradation_cost_per_kwh=0.01`, so the next implementation slice must replace that placeholder with configuration-driven economics and explicit regime-aware inputs while keeping one optimizer path.

- **Files**:
  - src/assets/core/optimization_schedule.py - Replace the fixed degradation penalty placeholder and thread Stage 2 regime-aware inputs into the active schedule asset.
  - src/physics/economics.py - Reuse the existing LCOS and economics primitives instead of inventing a second degradation model.
  - dashboard/server/utils/market-policy.ts - Remain the canonical Stage 2 regime and compliance vocabulary rather than duplicating legal semantics inside the asset.
- **Success**:
  - The schedule asset no longer hardcodes the Stage 2 degradation penalty placeholder.
  - Reserve floor, export-permission/regime context, and degradation economics flow from the existing Stage 2 configuration and policy vocabulary.
  - Stage 2 continues to rely on one deterministic optimization backbone.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 15-22) - Existing policy and settings surfaces are already present and should feed the remaining optimizer work.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 52-54) - The current pattern is to extend the active runtime surfaces rather than branch new Stage 2 code paths.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 110-113) - The remaining gap is the umbrella tracker and explicit optimizer-core follow-through, not a new research cycle.
- **Dependencies**:
  - Completed policy and operator-input baseline from Completed Context 0.1 and 0.2.

### Task 1.2: Finish the dual-regime financial analytics story across API, UI, and narrative docs

Step 7 is in progress. `/api/history` and `dashboard/app/pages/analytics.vue` already expose the foundation, so the remaining work is to finish the diploma-facing and operator-facing comparative framing without creating a second analytics contract.

- **Files**:
  - dashboard/server/api/history.ts - Keep `stage2_financials` as the canonical financial summary contract.
  - dashboard/app/pages/analytics.vue - Finish the comparative presentation of Saved Funds, Earned Funds, and regime labels from the canonical API payload.
  - docs/Stage 2/plan.md - Keep the narrative plan accurate about analytics progress and remaining work.
- **Success**:
  - The Stage 2 financial story uses one regime vocabulary across API, UI, and documentation.
  - Saved Funds, Earned Funds, BAU delta, and comparative regime framing are credible enough for demo and diploma use.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 19-20) - `/api/history` already exposes the landed financial analytics baseline.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 86-88) - `stage2_financials` is the canonical dashboard financial telemetry contract.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 117-129) - The new Stage 2 tracker should keep analytics marked in progress instead of hiding the current baseline.
- **Dependencies**:
  - Task 1.1 must stabilize the remaining optimizer inputs before final financial sign-off.

## Phase 2: Finish the Dashboard Reasoning Timeline and Operator Controls

### Task 2.1: Finish the Stage 2 reasoning timeline across schedule, execute, history, and UI surfaces

Step 9 is in progress. Control history already carries `decision_snapshot` and the battery UI already renders policy trace fields, but the remaining work should make the end-to-end reasoning timeline consistent across the active control surfaces.

- **Files**:
  - dashboard/server/api/control/execute.post.ts - Keep executed decisions aligned with the canonical decision snapshot and policy-compliance contract.
  - dashboard/server/api/control/schedule.post.ts - Keep scheduled decisions aligned with the same contract vocabulary.
  - dashboard/server/api/control/history.get.ts - Preserve decision-trace and policy metadata for timeline consumers.
  - dashboard/app/components/Battery/InteractiveIllustration.vue - Finish the active policy-trace and decision-source presentation without introducing a parallel timeline UI.
- **Success**:
  - Scheduled and executed decisions surface one consistent provenance and compliance vocabulary.
  - Market regime, veto status, adjusted action, and decision source stay visible in the active control-history UI.
  - No second reasoning-timeline model is introduced outside the current control/history surfaces.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 17-18) - Decision snapshot and optimization-history reconciliation already exist as the canonical audit contract.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 32-35) - The completed March 29 slices already include decision snapshot/history and UI policy trace work.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 89-91) - `decision_snapshot_v1` is already wired into scheduled and executed control flows.
- **Dependencies**:
  - Completed baseline from Completed Context 0.1.

### Task 2.2: Finish Stage 2 operator-input propagation through the config-backed settings flow

Step 10 is in progress. The current settings form and config APIs already save `connected_power_kw` and `market_regime_override`, so the remaining work is to make sure all Stage 2 consumers read those values from the same config-backed path and that any still-missing inputs are explicitly scoped.

- **Files**:
  - dashboard/app/components/Preferences/OptimizationProfile.vue - Keep Stage 2 operator inputs in the active settings panel.
  - dashboard/server/api/config/current.get.ts - Return normalized operator-input defaults and saved values.
  - dashboard/server/api/config/save.post.ts - Validate and persist the canonical Stage 2 operator-input contract.
  - dashboard/server/utils/market-policy.ts - Keep policy regime inference aligned with saved configuration values.
  - dashboard/server/api/history.ts - Continue consuming the same operator-input contract when resolving regime-aware analytics.
- **Success**:
  - Connected power and regime override propagate from saved tenant config into policy, analytics, and remaining optimizer consumers.
  - Any additional step 10 inputs either land through the same config-backed flow or are explicitly deferred.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 21-22) - The active preferences panel already exposes the key Stage 2 operator inputs.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 58-79) - The saved config example already includes `connected_power_kw` and `market_regime_override`.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 92-94) - The config endpoints already define the live operator-input contract.
- **Dependencies**:
  - Completed baseline from Completed Context 0.2.

## Phase 3: Finish Focused Validation and Demo Evidence

### Task 3.1: Complete focused Stage 2 validation coverage

Step 11 is in progress. Policy tests and history-contract tests already exist, so the remaining work is to round out the validation matrix for recommendation contracts, optimizer semantics, financial analytics, and timeline behavior without reopening a broad integration program.

- **Files**:
  - tests/unit/stage2_market_policy_contract.test.mjs - Preserve the hard-rule suite for silence-window, reserve-floor, REMIT, and regime-override behavior.
  - tests/unit/decision_snapshot_history_contract.test.mjs - Preserve and extend the decision snapshot and optimization-history contract suite.
  - tests/test_dashboard_battery_control_regression.py - Keep control-history decision-trace behavior covered.
  - tests/test_dashboard_economics_api.py - Keep `/api/history` economics alignment covered.
  - src/assets/core/optimization_schedule.py - Remain the validation target for the remaining schedule-semantics work.
- **Success**:
  - Stage 2 keeps one focused validation matrix for policy, history contracts, financial analytics, and schedule semantics.
  - Remaining implementation work can be landed without relying on a single broad end-to-end test.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 23-24) - Focused policy-test coverage already exists.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 32-33) - The March 29 status audit confirms the completed Stage 2 slices that validation should now protect.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 124-129) - Success means the new tracker can guide the remaining work without overloading the March 7 backlog.
- **Dependencies**:
  - Phase 1 and Phase 2 tasks stable enough for final assertions.

### Task 3.2: Run the Stage 2 demo scenarios and capture evidence from the active runtime

Step 12 remains not started. Use the current Dagster plus dashboard runtime rather than creating a parallel demo harness. The required scenario set remains silence-window export veto, evening high-price discharge, low-SoC REMIT block, and below-versus-above 50 kW comparative economics.

- **Files**:
  - docs/Stage 2/plan.md - Summarize scenario coverage once the demo path is validated.
  - .copilot-tracking/changes/20260329-stage2-diploma-mvp-changes.md - Append scenario validation notes as the umbrella tracker advances.
  - src/assets/core/optimization_schedule.py - Materialization target for deterministic schedule behavior.
  - dashboard/server/api/history.ts - Canonical financial API surface to verify during comparative-regime demo runs.
- **Success**:
  - Each required Stage 2 scenario has repeatable evidence from the active runtime.
  - Demo outputs reuse the same compliance, provenance, and regime vocabulary already present in the plan and UI.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 110-113) - The remaining need is execution tracking and targeted follow-through, not a new planning branch.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 117-129) - Step 12 should stay explicitly not started until scenario evidence exists.
- **Dependencies**:
  - Task 3.1 completion.

## Phase 4: Close the Documentation and Diploma-Framing Gap

### Task 4.1: Keep Stage 2 docs truthful about the implemented MVP and deferred scope

Step 13 is in progress. Documentation should describe the deterministic compliance-aware MVP that already exists, keep the March 29 status visible, and explicitly defer post-MVP work such as RL, Modulus, ApolloPFN, PatchTST, real hardware control, and VPP aggregation.

- **Files**:
  - docs/Stage 2/plan.md - Human-readable narrative plan with a concise tracker pointer and current status snapshot.
  - docs/Stage 2/*.md - Diploma-facing framing and regulatory notes that must stay aligned with the implemented MVP.
  - .copilot-tracking/plans/20260329-stage2-diploma-mvp-plan.instructions.md - Umbrella execution tracker for the active workstream.
- **Success**:
  - Stage 2 docs no longer imply zero progress or overstate post-MVP capabilities.
  - The human-readable plan and `.copilot-tracking` execution artifacts stay aligned as implementation continues.
- **Research References**:
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 9-14) - The old state was a narrative plan without March 29 execution status.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 41-44) - Repo conventions require `.copilot-tracking/` to carry the execution artifacts.
  - #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md (Lines 110-129) - The goal is one authoritative Stage 2 tracker plus accurate human-readable status.
- **Dependencies**:
  - Task 1.2, Task 2.1, Task 2.2, and Task 3.2 or any landed subset sufficient to update docs truthfully.

## Dependencies

- The March 29 status-audit research in #file:../research/20260329-stage2-diploma-mvp-status-audit-research.md
- The March 7 learned-policy tracker set as precursor context, not as the active Stage 2 execution plan
- The active `dashboard/` runtime surfaces and the deterministic optimizer asset in `src/assets/core/optimization_schedule.py`

## Success Criteria

- The remaining Stage 2 work is tracked against one active umbrella plan instead of the March 7 learned-policy backlog.
- Completed March 29 Stage 2 slices stay recorded as baseline context while the remaining work stays explicit.
- Future implementation work can proceed against the remaining optimizer, analytics, UI, validation, demo, and documentation tasks without reopening architecture scope.