## Plan: Stage 2 Diploma MVP

Build Stage 2 as a deterministic, compliance-aware arbitrage MVP on top of the active Dagster + Nuxt runtime, not as a separate greenfield MAS stack. Reuse the existing forecast, optimization, battery-state, and recommendation-contract surfaces; add a typed policy layer for Ukrainian market rules, dual-regime financial analytics, and an explainable reasoning timeline. Keep MAS as internal service boundaries and contracts for later evolution, while explicitly deferring RL, Modulus, ApolloPFN, and true 15-minute settlement optimization.

## Execution Status Snapshot

This document remains the human-readable Stage 2 narrative plan. The active execution tracker for the current workstream now lives in [.copilot-tracking/plans/20260329-stage2-diploma-mvp-plan.instructions.md](../../.copilot-tracking/plans/20260329-stage2-diploma-mvp-plan.instructions.md), with supporting [details](../../.copilot-tracking/details/20260329-stage2-diploma-mvp-details.md) and [changes](../../.copilot-tracking/changes/20260329-stage2-diploma-mvp-changes.md). The March 7 learned-policy migration tracker remains precursor work, not the umbrella tracker for this Stage 2 MVP slice.

- Completed: steps 1, 2, 3, 5, 6, and 8
- In progress: steps 7, 9, 10, 11, and 13
- Not started: steps 4 and 12

**Steps**
1. Phase 1: Freeze architecture boundaries and map the proposed research architecture onto the current repo. Reuse existing runtime surfaces instead of creating parallel trees. Map Forecaster to current Dagster market/weather/price assets, Physics Guard to LCOS and battery constraints, and Dispatch Commander to the normalized recommendation + compliance gate. This blocks all later steps.
2. Phase 1: Add one typed decision-contract layer and one market-rules/policy layer adjacent to the active runtime. Define the canonical Stage 2 entities: decision payload, battery constraint snapshot, market regime, compliance audit, and reasoning/rule-hit metadata. Hard rules belong here, not inside UI components or ad hoc Python heuristics. This depends on step 1.
3. Phase 1: Lock the regulatory semantics. Model the 50 kW split as a scenario/regime selector and comparative analytics boundary, not as live legal regime switching during operation. Model the “window of silence” as an export veto from 10:00 to 16:00 while still allowing charging, self-consumption support, and peak-shaving. Model REMIT as deliverable-energy validation after reserve and efficiency losses, not just raw SoC. This depends on step 2.
4. Phase 2: Extend the deterministic optimization core to become regime-aware. Update the active schedule asset to consume site regime, reserve floor, export permissions, and an LCOS/degradation input derived from the existing economics/physics surfaces. Replace the fixed degradation penalty placeholder with a configuration-driven calculation. This depends on step 3.
5. Phase 2: Add a post-optimizer compliance gate that acts as the MVP “Dispatch Commander.” It should translate schedule rows into canonical BUY/SELL/HOLD or charge/discharge/hold commands, attach rule hits and reasoning, apply vetoes, and emit a compliance audit hash or equivalent trace payload. This depends on step 4.
6. Phase 2: Keep rolling-horizon logic realistic for the current repo. Recompute an hourly 24-hour horizon on a periodic refresh using the current data resolution and contracts, with the architecture ready for later 15-minute buckets. Do not force true quarter-hour market optimization into the MVP before the data model supports it. This depends on step 5.
7. Phase 3: Add dual financial analytics for the diploma story and product differentiation. Compute and expose Saved Funds versus Earned Funds, BAU versus BESS delta, peak-shaving savings, and Net Billing versus Market Premium outputs from the same deterministic state. This can run in parallel with step 8 once step 4 is stable.
8. Phase 3: Add a decision and audit history surface. Persist state snapshot, chosen action, veto reason, estimated profit, estimated degradation, state source, and compliance metadata so the dashboard can show a reasoning timeline and later offline-training work can reuse the same records. This can run in parallel with step 7 after step 5.
9. Phase 4: Reuse the active dashboard instead of redesigning it. Extend the existing forecast, recommendation, and control-history surfaces to show: price curve, battery state, regime selector, compliance status, and a reasoning timeline with source, vetoes, and top factors. Prefer incremental changes to the control/history and existing ML components over a new complex frontend slice. This depends on steps 7 and 8.
10. Phase 4: Expose operator inputs needed for Stage 2 without introducing an LLM intent loop. Add structured settings for reserve floor, asset size, allowed export regime, blackout-risk mode, and tariff/regime assumptions. If desired, natural-language “intent” can be presented as preset strategy labels mapped to structured config, not as a live control authority. This depends on step 9.
11. Phase 5: Add focused validation. Cover policy rules, recommendation contract normalization, financial calculators, and schedule schema with narrow unit tests. Add one behavior test for each critical compliance path: silence-window export veto, REMIT insufficient-energy veto, reserve-floor hold, and dual-regime analytics split. This depends on steps 5, 7, and 8.
12. Phase 5: Validate the end-to-end demo path. Materialize the relevant Dagster assets, smoke the active dashboard APIs, and run manual Stage 2 scenarios: daytime solar surplus in silence window, evening high-price discharge, low-SoC REMIT block, and comparative site cases below and above the 50 kW boundary. This depends on step 11.
13. Phase 5: Update technical and diploma-facing documentation. Explain the Stage 2 architecture, regulatory assumptions, competitive positioning, and why RL/PPO, ApolloPFN, PatchTST, NVIDIA Modulus, real hardware control, and VPP aggregation remain post-MVP follow-on work. This depends on steps 9 through 12.

**Relevant files**
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/src/assets/core/optimization_schedule.py — active deterministic schedule asset with the current fixed `degradation_cost_per_kwh=0.01` placeholder and canonical schedule schema.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/src/physics/economics.py — existing LCOS and economic primitives to reuse instead of inventing a second battery-cost model.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/dashboard/server/utils/battery.ts — simulator-backed tenant battery state, which should remain the operational source of truth for Stage 2.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/dashboard/server/utils/recommendation-contract.ts — canonical normalized action/provenance surface to extend with Stage 2 reasoning and compliance metadata.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/dashboard/server/api/ml/recommendation.get.ts — current forecast/reasoning bridge and likely shortest path for Stage 2 recommendation payload enrichment.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/energy_ml/ml_integration.py — existing reasoning-generation and response-normalization surface that can back the deterministic commander output without introducing a separate live agent runtime.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/energy_ml/ml_integration_api.py — current Python bridge returning reasoning and decision-source metadata; align with the Stage 2 contract instead of branching another API path.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/dashboard/app/components/ML/ForecastChart.vue — existing price/action/reasoning visualization surface to reuse for the timeline.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/dashboard/app/components/ML/RecommendationCard.vue — current explanation card to extend with regime/compliance output.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/dashboard/pages/control.vue — existing command-history surface that can become the Stage 2 reasoning/audit timeline with minimal UI churn.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/.copilot-tracking/plans/20260307-learned-policy-migration-backlog-plan.instructions.md — existing migration plan that Stage 2 must align with by keeping learned-policy rollout out of the MVP critical path.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/docs/Stage 2/ШІ-арбітраж_ стратегія для МСБ.md — competitive and thesis framing for the SME niche.
- d:/OpenClaw-Backup/clawd/projects/smart-energy-ai/docs/Stage 2/Финансовая статистика и аукционы для клиентов (1).md — dual-regime financial model and Stage 2 economic framing.

**Verification**
1. Add narrow unit tests for the hard market-rule layer: silence-window export veto, REMIT deliverable-energy check, reserve-floor enforcement, and dual-regime routing.
2. Add contract tests around the normalized recommendation payload so action, provenance, and compliance metadata stay stable across Dagster and Python-backed paths.
3. Materialize the relevant Dagster assets for the touched slice, starting with the optimization schedule chain, and confirm the Stage 2 contract fields are present.
4. Smoke the active dashboard APIs that back recommendation, control history, and battery state, and verify the reasoning timeline uses one provenance vocabulary.
5. Run manual scenario demos for at least four cases: daytime export veto, evening price-spike discharge, REMIT low-energy block, and <50 kW versus >50 kW comparative economics.
6. Check docs and UI copy for truthfulness: no claims of live RL, autonomous market trading, or NVIDIA Modulus-based control in the MVP.

**Decisions**
- Included scope: deterministic optimization, Ukrainian compliance rules, dual-regime financial analytics, reasoning/audit UI, and simulator-backed operational state.
- Excluded scope: PPO or other learned-policy control, ApolloPFN/PatchTST production forecasting, NVIDIA Modulus integration, real Modbus/MQTT execution, VPP aggregation, and full 15-minute market-settlement optimization.
- Architectural stance: MAS appears as typed internal boundaries and future-ready contracts, not as multiple autonomous LLM agents in the live MVP control loop.
- Product stance: target SMEs in the 20–100 kW range, but treat the 50 kW boundary as a regulatory/financial regime split rather than a runtime legal toggle.
- Dashboard stance: extend the active `dashboard/` app only; do not revive legacy frontend surfaces.

**Further Considerations**
1. Refresh cadence recommendation: start with hourly price buckets and periodic recomputation on the existing schedule path; only move to quarter-hour resolution after the forecast, optimization schema, and validation data all support it.
2. Persistence recommendation: start by attaching Stage 2 reasoning/audit data to the existing dashboard or optimization-history persistence path instead of introducing a second storage subsystem.
3. Thesis framing recommendation: defend the MVP as an explainable, compliance-aware “AI arbitrage assistant” with deterministic control and future-ready MAS/RL interfaces, not as a finished autonomous trading robot.