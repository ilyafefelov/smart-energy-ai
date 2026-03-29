import assert from 'node:assert/strict'
import test from 'node:test'

import {
  DECISION_SNAPSHOT_VERSION,
  buildDecisionSnapshot,
  buildOptimizationExecutionKey,
  reconcileOptimizationHistoryEntry,
} from '../../dashboard/server/utils/optimization-history.ts'

function buildHistoryRow(overrides = {}) {
  return {
    execution_key: 'exec_test',
    command_id: 'cmd_test',
    schedule_id: null,
    tenant_id: 'tenant-alpha',
    execution_source: 'simulation',
    timestamp: '2026-03-07T10:00:00.000Z',
    predicted_action: 0,
    actual_action: null,
    cost_baseline: null,
    cost_rl: null,
    price_uah_kwh: 8.5,
    duration_minutes: 30,
    energy_kwh: 1.25,
    economics_method: 'tariff_interval',
    economics_version: 'v2',
    fallback_reason: null,
    price_source: 'prices_current',
    tariff_window: 'offpeak',
    interval_start: '2026-03-07T10:00:00.000Z',
    interval_end: '2026-03-07T11:00:00.000Z',
    battery_soc_start: 62,
    battery_soc_end: null,
    solar_actual: null,
    load_actual: null,
    decision_source: 'manual_override',
    execution_status: 'scheduled',
    event_type: 'scheduled_intent',
    mode_from: null,
    mode_to: null,
    realized_revenue_uah: null,
    realized_cost_uah: null,
    realized_net_uah: null,
    decision_snapshot: null,
    is_reconciled: false,
    reconciled_at: null,
    reconciliation_note: null,
    ...overrides,
  }
}

test('buildDecisionSnapshot creates the versioned contract and keeps unavailable runtime fields null', () => {
  const snapshot = buildDecisionSnapshot({
    tenant_id: 'tenant-alpha',
    timestamp: '2026-03-07T10:00:00Z',
    decision_source: 'manual_override',
    recommendation_source: 'manual_input',
    selected_action: 'charge',
    selected_power_kw: 2.5,
    current_price_uah_kwh: 8.75,
    avg_price_uah_kwh: 9.5,
    battery_soc_percent: 64,
    battery_health_percent: 97.4,
    battery_temp_c: 26.1,
    optimization_strategy: 'balanced',
    load_profile_type: 'standard',
    previous_action: 'hold',
    provenance: {
      state_source: 'simulator_backed_telemetry',
      state_source_detail: 'api/battery/status',
      telemetry_classification: 'simulated_operational_telemetry',
      recommendation_contract_version: 'learned_policy_migration_v1',
    },
    contract: {
      version: 'learned_policy_migration_v1',
      normalized_action: {
        action: 'SELL',
        base_action: 'SELL',
        execution_command: 'discharge',
        power_kw: 3.5,
        power_source: 'stage2_market_policy',
        confidence: 0.91,
        confidence_percent: 91,
        strategy_adjusted: true,
        strategy_adjustment_notes: ['Silence-window export veto applied for 10:00-16:00.'],
      },
      compliance: {
        policy_version: 'stage2_market_policy_v1',
        market_regime: 'market_premium',
        reserve_floor_percent: 20,
        export_targeted: true,
        export_allowed: false,
        veto_applied: true,
        adjusted_action: 'HOLD',
        adjusted_power_kw: 0,
        rule_hits: ['window_of_silence_export_veto'],
        explanations: ['Silence-window export veto applied for 10:00-16:00.'],
      },
    },
  })

  assert.equal(snapshot.version, DECISION_SNAPSHOT_VERSION)
  assert.equal(snapshot.selected_action, 'BUY')
  assert.equal(snapshot.previous_action, 'HOLD')
  assert.equal(snapshot.estimated_load_kw, null)
  assert.equal(snapshot.estimated_solar_kw, null)
  assert.equal(snapshot.provenance.state_source, 'simulator_backed_telemetry')
  assert.equal(snapshot.contract.version, 'learned_policy_migration_v1')
  assert.equal(snapshot.contract.normalized_action?.execution_command, 'discharge')
  assert.equal(snapshot.contract.policy_compliance?.market_regime, 'market_premium')
  assert.equal(snapshot.contract.policy_compliance?.veto_applied, true)
})

test('buildOptimizationExecutionKey reconciles scheduled intents and later execution through schedule identity', () => {
  const scheduledKey = buildOptimizationExecutionKey({
    commandId: 'cmd_for_sched_123',
    scheduleId: 'sched_123',
    tenantId: 'tenant-alpha',
    timestamp: '2026-03-07T10:00:00.000Z',
    command: 'charge',
    powerKw: 2.5,
    durationMinutes: null,
    userId: 'dashboard',
    reason: 'Scheduled charge',
    source: 'memory_schedule_intent',
  })

  const executionKey = buildOptimizationExecutionKey({
    commandId: 'cmd_runtime_override',
    scheduleId: 'sched_123',
    tenantId: 'tenant-alpha',
    timestamp: '2026-03-07T11:00:00.000Z',
    command: 'charge',
    powerKw: 2.5,
    durationMinutes: 30,
    userId: 'dashboard',
    reason: 'Execute scheduled charge',
    source: 'simulation',
  })

  assert.equal(scheduledKey, executionKey)
})

test('reconcileOptimizationHistoryEntry upgrades a scheduled row into an executed learning row', () => {
  const scheduledSnapshot = buildDecisionSnapshot({
    tenant_id: 'tenant-alpha',
    timestamp: '2026-03-07T10:00:00Z',
    decision_source: 'manual_override',
    recommendation_source: 'manual_input',
    selected_action: 'charge',
    selected_power_kw: 2.5,
    battery_soc_percent: 62,
    optimization_strategy: 'balanced',
    load_profile_type: 'standard',
    provenance: {
      state_source: 'simulator_backed_telemetry',
      telemetry_classification: 'simulated_operational_telemetry',
    },
  })
  const executedSnapshot = buildDecisionSnapshot({
    tenant_id: 'tenant-alpha',
    timestamp: '2026-03-07T10:00:00Z',
    decision_source: 'manual_override',
    recommendation_source: 'manual_input',
    selected_action: 'charge',
    selected_power_kw: 2.5,
    current_price_uah_kwh: 8.75,
    avg_price_uah_kwh: 9.5,
    battery_soc_percent: 62,
    battery_health_percent: 97.4,
    battery_temp_c: 26.1,
    optimization_strategy: 'balanced',
    load_profile_type: 'standard',
    previous_action: 'hold',
    provenance: {
      state_source: 'simulator_backed_telemetry',
      state_source_detail: 'api/battery/status',
      telemetry_classification: 'simulated_operational_telemetry',
      recommendation_contract_version: 'learned_policy_migration_v1',
    },
    contract: {
      version: 'learned_policy_migration_v1',
      normalized_action: {
        action: 'HOLD',
        base_action: 'SELL',
        execution_command: 'hold',
        power_kw: 0,
        power_source: 'stage2_market_policy',
        confidence: 0.88,
        confidence_percent: 88,
        strategy_adjusted: true,
        strategy_adjustment_notes: ['Silence-window export veto applied for 10:00-16:00.'],
      },
      compliance: {
        policy_version: 'stage2_market_policy_v1',
        market_regime: 'market_premium',
        reserve_floor_percent: 20,
        export_targeted: true,
        export_allowed: false,
        veto_applied: true,
        adjusted_action: 'HOLD',
        adjusted_power_kw: 0,
        rule_hits: ['window_of_silence_export_veto'],
        explanations: ['Silence-window export veto applied for 10:00-16:00.'],
      },
    },
  })
  const executionKey = buildOptimizationExecutionKey({
    commandId: 'cmd_for_sched_456',
    scheduleId: 'sched_456',
    tenantId: 'tenant-alpha',
    timestamp: '2026-03-07T10:00:00.000Z',
    command: 'charge',
    powerKw: 2.5,
    durationMinutes: null,
    userId: 'dashboard',
    reason: 'Scheduled charge',
    source: 'memory_schedule_intent',
  })

  const existing = buildHistoryRow({
    execution_key: executionKey,
    command_id: 'cmd_for_sched_456',
    schedule_id: 'sched_456',
    execution_source: 'memory_schedule_intent',
    decision_snapshot: scheduledSnapshot,
  })
  const incoming = buildHistoryRow({
    execution_key: executionKey,
    command_id: 'cmd_runtime_override',
    schedule_id: 'sched_456',
    execution_source: 'simulation',
    actual_action: 0,
    execution_status: 'executed',
    event_type: 'auto_transition',
    battery_soc_end: 67,
    realized_cost_uah: 10,
    realized_net_uah: -10,
    decision_snapshot: executedSnapshot,
  })

  const reconciliation = reconcileOptimizationHistoryEntry(existing, incoming, '2026-03-07T11:05:00.000Z')

  assert.equal(reconciliation.reconciled, true)
  assert.match(reconciliation.reconciliationNote || '', /scheduled_intent_reconciled/)
  assert.equal(reconciliation.entry.execution_source, 'simulation')
  assert.equal(reconciliation.entry.execution_status, 'executed')
  assert.equal(reconciliation.entry.actual_action, 0)
  assert.equal(reconciliation.entry.realized_net_uah, -10)
  assert.equal(reconciliation.entry.is_reconciled, true)
  assert.equal(reconciliation.entry.reconciled_at, '2026-03-07T11:05:00.000Z')
  assert.equal(reconciliation.entry.decision_snapshot.battery_temp_c, 26.1)
  assert.equal(reconciliation.entry.decision_snapshot.previous_action, 'HOLD')
  assert.equal(reconciliation.entry.decision_snapshot.contract.version, 'learned_policy_migration_v1')
  assert.equal(reconciliation.entry.decision_snapshot.contract.normalized_action?.power_source, 'stage2_market_policy')
  assert.equal(reconciliation.entry.decision_snapshot.contract.policy_compliance?.veto_applied, true)
})