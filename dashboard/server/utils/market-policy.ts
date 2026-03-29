import { normalizeRecommendationAction } from './recommendation-contract.ts'

export type Stage2MarketRegime = 'net_billing' | 'market_premium' | 'unclassified'
export type Stage2MarketRegimeOverride = 'auto' | 'net_billing' | 'market_premium'

export type Stage2PolicyRuleHit =
  | 'window_of_silence_export_veto'
  | 'reserve_floor_veto'
  | 'remit_insufficient_deliverable_energy'

export type Stage2MarketPolicyAssessment = {
  policy_version: 'stage2_market_policy_v1'
  market_regime: Stage2MarketRegime
  local_hour: number | null
  timezone: string | null
  reserve_floor_percent: number
  battery_soc_percent: number | null
  battery_capacity_kwh: number | null
  available_energy_above_reserve_kwh: number | null
  remit_deliverable_energy_kwh: number | null
  requested_discharge_energy_kwh: number | null
  export_targeted: boolean
  export_allowed: boolean
  remit_deliverable_energy_ok: boolean | null
  veto_applied: boolean
  adjusted_action: 'BUY' | 'SELL' | 'HOLD'
  adjusted_power_kw: number | null
  rule_hits: Stage2PolicyRuleHit[]
  explanations: string[]
  reasoning_suffix: string
}

type Stage2MarketPolicyInput = {
  action: unknown
  powerKw?: unknown
  batterySocPercent?: unknown
  batteryCapacityKwh?: unknown
  reserveFloorPercent?: unknown
  sitePowerKw?: unknown
  marketRegimeOverride?: unknown
  timestamp?: string | Date | null
  timezone?: string | null
  dispatchDurationHours?: unknown
  dischargeEfficiency?: unknown
  localHourOverride?: unknown
}

const DEFAULT_RESERVE_FLOOR_PERCENT = 15
const DEFAULT_DISCHARGE_EFFICIENCY = 0.95
const SILENCE_WINDOW_START_HOUR = 10
const SILENCE_WINDOW_END_HOUR = 16

function toFiniteNumber(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function roundNumber(value: number | null, digits = 3): number | null {
  if (value == null || !Number.isFinite(value)) return null
  return Number(value.toFixed(digits))
}

function normalizePercentCandidate(value: number | null): number | null {
  if (value == null) return null
  if (value >= 0 && value <= 1) {
    return value * 100
  }
  return value
}

function resolveLocalHour(timestamp: string | Date | null | undefined, timezone: string | null | undefined): number | null {
  if (!timestamp) return null

  const date = timestamp instanceof Date ? timestamp : new Date(timestamp)
  if (Number.isNaN(date.getTime())) {
    return null
  }

  try {
    const formatter = new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit',
      hour12: false,
      timeZone: timezone || 'UTC',
    })
    const hourPart = formatter.formatToParts(date).find((part) => part.type === 'hour')
    const hour = Number(hourPart?.value)
    return Number.isInteger(hour) ? hour : null
  } catch {
    const hour = date.getUTCHours()
    return Number.isInteger(hour) ? hour : null
  }
}

export function inferReserveFloorPercent(config: Record<string, any> | null | undefined, fallback = DEFAULT_RESERVE_FLOOR_PERCENT): number {
  const candidates = [
    config?.battery?.minSOC,
    config?.battery?.min_soc,
    config?.battery_soc_min,
    config?.battery_min_soc,
    config?.minSOC,
    config?.min_soc,
    config?.reserve_soc_percent,
  ]

  for (const candidate of candidates) {
    const normalized = normalizePercentCandidate(toFiniteNumber(candidate))
    if (normalized != null) {
      return clamp(normalized, 0, 95)
    }
  }

  return fallback
}

export function inferSitePowerKw(config: Record<string, any> | null | undefined): number | null {
  const candidates = [
    config?.system_power_kw,
    config?.site_power_kw,
    config?.connected_power_kw,
    config?.contracted_power_kw,
    config?.solar_capacity_kw,
    config?.pv_capacity_kw,
    config?.renewable_capacity_kw,
    config?.load_peak_kw,
  ]

  for (const candidate of candidates) {
    const numeric = toFiniteNumber(candidate)
    if (numeric != null && numeric > 0) {
      return numeric
    }
  }

  return null
}

export function normalizeMarketRegimeOverride(value: unknown): Stage2MarketRegimeOverride {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'net_billing' || normalized === 'net-billing') return 'net_billing'
  if (normalized === 'market_premium' || normalized === 'market-premium') return 'market_premium'
  return 'auto'
}

export function inferMarketRegime(sitePowerKw: unknown, override: unknown = 'auto'): Stage2MarketRegime {
  const normalizedOverride = normalizeMarketRegimeOverride(override)
  if (normalizedOverride !== 'auto') {
    return normalizedOverride
  }

  const numeric = toFiniteNumber(sitePowerKw)
  if (numeric == null || numeric <= 0) return 'unclassified'
  return numeric > 50 ? 'market_premium' : 'net_billing'
}

export function assessStage2MarketPolicy(input: Stage2MarketPolicyInput): Stage2MarketPolicyAssessment {
  const action = normalizeRecommendationAction(input.action)
  const powerKw = toFiniteNumber(input.powerKw)
  const batterySocPercent = toFiniteNumber(input.batterySocPercent)
  const batteryCapacityKwh = toFiniteNumber(input.batteryCapacityKwh)
  const reserveFloorPercent = clamp(
    normalizePercentCandidate(toFiniteNumber(input.reserveFloorPercent)) ?? DEFAULT_RESERVE_FLOOR_PERCENT,
    0,
    95,
  )
  const dispatchDurationHours = Math.max(0.25, toFiniteNumber(input.dispatchDurationHours) ?? 1)
  const dischargeEfficiency = clamp(toFiniteNumber(input.dischargeEfficiency) ?? DEFAULT_DISCHARGE_EFFICIENCY, 0.5, 1)
  const localHour = Number.isInteger(toFiniteNumber(input.localHourOverride))
    ? Number(toFiniteNumber(input.localHourOverride))
    : resolveLocalHour(input.timestamp, input.timezone)
  const marketRegime = inferMarketRegime(input.sitePowerKw, input.marketRegimeOverride)

  const availableEnergyAboveReserveKwh = batterySocPercent != null && batteryCapacityKwh != null
    ? Math.max(0, batteryCapacityKwh * ((batterySocPercent - reserveFloorPercent) / 100))
    : null
  const remitDeliverableEnergyKwh = availableEnergyAboveReserveKwh == null
    ? null
    : Math.max(0, availableEnergyAboveReserveKwh * dischargeEfficiency)
  const requestedDischargeEnergyKwh = action === 'SELL' && powerKw != null
    ? Math.max(0, powerKw * dispatchDurationHours)
    : null

  const ruleHits: Stage2PolicyRuleHit[] = []
  const explanations: string[] = []
  let adjustedAction: 'BUY' | 'SELL' | 'HOLD' = action
  let adjustedPowerKw = powerKw

  if (action === 'SELL') {
    if (localHour != null && localHour >= SILENCE_WINDOW_START_HOUR && localHour < SILENCE_WINDOW_END_HOUR) {
      adjustedAction = 'HOLD'
      adjustedPowerKw = 0
      ruleHits.push('window_of_silence_export_veto')
      explanations.push('Silence-window export veto applied for 10:00-16:00.')
    }

    if (batterySocPercent != null && batterySocPercent <= reserveFloorPercent) {
      adjustedAction = 'HOLD'
      adjustedPowerKw = 0
      ruleHits.push('reserve_floor_veto')
      explanations.push(`Reserve-floor guard blocked discharge at ${batterySocPercent.toFixed(1)}% SoC with a ${reserveFloorPercent.toFixed(1)}% reserve floor.`)
    }

    if (
      requestedDischargeEnergyKwh != null
      && remitDeliverableEnergyKwh != null
      && requestedDischargeEnergyKwh > remitDeliverableEnergyKwh + 1e-9
    ) {
      adjustedAction = 'HOLD'
      adjustedPowerKw = 0
      ruleHits.push('remit_insufficient_deliverable_energy')
      explanations.push(
        `REMIT guard blocked discharge because deliverable energy ${remitDeliverableEnergyKwh.toFixed(2)} kWh is below requested ${requestedDischargeEnergyKwh.toFixed(2)} kWh above reserve.`,
      )
    }
  }

  const vetoApplied = adjustedAction !== action || (adjustedPowerKw ?? null) !== (powerKw ?? null)

  return {
    policy_version: 'stage2_market_policy_v1',
    market_regime: marketRegime,
    local_hour: localHour,
    timezone: input.timezone || null,
    reserve_floor_percent: roundNumber(reserveFloorPercent, 2) ?? DEFAULT_RESERVE_FLOOR_PERCENT,
    battery_soc_percent: roundNumber(batterySocPercent, 3),
    battery_capacity_kwh: roundNumber(batteryCapacityKwh, 3),
    available_energy_above_reserve_kwh: roundNumber(availableEnergyAboveReserveKwh, 3),
    remit_deliverable_energy_kwh: roundNumber(remitDeliverableEnergyKwh, 3),
    requested_discharge_energy_kwh: roundNumber(requestedDischargeEnergyKwh, 3),
    export_targeted: action === 'SELL',
    export_allowed: adjustedAction === 'SELL',
    remit_deliverable_energy_ok:
      requestedDischargeEnergyKwh == null || remitDeliverableEnergyKwh == null
        ? null
        : requestedDischargeEnergyKwh <= remitDeliverableEnergyKwh + 1e-9,
    veto_applied: vetoApplied,
    adjusted_action: adjustedAction,
    adjusted_power_kw: adjustedAction === 'HOLD' ? 0 : roundNumber(adjustedPowerKw, 3),
    rule_hits: ruleHits,
    explanations,
    reasoning_suffix: explanations.length > 0 ? ` Compliance: ${explanations.join(' ')}` : '',
  }
}