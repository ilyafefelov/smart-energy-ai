import { assessStage2MarketPolicy, inferReserveFloorPercent, inferSitePowerKw } from './market-policy'

export type DagsterSchedulePolicyInputRow = {
  hour?: unknown
  hour_offset?: unknown
  action?: unknown
  action_kw?: unknown
  soc_before_kwh?: unknown
}

export type DagsterSchedulePolicyContext = {
  config: Record<string, any> | null | undefined
  batteryCapacityKwh?: unknown
  scheduleStartUtc?: string | null
}

function toFiniteNumber(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}

export function normalizeClockHour(value: unknown, fallback = 0): number {
  const parsed = Math.floor(toFiniteNumber(value) ?? fallback)
  return ((parsed % 24) + 24) % 24
}

export function formatClockHour(hour: number): string {
  return `${String(normalizeClockHour(hour)).padStart(2, '0')}:00`
}

export function normalizeScheduleAction(action: unknown): 'BUY' | 'SELL' | 'HOLD' {
  const normalized = String(action || 'HOLD').trim().toUpperCase()
  if (normalized === 'DISCHARGE') return 'SELL'
  if (normalized === 'BUY' || normalized === 'SELL') return normalized
  return 'HOLD'
}

function resolveRowTimestamp(scheduleStartUtc: string | null | undefined, hourOffset: number): string | null {
  if (!scheduleStartUtc) return null
  const startDate = new Date(scheduleStartUtc)
  if (Number.isNaN(startDate.getTime())) return null
  return new Date(startDate.getTime() + (hourOffset * 60 * 60 * 1000)).toISOString()
}

function inferBatterySocPercent(socBeforeKwh: unknown, batteryCapacityKwh: unknown): number | null {
  const socBefore = toFiniteNumber(socBeforeKwh)
  const capacity = toFiniteNumber(batteryCapacityKwh)
  if (socBefore == null || capacity == null || capacity <= 0) {
    return null
  }

  return clamp((socBefore / capacity) * 100, 0, 100)
}

export function assessDagsterScheduleRowPolicy(
  row: DagsterSchedulePolicyInputRow,
  context: DagsterSchedulePolicyContext,
) {
  const hourOffset = normalizeClockHour(row?.hour_offset ?? row?.hour ?? 0, 0)
  const requestedAction = normalizeScheduleAction(row?.action)
  const requestedPowerKw = Math.abs(toFiniteNumber(row?.action_kw) ?? 0)
  const config = context.config || null
  const batteryCapacityKwh = toFiniteNumber(context.batteryCapacityKwh ?? config?.battery_capacity_kwh)
  const batterySocPercent = inferBatterySocPercent(row?.soc_before_kwh, batteryCapacityKwh)
  const timestamp = resolveRowTimestamp(context.scheduleStartUtc, hourOffset)

  const policyCompliance = assessStage2MarketPolicy({
    action: requestedAction,
    powerKw: requestedPowerKw,
    batterySocPercent,
    batteryCapacityKwh,
    reserveFloorPercent: inferReserveFloorPercent(config),
    sitePowerKw: inferSitePowerKw(config),
    marketRegimeOverride: config?.market_regime_override,
    timestamp,
    timezone: String(config?.timezone || 'Europe/Kiev'),
    dispatchDurationHours: 1,
    dischargeEfficiency: config?.battery_efficiency,
    localHourOverride: hourOffset,
  })

  return {
    hourOffset,
    timestamp,
    requestedAction,
    requestedPowerKw,
    batterySocPercent,
    policyCompliance,
  }
}