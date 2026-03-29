import assert from 'node:assert/strict'
import test from 'node:test'

import {
  assessStage2MarketPolicy,
  inferReserveFloorPercent,
  inferSitePowerKw,
} from '../../dashboard/server/utils/market-policy.ts'

test('silence-window policy veto converts export recommendation into hold', () => {
  const result = assessStage2MarketPolicy({
    action: 'SELL',
    powerKw: 4,
    batterySocPercent: 80,
    batteryCapacityKwh: 100,
    reserveFloorPercent: 20,
    sitePowerKw: 75,
    localHourOverride: 11,
    timezone: 'Europe/Kiev',
  })

  assert.equal(result.market_regime, 'market_premium')
  assert.equal(result.adjusted_action, 'HOLD')
  assert.equal(result.export_allowed, false)
  assert.equal(result.veto_applied, true)
  assert.deepEqual(result.rule_hits, ['window_of_silence_export_veto'])
})

test('remit deliverable-energy guard blocks discharge beyond available energy above reserve', () => {
  const result = assessStage2MarketPolicy({
    action: 'SELL',
    powerKw: 8,
    batterySocPercent: 25,
    batteryCapacityKwh: 40,
    reserveFloorPercent: 20,
    sitePowerKw: 40,
    localHourOverride: 18,
    timezone: 'Europe/Kiev',
  })

  assert.equal(result.market_regime, 'net_billing')
  assert.equal(result.adjusted_action, 'HOLD')
  assert.equal(result.export_allowed, false)
  assert.equal(result.remit_deliverable_energy_ok, false)
  assert.ok(result.rule_hits.includes('remit_insufficient_deliverable_energy'))
})

test('config helpers infer reserve floor and site power from common dashboard fields', () => {
  const reserveFloorPercent = inferReserveFloorPercent({
    battery_soc_min: 0.2,
  })
  const sitePowerKw = inferSitePowerKw({
    solar_capacity_kw: 48,
  })

  assert.equal(reserveFloorPercent, 20)
  assert.equal(sitePowerKw, 48)
})