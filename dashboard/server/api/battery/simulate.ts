import { existsSync, readFileSync } from 'fs'
import { join } from 'path'
import { eventHandler, getMethod, readBody } from 'h3'
import { getBatteryState, updateBatteryState } from '~/server/utils/battery'

interface BatterySimSpec {
  batteryType: string
  typeName: string
  capacityKwh: number
  usableCapacityKwh: number
  socMinPercent: number
  socMaxPercent: number
  maxChargePowerKw: number
  maxDischargePowerKw: number
  efficiency: number
  nominalVoltage: number
  selfDischargePercentMonthly: number
}

let powerCommand = 0
let manualMode = true
let autoOptimization = false

const round = (value: number, digits = 2) => Number(value.toFixed(digits))

function loadBatterySimulationSpec(defaultVoltage: number): BatterySimSpec {
  const configPath = join(process.cwd(), '../energy_ml/configs/user_config.json')

  let config: any = null
  if (existsSync(configPath)) {
    try {
      config = JSON.parse(readFileSync(configPath, 'utf-8'))
    } catch {
      config = null
    }
  }

  const batteryType = String(config?.battery_type || 'LFP')
  const capacityKwh = Number(config?.battery_capacity_kwh || 150)
  const efficiency = Number(config?.battery_efficiency || 0.95)
  const socMinPercent = Number(config?.battery_soc_min ?? 0.1) * 100
  const socMaxPercent = Number(config?.battery_soc_max ?? 0.95) * 100

  const maxChargePowerKw = Math.max(0.1, capacityKwh * Number(config?.battery_c_rate_charge || 0.5))
  const maxDischargePowerKw = Math.max(0.1, capacityKwh * Number(config?.battery_c_rate_discharge || 1.0))

  const typeNames: Record<string, string> = {
    LFP: 'Lithium Iron Phosphate',
    'Lead-Acid': 'Lead-Acid Deep Cycle',
    VRFB: 'Vanadium Redox Flow Battery',
  }

  return {
    batteryType,
    typeName: typeNames[batteryType] || batteryType,
    capacityKwh,
    usableCapacityKwh: capacityKwh * Math.max(0, (socMaxPercent - socMinPercent) / 100),
    socMinPercent,
    socMaxPercent,
    maxChargePowerKw,
    maxDischargePowerKw,
    efficiency,
    nominalVoltage: Number.isFinite(defaultVoltage) && defaultVoltage > 0 ? defaultVoltage : 400,
    selfDischargePercentMonthly: 1,
  }
}

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

function clampPower(targetKw: number, spec: BatterySimSpec): number {
  if (!Number.isFinite(targetKw)) return 0
  return Math.max(-spec.maxDischargePowerKw, Math.min(spec.maxChargePowerKw, targetKw))
}

export default eventHandler(async (event) => {
  const method = getMethod(event)

  if (method === 'GET') {
    const state = await getBatteryState()

    const socPercent = Number(state?.soc ?? 50)
    const voltage = Number(state?.voltage ?? 400)
    const current = Number(state?.current ?? 0)
    const livePowerKw = round((voltage * current) / 1000, 3)

    const spec = loadBatterySimulationSpec(voltage)
    const effectivePowerCommand = manualMode
      ? powerCommand
      : computeAutoPowerKw(socPercent, spec)

    return {
      success: true,
      battery: {
        soc: round(socPercent / 100, 4),
        socPercentage: round(socPercent, 1),
        power: livePowerKw,
        commandedPower: effectivePowerCommand,
        voltage: round(voltage, 2),
        current: round(current, 2),
        temperature: round(Number(state?.temperature ?? 25), 1),
        health: round(Number(state?.health ?? 98.5), 1),
        cycleCount: Number(state?.cycles ?? 0),
        type: spec.batteryType,
        capacity: round(spec.capacityKwh, 2),
        usableCapacity: round(spec.usableCapacityKwh, 2),
        socMin: round(spec.socMinPercent, 1),
        socMax: round(spec.socMaxPercent, 1),
        maxChargePower: round(spec.maxChargePowerKw, 2),
        maxDischargePower: round(spec.maxDischargePowerKw, 2),
        isCharging: effectivePowerCommand > 0.1,
        isDischarging: effectivePowerCommand < -0.1,
        isIdle: Math.abs(effectivePowerCommand) <= 0.1,
        estimatedRuntime: null,
        estimatedChargeTime: null,
        powerCommand: effectivePowerCommand,
        manualMode,
        autoOptimization,
        execution_mode: manualMode ? 'manual_command' : 'auto_optimization',
        isSimulationRunning: true,
        source: 'battery_state_backed_simulator',
        lastUpdated: state?.lastUpdate || new Date().toISOString(),
      },
      specs: {
        typeName: spec.typeName,
        efficiency: round(spec.efficiency, 4),
        roundTripEfficiency: round(spec.efficiency * spec.efficiency, 4),
        nominalVoltage: round(spec.nominalVoltage, 2),
        selfDischarge: spec.selfDischargePercentMonthly,
      },
    }
  }

  if (method === 'POST') {
    const body = await readBody(event)
    const state = await getBatteryState()
    const spec = loadBatterySimulationSpec(Number(state?.voltage ?? 400))

    if (body.action === 'setPower') {
      const requestedPowerKw = Number(body.power ?? 0)
      powerCommand = round(clampPower(requestedPowerKw, spec), 3)
      manualMode = true
      autoOptimization = false

      const voltage = Number(state?.voltage ?? spec.nominalVoltage)
      const derivedCurrent = voltage > 0 ? round((powerCommand * 1000) / voltage, 2) : 0
      await updateBatteryState({ current: derivedCurrent })

      return {
        success: true,
        message: `Power set to ${powerCommand}kW`,
        powerCommand,
        execution_mode: 'manual_command',
      }
    }

    if (body.action === 'setAutoMode') {
      autoOptimization = body.enabled ?? true
      manualMode = !autoOptimization

      if (autoOptimization) {
        powerCommand = 0
        await updateBatteryState({ current: 0 })
      }

      return {
        success: true,
        message: `Auto mode ${autoOptimization ? 'enabled' : 'disabled'}`,
        autoOptimization,
        manualMode,
        execution_mode: autoOptimization ? 'auto_optimization' : 'manual_command',
      }
    }

    if (body.action === 'reset') {
      powerCommand = 0
      manualMode = true
      autoOptimization = false

      await updateBatteryState({
        current: 0,
        temperature: 25,
      })

      return {
        success: true,
        message: 'Battery reset',
        execution_mode: 'manual_command',
      }
    }

    return { success: false, error: 'Unknown action' }
  }

  return { success: false, error: 'Method not allowed' }
})
