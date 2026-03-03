<!-- markdownlint-disable-file -->

# Task Research Notes: battery-auto-mode-monetization-notifications

## Research Executed

### File Analysis

- `dashboard/server/api/battery/simulate.ts`
  - Auto/manual state is toggled here (`manualMode`, `autoOptimization`), but auto behavior is a local hour/SOC heuristic (`computeAutoPowerKw`) and not ML recommendation-driven.
  - Control state is module-global (not tenant-scoped), creating cross-tenant risk.
- `dashboard/stores/batteryPhysicsStore.ts`
  - Dashboard battery widget toggles auto/manual by posting `action: 'setAutoMode'` to `/api/battery/simulate`.
- `dashboard/app/components/Battery/InteractiveIllustration.vue`
  - UI toggle calls `batteryPhysicsStore.setAutoMode`; component currently uses inline feedback message, not global deduped toasts.
- `dashboard/app/pages/control.vue`
  - Separate control path toggles to auto by issuing `executeCommand('auto', 0)`; this is disconnected from `/api/battery/simulate` auto toggle.
  - Uses `useToast()` and many `toast.add` calls, no `id` dedup keys.
- `dashboard/server/api/control/execute.post.ts`
  - Persists optimization history rows with `predicted_action`, `actual_action`, `cost_baseline`, `cost_rl`, `energy_kwh`.
  - `auto` maps to idle action `4` and simulation path does not perform charge/discharge for `auto`.
- `dashboard/server/api/control/history.get.ts`
  - Backfills optimization_history rows from controller/memory history with `economics_method: 'history_backfill_stub'` and `fallback_reason: 'missing_economics_payload'`.
- `dashboard/server/api/control/schedule.post.ts`
  - Persists scheduled intent rows (`actual_action: null`, `economics_method: 'scheduled_intent'`) but no verified execution worker in dashboard API path.
- `dashboard/server/api/control/status.get.ts`
  - Fallback derives mode from recent command history (`activeCommand ? 'manual' : 'automatic'`) rather than explicit auto/manual state machine.
- `dashboard/server/utils/optimization-history.ts`
  - Defines and upserts `optimization_history` via `execution_key` (`ON CONFLICT (execution_key)`), includes tenant/economics fields.
- `dashboard/server/api/history.ts`
  - Aggregates `optimization_history` by date for baseline/optimized/savings and reconciliation metadata.
- `dashboard/server/api/metrics.ts`
  - Derives summary savings from `/api/history` with multiple fallbacks (PPO artifact and analytics cache).
- `dashboard/server/api/metrics/dashboard.ts`
  - Can override daily/monthly savings with `/api/ml/recommendation` estimated values, not necessarily realized execution.
- `dashboard/app/pages/index.vue`
  - Key charts are computed from stores; weekly savings trend is synthetic from trend factors, not true 7-day historical series.
- `dashboard/app/components/ML/RecommendationCard.vue`
  - Fetches recommendation on mount and manual refresh only (no periodic synchronization).
- `dashboard/app/components/ML/ForecastChart.vue`
  - Forecast chart derived from `pricesStore` only; does not include executed control mode/economic realization.
- `dashboard/server/utils/python-runner.js`
  - Expects array args (`args.join(' ')`), but control endpoints pass objects.
- `energy_ml/control/inverter_controller.py`
  - Python controller supports AUTO mode as mode flip (`_enable_auto_mode`), not explicit monetized auto-trade policy.
- `energy_ml/scripts/execute_control_command.py`, `energy_ml/scripts/get_control_status.py`
  - Present.
- Missing verified scripts referenced by control APIs:
  - `get_control_history.py`, `create_schedule.py`, `get_scheduled_commands.py`, `cancel_scheduled_command.py`.

### Code Search Results

- `setAutoMode|manualMode|autoOptimization|computeAutoPowerKw`
  - Found in `dashboard/server/api/battery/simulate.ts`, `dashboard/stores/batteryPhysicsStore.ts`, `dashboard/app/components/Battery/InteractiveIllustration.vue`.
- `executeCommand('auto', 0)|watch(manualMode)`
  - Found in `dashboard/app/pages/control.vue`.
- `persistOptimizationHistory|predicted_action|actual_action|cost_baseline|cost_rl`
  - Found in `dashboard/server/api/control/execute.post.ts`, `dashboard/server/api/control/history.get.ts`, `dashboard/server/api/control/schedule.post.ts`, `dashboard/server/utils/optimization-history.ts`.
- `FROM optimization_history|economics_source|fallback_reason_code`
  - Found in `dashboard/server/api/history.ts`, `dashboard/server/api/metrics.ts`.
- `useToast|toast.add`
  - Found in `dashboard/app/pages/control.vue`, `dashboard/app/components/ML/MonitoringDashboard.vue`, `dashboard/app/components/Renewable/EnergyConfig.vue`.
- `weeklySavingsSeries|factorsByTrend|projectTrajectory`
  - Found in `dashboard/app/pages/index.vue`.
- `/api/dagster/recommendation`
  - Found in `dashboard/app/stores/mlPipelineStore.ts`; not consumed by control execution endpoints.

### External Research

- #githubRepo:"nuxt/ui useToast deduplicated toasts id"
  - `useToast` implementation shows duplicate handling by `id` (`existingIndex` update with `_duplicate` increment) and toast queue limiting.
- #githubRepo:"vueuse/vueuse watchDebounced debounceFilter watchWithFilter"
  - `watchDebounced` wraps `watchWithFilter` + `debounceFilter(debounce, { maxWait })`, suitable for transition dedup/debounce hooks.
- #fetch:https://ui.nuxt.com/components/toast
  - Nuxt UI documents deduplicated toasts (`id`) and requires app wrapper (`UApp`/toaster config) for global toast behavior.
- #fetch:https://raw.githubusercontent.com/nuxt/ui/v4/src/runtime/composables/useToast.ts
  - Confirms queue + duplicate-by-id behavior in code.
- #fetch:https://vuejs.org/api/reactivity-core.html#watch
  - `watch` provides `(newValue, oldValue)` and cleanup, appropriate for state transition detection.
- #fetch:https://vueuse.org/shared/watchDebounced/
  - Debounced watcher options (`debounce`, `maxWait`) and watch option compatibility.
- #fetch:https://raw.githubusercontent.com/vueuse/vueuse/main/packages/shared/watchDebounced/index.ts
  - Confirms canonical implementation details.
- #fetch:https://www.postgresql.org/docs/current/sql-insert.html
  - `INSERT ... ON CONFLICT DO UPDATE` guarantees atomic upsert behavior under concurrency.

### Project Conventions

- Standards referenced: `AGENTS.md` (Beads-first workflow), `vscode-userdata:/.../vuejs3.instructions.md` (Vue Composition API/Pinia conventions).
- Instructions followed: Research-only mode constraints, no product code edits, created only `.copilot-tracking/research/20260303-battery-auto-mode-monetization-notifications-research.md`.

## Key Discoveries

### Project Structure

- There are two independent battery-control pathways in dashboard runtime:
  - Path A (widget path): `InteractiveIllustration` -> `batteryPhysicsStore` -> `/api/battery/simulate`.
  - Path B (control page path): `control.vue` -> `/api/control/execute|schedule|status|history`.
- These paths do not share one explicit mode state machine and do not consume one canonical recommendation stream.
- Economic persistence exists (`optimization_history`) and is reused by `/api/history` and `/api/metrics`, but rows are partly intent/stub/fallback-derived.

### Implementation Patterns

- Auto mode today is primarily a flag/heuristic path, not verified as recommendation-to-actuation pipeline:
  - `dashboard/server/api/battery/simulate.ts:71` (`computeAutoPowerKw`) uses hour windows and SOC thresholds.
  - `dashboard/server/api/battery/simulate.ts:21` to `dashboard/server/api/battery/simulate.ts:23` stores mode/command in module globals.
  - `dashboard/server/api/battery/simulate.ts:182` resets current to `0` when enabling auto.
- Control execution path monetization is canonicalized but not necessarily realized:
  - `dashboard/server/api/control/execute.post.ts:263` maps commands to actions; `auto` -> `4` (idle) at `dashboard/server/api/control/execute.post.ts:271`.
  - `dashboard/server/api/control/execute.post.ts:118` to `dashboard/server/api/control/execute.post.ts:136` simulation applies SOC delta only for charge/discharge.
  - `dashboard/server/api/control/execute.post.ts:488` to `dashboard/server/api/control/execute.post.ts:494` persists economics/energy.
- Scheduled flow currently records intent more than execution:
  - `dashboard/server/api/control/schedule.post.ts:201` sets `actual_action: null`.
  - `dashboard/server/api/control/schedule.post.ts:207` to `dashboard/server/api/control/schedule.post.ts:209` marks row as `scheduled_intent` fallback.
- Notifications exist but transition-specific dedup/debounce wiring is absent:
  - `dashboard/app/pages/control.vue:507` (`useToast`) with many `toast.add` calls.
  - No `toast.add({ id: ... })` usage found in app-level source.

### Complete Examples

```ts
// dashboard/server/api/battery/simulate.ts (verified behavior)
let powerCommand = 0
let manualMode = true
let autoOptimization = false

function computeAutoPowerKw(socPercent: number, spec: BatterySimSpec): number {
  const hour = new Date().getHours()
  const isOffPeak = hour >= 23 || hour < 7
  const isPeak = hour >= 8 && hour <= 22

  if (isOffPeak && socPercent < spec.socMaxPercent - 5) {
    return round(spec.maxChargePowerKw * 0.2, 3)
  }
  if (isPeak && socPercent > spec.socMinPercent + 10) {
    return round(-spec.maxDischargePowerKw * 0.15, 3)
  }
  return 0
}

// GET returns heuristic effective command; physical power is still live current-derived
const livePowerKw = round((voltage * current) / 1000, 3)
const effectivePowerCommand = manualMode ? powerCommand : computeAutoPowerKw(socPercent, spec)

// POST setAutoMode only flips flags and clears current
if (body.action === 'setAutoMode') {
  autoOptimization = body.enabled ?? true
  manualMode = !autoOptimization
  if (autoOptimization) {
    powerCommand = 0
    await updateBatteryState({ current: 0 }, tenant.id)
  }
}
```

```ts
// dashboard/server/api/control/execute.post.ts (verified persistence path)
function mapCommandToAction(command: string): number {
  switch (command) {
    case 'charge': return 0
    case 'discharge': return 1
    case 'hold': return 4
    case 'auto': return 4
    default: return 4
  }
}

const persistResult = await persistOptimizationHistory({
  execution_key: executionKey,
  predicted_action: mapCommandToAction(command.command),
  actual_action: mapCommandToAction(command.command),
  cost_baseline: economics.baselineCost,
  cost_rl: economics.optimizedCost,
  energy_kwh: energyKwh,
  economics_method: economics.economicsMethod,
})
```

### API and Schema Documentation

- Control and mode APIs
  - `GET/POST /api/battery/simulate` -> `dashboard/server/api/battery/simulate.ts`.
  - `POST /api/control/execute` -> `dashboard/server/api/control/execute.post.ts`.
  - `GET /api/control/status` -> `dashboard/server/api/control/status.get.ts`.
  - `GET /api/control/history` -> `dashboard/server/api/control/history.get.ts`.
  - `POST /api/control/schedule`, `GET /api/control/scheduled`, `DELETE /api/control/schedule/:id`.
- Earnings/history APIs
  - `GET /api/history` -> date aggregates over `optimization_history`.
  - `GET /api/metrics` -> merges `/api/history` and fallback artifacts.
  - `GET /api/metrics/dashboard` -> may override with ML estimated savings.
- Recommendation APIs
  - `GET /api/ml/recommendation` (Python bridge) and `GET /api/dagster/recommendation` (advisory schedule).
  - No verified control endpoint consumption of `/api/dagster/recommendation`.
- Persistence schema
  - `optimization_history` table creation/upsert in `dashboard/server/utils/optimization-history.ts`.
  - ORM representation in `src/models.py`.

### Configuration Examples

```sql
-- Existing persistence pattern (already in repo):
CREATE UNIQUE INDEX IF NOT EXISTS uq_optimization_history_execution_key
ON optimization_history(execution_key);

INSERT INTO optimization_history (...)
VALUES (...)
ON CONFLICT (execution_key)
DO UPDATE SET ...;
```

```ts
// Existing control runner contract mismatch area:
// dashboard/server/utils/python-runner.js
export async function execPython(scriptName, args = []) {
  const argsString = args.join(' ') // expects array
}

// Control endpoints currently pass object payloads, e.g.:
// dashboard/server/api/control/execute.post.ts
await execPython('execute_control_command.py', { command: 'charge', power_kw: '2' })
```

### Technical Requirements

1. Unify auto-mode semantics into one authoritative state machine shared by widget and control page paths.
2. Replace heuristic-only auto decisions with recommendation-backed execution policy (with explicit fallback policy marker).
3. Persist realized earnings at execution time (not only estimates), including signed cashflow and transition event metadata.
4. Distinguish intent rows from executed rows in `optimization_history` and expose this via `/api/history` and `/api/metrics`.
5. Add durable control execution log (or event table) for transition auditing and notification replay.
6. Wire notification preferences (`settings.notifications`) into transition emission logic.
7. Add debounce/dedup for transition toasts using deterministic IDs (per transition tuple and time window).
8. Make dashboard charts consume canonical realized series (history endpoint) instead of synthetic trend factors.

## Recommended Approach

Implement a single transition-event ledger pattern centered on `optimization_history` as the execution truth source, then project UI/metrics from that source.

- Decision/execution flow:
  - Resolve recommendation source (`ml`/`dagster`/`heuristic`) and record `decision_source`.
  - Execute control action (or explicit no-op), capture start/end SOC, energy, price context.
  - Persist one canonical execution event row (idempotent by `execution_key`) with intent and realized fields.
- Earnings model:
  - Add explicit realized fields (`realized_revenue_uah`, `realized_cost_uah`, `realized_net_uah`, `realized_at`, `execution_status`, `event_type`, `mode_from`, `mode_to`).
  - Keep `cost_baseline`/`cost_rl` as model-comparison fields; do not treat them as sole realized ledger values.
- Notifications:
  - Add transition watcher on canonical mode/action stream and emit toasts with stable `id` keys (e.g., `mode:{tenant}:{from}->{to}:{bucket}`) to deduplicate.
  - Apply debounce (`watchDebounced`) to suppress poll-jitter duplicates.
- Charts/reactivity:
  - Bind mode and earnings charts to `/api/history` realized series and/or new `/api/control/transitions` feed.
  - Keep synthetic calculations only as explicit fallback mode with source labels.

## Implementation Guidance

- **Objectives**: Ensure auto mode executes measurable profitable actions (or explicit no-op), persist realized earnings historically, emit clean transition notifications, and keep dashboard charts reactive to canonical state.
- **Key Tasks**: Fix control runner argument contract; provide missing control scripts or remove dead Python paths; unify auto-mode state source; extend optimization_history schema and APIs for realized economics; add notification dedup/debounce; rewire dashboard charts to realized history.
- **Dependencies**: PostgreSQL `optimization_history` schema migration; dashboard control endpoints; app stores/pages (`batteryPhysicsStore`, `control.vue`, `index.vue`, `analytics.vue`); optional Nuxt UI toaster integration contract.
- **Success Criteria**: Auto toggle and control execution produce deterministic transition events with realized economics; `/api/history` and `/api/metrics` reflect realized values; transition toasts are deduped and preference-aware; charts update from canonical data without synthetic-only drift.
