import { existsSync, readFileSync } from 'fs'
import { join } from 'path'
import { eventHandler, getMethod, readBody } from 'h3'
import { getBatteryState, updateBatteryState } from '~/server/utils/battery'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

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

type TenantControlMirror = {
  powerCommand: number
  manualMode: boolean
  autoOptimization: boolean
  updatedAt: string
}

const round = (value: number, digits = 2) => Number(value.toFixed(digits))

function getControlMirrorStore(): Record<string, TenantControlMirror> {
  ;(globalThis as any).__batteryControlMirrorByTenant = (globalThis as any).__batteryControlMirrorByTenant || {}
  return (globalThis as any).__batteryControlMirrorByTenant
}

function readControlMirror(tenantId: string): TenantControlMirror {
  const store = getControlMirrorStore()
  const existing = store[tenantId]
  if (existing) {
    return existing
  }

  return {
    powerCommand: 0,
    manualMode: true,
    autoOptimization: false,
    updatedAt: new Date().toISOString(),
  }
}

function writeControlMirror(tenantId: string, updates: Partial<TenantControlMirror>): TenantControlMirror {
  const next = {
    ...readControlMirror(tenantId),
    ...updates,
    updatedAt: new Date().toISOString(),
  }
  getControlMirrorStore()[tenantId] = next
  return next
}

function loadBatterySimulationSpec(defaultVoltage: number, tenantId: string): BatterySimSpec {
  const tenantConfigPath = join(process.cwd(), '../energy_ml/configs/tenants', tenantId, 'user_config.json')
  const legacyConfigPath = join(process.cwd(), '../energy_ml/configs/user_config.json')
  const configPath = existsSync(tenantConfigPath) ? tenantConfigPath : legacyConfigPath

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

function clampPower(targetKw: number, spec: BatterySimSpec): number {
  if (!Number.isFinite(targetKw)) return 0
  return Math.max(-spec.maxDischargePowerKw, Math.min(spec.maxChargePowerKw, targetKw))
}

function resolveManualCommand(powerKw: number): { command: 'charge' | 'discharge' | 'hold', powerKw: number } {
  const normalized = Number(powerKw)
  if (!Number.isFinite(normalized) || Math.abs(normalized) < 0.05) {
    return { command: 'hold', powerKw: 0 }
  }
  if (normalized > 0) {
    return { command: 'charge', powerKw: Math.abs(normalized) }
  }
  return { command: 'discharge', powerKw: -Math.abs(normalized) }
}

function resolveCommandedPower(params: {
  activeCommand: string
  livePowerKw: number
  historyPowerKw: number | null
  mirrorPowerKw: number
  spec: BatterySimSpec
}): number {
  const historyPowerKw = params.historyPowerKw
  if (Number.isFinite(historyPowerKw)) {
    return round(clampPower(Number(historyPowerKw), params.spec), 3)
  }

  if (Number.isFinite(params.mirrorPowerKw) && Math.abs(params.mirrorPowerKw) > 0.001) {
    return round(clampPower(params.mirrorPowerKw, params.spec), 3)
  }

  if (params.activeCommand === 'charge') {
    const fallback = Math.abs(params.livePowerKw) > 0.05 ? Math.abs(params.livePowerKw) : params.spec.maxChargePowerKw * 0.2
    return round(clampPower(Math.abs(fallback), params.spec), 3)
  }

  if (params.activeCommand === 'discharge') {
    const fallback = Math.abs(params.livePowerKw) > 0.05 ? Math.abs(params.livePowerKw) : params.spec.maxDischargePowerKw * 0.2
    return round(clampPower(-Math.abs(fallback), params.spec), 3)
  }

  return 0
}

export default eventHandler(async (event) => {
  const tenant = await resolveTenantContext(event)
  const method = getMethod(event)
  const tenantRequest = {
    query: {
      tenantId: tenant.id,
    },
    headers: {
      'x-tenant-id': tenant.id,
    },
  }

  if (method === 'GET') {
    const [state, controlStatus, controlHistory] = await Promise.all([
      getBatteryState(tenant.id),
      $fetch<any>('/api/control/status', tenantRequest).catch(() => null),
      $fetch<any>('/api/control/history', {
        ...tenantRequest,
        query: {
          ...tenantRequest.query,
          limit: 1,
        },
      }).catch(() => null),
    ])

    const socPercent = Number(state?.soc ?? 50)
    const voltage = Number(state?.voltage ?? 400)
    const current = Number(state?.current ?? 0)
    const livePowerKw = round((voltage * current) / 1000, 3)

    const spec = loadBatterySimulationSpec(voltage, tenant.id)
    const mirror = readControlMirror(tenant.id)
    const statusMode = String(controlStatus?.mode || '').toLowerCase() === 'automatic' ? 'automatic' : 'manual'
    const manualMode = statusMode === 'manual'
    const autoOptimization = !manualMode
    const activeCommand = String(controlStatus?.active_command || controlHistory?.history?.[0]?.command || 'hold').toLowerCase()
    const historyPowerKwRaw = Number(controlHistory?.history?.[0]?.power_kw)
    const historyPowerKw = Number.isFinite(historyPowerKwRaw) ? historyPowerKwRaw : null

    const effectivePowerCommand = resolveCommandedPower({
      activeCommand,
      livePowerKw,
      historyPowerKw,
      mirrorPowerKw: mirror.powerCommand,
      spec,
    })

    writeControlMirror(tenant.id, {
      powerCommand: effectivePowerCommand,
      manualMode,
      autoOptimization,
    })

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
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
        execution_mode: manualMode ? 'manual_command' : 'auto_recommendation',
        active_command: activeCommand,
        requested_command: controlStatus?.requested_command || null,
        decision_source: controlStatus?.decision_source || null,
        isSimulationRunning: true,
        source: 'control_status_backed_simulator',
        lastUpdated: state?.lastUpdate || new Date().toISOString(),
      },
      specs: {
        typeName: spec.typeName,
        efficiency: round(spec.efficiency, 4),
        roundTripEfficiency: round(spec.efficiency * spec.efficiency, 4),
        nominalVoltage: round(spec.nominalVoltage, 2),
        selfDischarge: spec.selfDischargePercentMonthly,
      },
      source_metadata: {
        tenant_filter_applied: true,
        control_status_source: controlStatus?.source || 'unavailable',
        control_history_source: controlHistory?.source || 'unavailable',
      },
    }
  }

  if (method === 'POST') {
    const body = await readBody(event)
    const state = await getBatteryState(tenant.id)
    const spec = loadBatterySimulationSpec(Number(state?.voltage ?? 400), tenant.id)

    if (body.action === 'setPower') {
      const requestedPowerKw = Number(body.power ?? 0)
      const clampedPowerKw = round(clampPower(requestedPowerKw, spec), 3)
      const resolved = resolveManualCommand(clampedPowerKw)

      const executeResponse = await $fetch<any>('/api/control/execute', {
        ...tenantRequest,
        method: 'POST',
        body: {
          tenantId: tenant.id,
          command: resolved.command,
          power_kw: resolved.powerKw,
          reason: body.reason || 'Battery simulator manual power command',
          user_id: body.user_id || 'battery_simulator',
        },
      }).catch((error) => {
        throw createError({
          statusCode: 500,
          statusMessage: error?.data?.error || error?.message || 'Control execute request failed',
        })
      })

      if (!executeResponse?.success) {
        throw createError({
          statusCode: 500,
          statusMessage: executeResponse?.error || 'Control execute request failed',
        })
      }

      writeControlMirror(tenant.id, {
        powerCommand: clampedPowerKw,
        manualMode: true,
        autoOptimization: false,
      })

      return {
        success: true,
        tenant: getTenantResponseMetadata(tenant),
        message: `Power set to ${clampedPowerKw}kW`,
        powerCommand: clampedPowerKw,
        requested_command: executeResponse?.requested_command || resolved.command,
        resolved_command: executeResponse?.resolved_command || resolved.command,
        decision_source: executeResponse?.decision_source || 'manual',
        execution_mode: 'manual_command',
        source: executeResponse?.source || 'control_execute',
        source_metadata: executeResponse?.source_metadata || {
          tenant_filter_applied: true,
        },
      }
    }

    if (body.action === 'setAutoMode') {
      const enabled = body.enabled ?? true
      const executeResponse = await $fetch<any>('/api/control/execute', {
        ...tenantRequest,
        method: 'POST',
        body: {
          tenantId: tenant.id,
          command: enabled ? 'auto' : 'hold',
          power_kw: enabled ? Math.abs(Number(body.power ?? 2.5)) : 0,
          reason: enabled ? 'Battery simulator: enable auto mode' : 'Battery simulator: disable auto mode',
          user_id: body.user_id || 'battery_simulator',
        },
      }).catch((error) => {
        throw createError({
          statusCode: 500,
          statusMessage: error?.data?.error || error?.message || 'Failed to set control mode',
        })
      })

      if (!executeResponse?.success) {
        throw createError({
          statusCode: 500,
          statusMessage: executeResponse?.error || 'Failed to set control mode',
        })
      }

      writeControlMirror(tenant.id, {
        powerCommand: enabled ? 0 : Number(readControlMirror(tenant.id).powerCommand || 0),
        manualMode: !enabled,
        autoOptimization: enabled,
      })

      return {
        success: true,
        tenant: getTenantResponseMetadata(tenant),
        message: `Auto mode ${enabled ? 'enabled' : 'disabled'}`,
        autoOptimization: enabled,
        manualMode: !enabled,
        requested_command: executeResponse?.requested_command || (enabled ? 'auto' : 'hold'),
        resolved_command: executeResponse?.resolved_command || (enabled ? 'auto' : 'hold'),
        decision_source: executeResponse?.decision_source || (enabled ? 'dagster' : 'manual'),
        execution_mode: enabled ? 'auto_recommendation' : 'manual_command',
        source: executeResponse?.source || 'control_execute',
        source_metadata: executeResponse?.source_metadata || {
          tenant_filter_applied: true,
        },
      }
    }

    if (body.action === 'reset') {
      await $fetch<any>('/api/control/execute', {
        ...tenantRequest,
        method: 'POST',
        body: {
          tenantId: tenant.id,
          command: 'hold',
          power_kw: 0,
          reason: 'Battery simulator reset command',
          user_id: body.user_id || 'battery_simulator',
        },
      }).catch(() => null)

      writeControlMirror(tenant.id, {
        powerCommand: 0,
        manualMode: true,
        autoOptimization: false,
      })

      await updateBatteryState({
        current: 0,
        temperature: 25,
      }, tenant.id)

      return {
        success: true,
        tenant: getTenantResponseMetadata(tenant),
        message: 'Battery reset',
        execution_mode: 'manual_command',
      }
    }

    return { success: false, error: 'Unknown action' }
  }

  return { success: false, error: 'Method not allowed' }
})
