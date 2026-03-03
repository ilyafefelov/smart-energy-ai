import { existsSync, readFileSync } from 'fs'
import { join } from 'path'
import { eventHandler } from 'h3'
import { getBatteryState } from '~/server/utils/battery'

type CommandRecord = {
  command?: string
  power_kw?: number
  duration_minutes?: number
  executed_at?: string
  timestamp?: string
}

function loadConfig() {
  const configPath = join(process.cwd(), '../energy_ml/configs/user_config.json')
  const defaults = {
    battery_capacity_kwh: 150,
    battery_efficiency: 0.95,
    battery_soc_min: 0.1,
    battery_soc_max: 0.95,
    battery_c_rate_charge: 0.5,
    battery_c_rate_discharge: 1.0,
    battery_cycles_max: 8000,
  }

  if (!existsSync(configPath)) {
    return defaults
  }

  try {
    const raw = JSON.parse(readFileSync(configPath, 'utf-8'))
    return {
      ...defaults,
      ...raw,
    }
  } catch {
    return defaults
  }
}

function deriveTodayTotals(history: CommandRecord[], usableCapacity: number) {
  const startOfDay = new Date()
  startOfDay.setHours(0, 0, 0, 0)

  let energyIn = 0
  let energyOut = 0

  for (const entry of history) {
    const ts = new Date(entry.executed_at || entry.timestamp || 0)
    if (!Number.isFinite(ts.getTime()) || ts < startOfDay) continue

    const power = Number(entry.power_kw || 0)
    const durationHours = Math.max(0, Number(entry.duration_minutes || 0) / 60)
    const throughput = Math.abs(power) * durationHours

    if (power > 0) {
      energyIn += throughput
    } else if (power < 0) {
      energyOut += throughput
    }
  }

  const totalThroughput = energyIn + energyOut
  const cycles = usableCapacity > 0 ? totalThroughput / (2 * usableCapacity) : 0

  return {
    energyIn,
    energyOut,
    cycles,
  }
}

export default eventHandler(async () => {
  const state = await getBatteryState()
  const config = loadConfig()

  const soc = Number(state?.soc ?? 50)
  const voltage = Number(state?.voltage ?? 400)
  const current = Number(state?.current ?? 0)
  const derivedPowerKw = Number(((voltage * current) / 1000).toFixed(3))

  const capacityKwh = Number(config.battery_capacity_kwh || state?.capacity || 150)
  const efficiency = Number(config.battery_efficiency || 0.95)
  const minSoc = Number(config.battery_soc_min || 0.1) * 100
  const maxSoc = Number(config.battery_soc_max || 0.95) * 100
  const chargeRateMax = Number(config.battery_c_rate_charge || 0.5) * capacityKwh
  const dischargeRateMax = Number(config.battery_c_rate_discharge || 1.0) * capacityKwh
  const cyclesMax = Number(config.battery_cycles_max || 8000)
  const cyclesDone = Number(state?.cycles || 0)

  const usableCapacity = capacityKwh * Math.max(0, (maxSoc - minSoc) / 100)
  const commandHistory = Array.isArray((globalThis as any).commandHistory)
    ? (globalThis as any).commandHistory as CommandRecord[]
    : []
  const today = deriveTodayTotals(commandHistory, usableCapacity)

  const losses = (today.energyIn + today.energyOut) * Math.max(0, 1 - efficiency)
  const energyStored = capacityKwh * (soc / 100)

  return {
    success: true,
    timestamp: new Date().toISOString(),
    source: 'battery_state_and_config',
    status: {
      soc: Number(soc.toFixed(2)),
      capacity_kwh: Number(capacityKwh.toFixed(2)),
      energy_stored: Number(energyStored.toFixed(2)),
      charging: derivedPowerKw > 0.1,
      power: derivedPowerKw,
      efficiency: Number(efficiency.toFixed(4)),
    },
    config: {
      min_soc: Number(minSoc.toFixed(2)),
      max_soc: Number(maxSoc.toFixed(2)),
      charge_rate_max: Number(chargeRateMax.toFixed(2)),
      discharge_rate_max: Number(dischargeRateMax.toFixed(2)),
      cycles_remaining: Math.max(0, Math.round(cyclesMax - cyclesDone)),
    },
    today: {
      cycles: Number(today.cycles.toFixed(4)),
      energy_in: Number(today.energyIn.toFixed(3)),
      energy_out: Number(today.energyOut.toFixed(3)),
      losses: Number(losses.toFixed(3)),
      derived_from_command_history: true,
    },
  }
})
