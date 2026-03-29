import test from 'node:test'
import assert from 'node:assert/strict'

import { assessDagsterScheduleRowPolicy } from '../../dashboard/server/utils/dagster-schedule-policy.ts'

test('Dagster schedule sell row is vetoed during Stage 2 silence window', () => {
  const result = assessDagsterScheduleRowPolicy(
    {
      hour_offset: 10,
      action: 'SELL',
      action_kw: 18,
      soc_before_kwh: 80,
    },
    {
      config: {
        battery_capacity_kwh: 100,
        battery_soc_min: 0.15,
        battery_efficiency: 0.95,
        connected_power_kw: 75,
        market_regime_override: 'market_premium',
        timezone: 'Europe/Kiev',
      },
      batteryCapacityKwh: 100,
      scheduleStartUtc: '2026-03-29T00:00:00.000Z',
    },
  )

  assert.equal(result.requestedAction, 'SELL')
  assert.equal(result.policyCompliance.market_regime, 'market_premium')
  assert.equal(result.policyCompliance.adjusted_action, 'HOLD')
  assert.equal(result.policyCompliance.veto_applied, true)
  assert.ok(result.policyCompliance.rule_hits.includes('window_of_silence_export_veto'))
})