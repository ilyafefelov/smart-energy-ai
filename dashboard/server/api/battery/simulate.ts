import { existsSync, readFileSync } from 'fs'
import { join } from 'path'
import { eventHandler, getMethod, readBody } from 'h3'
import { getBatteryState, updateBatteryState } from '../../utils/battery'
import { getBatteryControlState, updateBatteryControlState } from '../../utils/battery-control-state'
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
const SIMULATION_TIME_SCALE = 120

const DEFAULT_ENERGY_CONFIG = {
  battery_type: 'LFP',
  battery_capacity_kwh: 150,
  battery_efficiency: 0.95,
  battery_c_rate_charge: 0.5,
  battery_c_rate_discharge: 1,
  battery_soc_min: 0.1,
  battery_soc_max: 0.95,
  load_profile_type: 'standard',
  load_peak_kw: 10,
  load_base_kw: 2,
  load_custom_hourly: null,
  load_seasonal_variation: 0.2,
  load_weekend_factor: 0.6,
  load_night_factor: 0.3,
  has_solar: false,
  has_wind: false,
  solar_capacity_kw: 0,
  wind_capacity_kw: 0,
  solar_efficiency: 0.2,
  wind_efficiency: 0.35,
  wind_cut_in_speed_mps: 3,
  wind_rated_speed_mps: 12,
}

const LOAD_PROFILE_COEFFICIENTS: Record<'standard' | 'multi-shift' | '24/7', number[]> = {
  standard: [0.2, 0.2, 0.2, 0.2, 0.2, 0.3, 0.4, 0.6, 0.8, 1, 1, 0.9, 0.8, 0.9, 1, 1, 0.9, 0.8, 0.6, 0.5, 0.4, 0.3, 0.3, 0.2],
  'multi-shift': [0.8, 0.8, 0.7, 0.6, 0.5, 0.4, 1, 1, 1, 1, 1, 1, 1, 1, 0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3, 0.9, 0.9],
  '24/7': [0.9, 0.9, 0.9, 0.9, 0.9, 0.95, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.95, 0.95, 0.9, 0.9],
}

function deterministicNoise(seed: number): number {
  const value = Math.sin(seed * 12.9898 + 78.233) * 43758.5453
  return value - Math.floor(value)
}

function normalizeLoadProfileType(value: unknown): 'standard' | 'multi-shift' | '24/7' | 'custom' {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'multi_shift' || normalized === 'multi-shift') return 'multi-shift'
  if (normalized === '24_7' || normalized === '24/7') return '24/7'
  if (normalized === 'custom') return 'custom'
  return 'standard'
}

function loadTenantEnergyConfig(tenantId: string): any {
  const tenantConfigPath = join(process.cwd(), '../energy_ml/configs/tenants', tenantId, 'user_config.json')
  const legacyConfigPath = join(process.cwd(), '../energy_ml/configs/user_config.json')
  const configPath = existsSync(tenantConfigPath) ? tenantConfigPath : legacyConfigPath

  let config: any = {}
  if (existsSync(configPath)) {
    try {
      config = JSON.parse(readFileSync(configPath, 'utf-8'))
    } catch {
      config = {}
    }
  }

  return {
    ...DEFAULT_ENERGY_CONFIG,
    ...config,
    load_profile_type: normalizeLoadProfileType(config?.load_profile_type),
  }
}

function getDayOfYear(date: Date): number {
  const start = new Date(Date.UTC(date.getUTCFullYear(), 0, 0))
  const diff = date.getTime() - start.getTime()
  return Math.floor(diff / 86400000)
}

function estimateLoadDemandKw(config: any, at: Date): number {
  const hour = at.getHours()
  const day = at.getDay()
  const profileType = normalizeLoadProfileType(config?.load_profile_type)
  const baseKw = Math.max(0.1, Number(config?.load_base_kw ?? DEFAULT_ENERGY_CONFIG.load_base_kw))
  const peakKw = Math.max(baseKw, Number(config?.load_peak_kw ?? DEFAULT_ENERGY_CONFIG.load_peak_kw))

  let profileCoeff = 0.6
  const customProfile = Array.isArray(config?.load_custom_hourly) ? config.load_custom_hourly : null
  if (profileType === 'custom' && customProfile && customProfile.length === 24) {
    profileCoeff = Math.max(0, Math.min(1.5, Number(customProfile[hour] ?? 0.5)))
  } else {
    const profile = LOAD_PROFILE_COEFFICIENTS[profileType as 'standard' | 'multi-shift' | '24/7'] || LOAD_PROFILE_COEFFICIENTS.standard
    profileCoeff = Number(profile[hour] ?? 0.6)
  }

  const weekendFactor = (day === 0 || day === 6)
    ? Math.max(0.2, Number(config?.load_weekend_factor ?? DEFAULT_ENERGY_CONFIG.load_weekend_factor))
    : 1
  const nightFactor = (hour < 6 || hour >= 22)
    ? Math.max(0.2, Number(config?.load_night_factor ?? DEFAULT_ENERGY_CONFIG.load_night_factor)) + 0.7
    : 1
  const seasonalVariation = Math.max(0, Number(config?.load_seasonal_variation ?? DEFAULT_ENERGY_CONFIG.load_seasonal_variation))
  const seasonalFactor = 1 + Math.sin((2 * Math.PI * (getDayOfYear(at) - 80)) / 365) * seasonalVariation * 0.25

  const demand = (baseKw + (peakKw - baseKw) * profileCoeff) * weekendFactor * nightFactor * seasonalFactor
  return round(Math.max(0.1, demand), 3)
}

function estimateRenewableGenerationKw(config: any, at: Date): number {
  const hour = at.getHours()
  const dayOfYear = getDayOfYear(at)

  const hasSolar = Boolean(config?.has_solar ?? Number(config?.solar_capacity_kw || 0) > 0)
  const hasWind = Boolean(config?.has_wind ?? Number(config?.wind_capacity_kw || 0) > 0)
  const solarCapacityKw = hasSolar ? Math.max(0, Number(config?.solar_capacity_kw || 0)) : 0
  const windCapacityKw = hasWind ? Math.max(0, Number(config?.wind_capacity_kw || 0)) : 0

  let solarGenerationKw = 0
  if (solarCapacityKw > 0 && hour >= 6 && hour <= 18) {
    const sunFactor = Math.sin(Math.PI * (hour - 6) / 12)
    const seasonalFactor = 0.7 + 0.3 * Math.sin((2 * Math.PI * (dayOfYear - 80)) / 365)
    const cloudNoise = deterministicNoise(dayOfYear * 37 + hour * 11 + 7)
    const cloudFactor = 0.55 + 0.45 * (1 - cloudNoise)
    const solarEfficiency = Math.max(0.1, Number(config?.solar_efficiency || DEFAULT_ENERGY_CONFIG.solar_efficiency))
    const solarEfficiencyFactor = Math.max(0.4, Math.min(1.35, solarEfficiency / 0.2))
    solarGenerationKw = solarCapacityKw * sunFactor * seasonalFactor * cloudFactor * solarEfficiencyFactor
  }

  let windGenerationKw = 0
  if (windCapacityKw > 0) {
    const windEfficiency = Math.max(0.1, Number(config?.wind_efficiency || DEFAULT_ENERGY_CONFIG.wind_efficiency))
    const windEfficiencyFactor = Math.max(0.35, Math.min(1.25, windEfficiency / 0.35))
    const cutIn = Math.max(0.5, Number(config?.wind_cut_in_speed_mps || DEFAULT_ENERGY_CONFIG.wind_cut_in_speed_mps))
    const rated = Math.max(cutIn + 1, Number(config?.wind_rated_speed_mps || DEFAULT_ENERGY_CONFIG.wind_rated_speed_mps))
    const windNoise = deterministicNoise(dayOfYear * 19 + hour * 3 + 17)
    const windSpeed = 2.5 + windNoise * 10.5

    if (windSpeed >= cutIn && windSpeed < 25) {
      if (windSpeed <= rated) {
        windGenerationKw = windCapacityKw * Math.pow((windSpeed - cutIn) / (rated - cutIn), 3) * windEfficiencyFactor
      } else {
        windGenerationKw = windCapacityKw * 0.95 * windEfficiencyFactor
      }
    }
  }

  return round(Math.max(0, solarGenerationKw + windGenerationKw), 3)
}

function resolveRenewableChargePowerKw(input: {
  renewableGenerationKw: number
  loadDemandKw: number
  spec: BatterySimSpec
}): { renewableSurplusKw: number; chargePowerKw: number } {
  const renewableSurplusKw = round(input.renewableGenerationKw - input.loadDemandKw, 3)
  const chargePowerKw = renewableSurplusKw > 0
    ? round(Math.min(input.spec.maxChargePowerKw, renewableSurplusKw), 3)
    : 0

  return {
    renewableSurplusKw,
    chargePowerKw,
  }
}

function commandFromPower(powerKw: number): 'charge' | 'discharge' | 'hold' {
  if (powerKw > 0.05) return 'charge'
  if (powerKw < -0.05) return 'discharge'
  return 'hold'
}

function resolveModeState(
  controlStatus: any,
  mirror: TenantControlMirror,
): { manualMode: boolean; autoOptimization: boolean; activeCommand: string } {
  const hasControlMode = typeof controlStatus?.mode === 'string' && controlStatus.mode.trim().length > 0
  if (hasControlMode) {
    const manualMode = String(controlStatus.mode).toLowerCase() !== 'automatic'
    const activeCommand = String(controlStatus?.active_command || commandFromPower(mirror.powerCommand)).toLowerCase()
    return {
      manualMode,
      autoOptimization: !manualMode,
      activeCommand,
    }
  }

  return {
    manualMode: Boolean(mirror.manualMode),
    autoOptimization: !Boolean(mirror.manualMode),
    activeCommand: commandFromPower(Number(mirror.powerCommand || 0)),
  }
}

async function applyCommandProgression(params: {
  tenantId: string
  state: any
  spec: BatterySimSpec
  appliedPowerCommand: number
}): Promise<any> {
  const { tenantId, state, spec } = params
  const appliedPowerCommand = Number(params.appliedPowerCommand || 0)
  const now = Date.now()
  const lastUpdateMs = new Date(state?.lastUpdate || 0).getTime()
  if (!Number.isFinite(lastUpdateMs)) {
    return state
  }

  const elapsedHoursRaw = Math.max(0, (now - lastUpdateMs) / 3600000) * SIMULATION_TIME_SCALE
  const elapsedHours = Math.min(elapsedHoursRaw, 0.25)
  if (elapsedHours <= 0.0005) {
    return state
  }

  const socCurrent = Number(state?.soc ?? 50)
  const voltage = Number(state?.voltage ?? spec.nominalVoltage ?? 400)
  const baselineTemp = 24
  let socNext = socCurrent

  if (Math.abs(appliedPowerCommand) > 0.05 && spec.capacityKwh > 0) {
    const transferKwh = Math.abs(appliedPowerCommand) * elapsedHours
    if (appliedPowerCommand > 0) {
      socNext += (transferKwh * spec.efficiency / spec.capacityKwh) * 100
    } else {
      socNext -= (transferKwh / Math.max(0.6, spec.efficiency) / spec.capacityKwh) * 100
    }
  } else {
    const selfDischargePerHour = (spec.selfDischargePercentMonthly / 30 / 24)
    socNext -= selfDischargePerHour * elapsedHours
  }

  socNext = Math.max(spec.socMinPercent, Math.min(spec.socMaxPercent, socNext))

  const nextCurrent = Math.abs(appliedPowerCommand) > 0.05
    ? (appliedPowerCommand * 1000) / Math.max(1, voltage)
    : 0
  const priorTemp = Number(state?.temperature ?? baselineTemp)
  const tempTarget = baselineTemp + Math.min(12, Math.abs(nextCurrent) / 12)
  const tempBlend = Math.min(1, elapsedHours / 0.2)
  const nextTemperature = priorTemp + (tempTarget - priorTemp) * tempBlend

  return updateBatteryState({
    soc: round(socNext, 2),
    current: round(nextCurrent, 3),
    temperature: round(nextTemperature, 1),
  }, tenantId)
}

function loadBatterySimulationSpec(defaultVoltage: number, tenantConfig: any): BatterySimSpec {
  const batteryType = String(tenantConfig?.battery_type || DEFAULT_ENERGY_CONFIG.battery_type)
  const capacityKwh = Number(tenantConfig?.battery_capacity_kwh || DEFAULT_ENERGY_CONFIG.battery_capacity_kwh)
  const efficiency = Number(tenantConfig?.battery_efficiency || DEFAULT_ENERGY_CONFIG.battery_efficiency)
  const socMinPercent = Number(tenantConfig?.battery_soc_min ?? DEFAULT_ENERGY_CONFIG.battery_soc_min) * 100
  const socMaxPercent = Number(tenantConfig?.battery_soc_max ?? DEFAULT_ENERGY_CONFIG.battery_soc_max) * 100

  const maxChargePowerKw = Math.max(0.1, capacityKwh * Number(tenantConfig?.battery_c_rate_charge || DEFAULT_ENERGY_CONFIG.battery_c_rate_charge))
  const maxDischargePowerKw = Math.max(0.1, capacityKwh * Number(tenantConfig?.battery_c_rate_discharge || DEFAULT_ENERGY_CONFIG.battery_c_rate_discharge))

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
  const desiredSign = params.activeCommand === 'charge' ? 1 : params.activeCommand === 'discharge' ? -1 : 0
  const historyPowerKw = params.historyPowerKw
  if (Number.isFinite(historyPowerKw)) {
    const normalizedHistory = round(clampPower(Number(historyPowerKw), params.spec), 3)
    if (
      desiredSign === 0
      || (Math.abs(normalizedHistory) > 0.05 && Math.sign(normalizedHistory) === desiredSign)
    ) {
      return normalizedHistory
    }
  }

  if (Number.isFinite(params.mirrorPowerKw) && Math.abs(params.mirrorPowerKw) > 0.001) {
    const normalizedMirror = round(clampPower(params.mirrorPowerKw, params.spec), 3)
    if (desiredSign === 0) {
      return 0
    }
    if (Math.sign(normalizedMirror) !== desiredSign && Math.abs(normalizedMirror) > 0.05) {
      return round(clampPower(Math.abs(normalizedMirror) * desiredSign, params.spec), 3)
    }
    return normalizedMirror
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

    const tenantConfig = loadTenantEnergyConfig(tenant.id)
    const spec = loadBatterySimulationSpec(voltage, tenantConfig)
    const loadDemandKw = estimateLoadDemandKw(tenantConfig, new Date())
    const renewableGenerationKw = estimateRenewableGenerationKw(tenantConfig, new Date())
    const mirror = await getBatteryControlState(tenant.id)
    const resolvedMode = resolveModeState(controlStatus, mirror)
    const manualMode = resolvedMode.manualMode
    const autoOptimization = resolvedMode.autoOptimization
    const activeCommand = String(controlStatus?.active_command || controlHistory?.history?.[0]?.command || resolvedMode.activeCommand || 'hold').toLowerCase()
    const historyPowerKwRaw = Number(controlHistory?.history?.[0]?.power_kw)
    const historyPowerKw = Number.isFinite(historyPowerKwRaw) ? historyPowerKwRaw : null

    const effectivePowerCommand = resolveCommandedPower({
      activeCommand,
      livePowerKw,
      historyPowerKw,
      mirrorPowerKw: mirror.powerCommand,
      spec,
    })

    const renewablePower = resolveRenewableChargePowerKw({
      renewableGenerationKw,
      loadDemandKw,
      spec,
    })

    const renewableChargeAppliedKw = effectivePowerCommand < -0.05
      ? 0
      : renewablePower.chargePowerKw

    const appliedPowerCommand = round(clampPower(effectivePowerCommand + renewableChargeAppliedKw, spec), 3)

    await updateBatteryControlState({
      powerCommand: effectivePowerCommand,
      manualMode,
      autoOptimization,
    })

    const progressedState = await applyCommandProgression({
      tenantId: tenant.id,
      state,
      spec,
      appliedPowerCommand,
    })

    const progressedSocPercent = Number(progressedState?.soc ?? socPercent)
    const progressedVoltage = Number(progressedState?.voltage ?? voltage)
    const progressedCurrent = Number(progressedState?.current ?? current)
    const progressedLivePowerKw = round((progressedVoltage * progressedCurrent) / 1000, 3)

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      battery: {
        soc: round(progressedSocPercent / 100, 4),
        socPercentage: round(progressedSocPercent, 1),
        power: progressedLivePowerKw,
        commandedPower: effectivePowerCommand,
        appliedPowerCommand,
        voltage: round(progressedVoltage, 2),
        current: round(progressedCurrent, 2),
        temperature: round(Number(progressedState?.temperature ?? 25), 1),
        health: round(Number(progressedState?.health ?? 98.5), 1),
        cycleCount: Number(progressedState?.cycles ?? 0),
        type: spec.batteryType,
        capacity: round(spec.capacityKwh, 2),
        usableCapacity: round(spec.usableCapacityKwh, 2),
        socMin: round(spec.socMinPercent, 1),
        socMax: round(spec.socMaxPercent, 1),
        maxChargePower: round(spec.maxChargePowerKw, 2),
        maxDischargePower: round(spec.maxDischargePowerKw, 2),
        isCharging: appliedPowerCommand > 0.1,
        isDischarging: appliedPowerCommand < -0.1,
        isIdle: Math.abs(appliedPowerCommand) <= 0.1,
        estimatedRuntime: null,
        estimatedChargeTime: null,
        powerCommand: effectivePowerCommand,
        renewableGenerationKw,
        loadDemandKw,
        renewableSurplusKw: renewablePower.renewableSurplusKw,
        renewableChargePowerKw: renewableChargeAppliedKw,
        renewableChargeAvailableKw: renewablePower.chargePowerKw,
        manualMode,
        autoOptimization,
        execution_mode: manualMode ? 'manual_command' : 'auto_recommendation',
        active_command: activeCommand,
        requested_command: controlStatus?.requested_command || null,
        decision_source: controlStatus?.decision_source || null,
        command_reason: controlStatus?.command_reason || null,
        control_source: controlStatus?.source || null,
        control_fallback_reason_code: controlStatus?.source_metadata?.fallback_reason_code || null,
        isSimulationRunning: true,
        source: 'control_status_backed_simulator',
        lastUpdated: progressedState?.lastUpdate || new Date().toISOString(),
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
        renewable_model_source: 'local_deterministic_estimate',
      },
    }
  }

  if (method === 'POST') {
    const body = await readBody(event)
    const state = await getBatteryState(tenant.id)
    const tenantConfig = loadTenantEnergyConfig(tenant.id)
    const spec = loadBatterySimulationSpec(Number(state?.voltage ?? 400), tenantConfig)

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

      await updateBatteryControlState({
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

      const currentMirror = await getBatteryControlState(tenant.id)
      await updateBatteryControlState({
        powerCommand: enabled ? 0 : Number(currentMirror.powerCommand || 0),
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

      await updateBatteryControlState({
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

    if (body.action === 'setSoc') {
      const rawSoc = Number(body.socPercent ?? body.soc ?? NaN)
      if (!Number.isFinite(rawSoc)) {
        throw createError({
          statusCode: 400,
          statusMessage: 'Invalid socPercent. Must be a finite number between 0 and 100',
        })
      }

      const normalizedSoc = rawSoc <= 1 ? rawSoc * 100 : rawSoc
      const clampedSoc = round(Math.max(0, Math.min(100, normalizedSoc)), 2)
      const updated = await updateBatteryState({
        soc: clampedSoc,
        current: 0,
      }, tenant.id)

      return {
        success: true,
        tenant: getTenantResponseMetadata(tenant),
        message: `Battery SoC synchronized to ${clampedSoc}%`,
        socPercent: clampedSoc,
        soc: round(clampedSoc / 100, 4),
        lastUpdated: updated.lastUpdate,
        execution_mode: 'manual_sync',
      }
    }

    return { success: false, error: 'Unknown action' }
  }

  return { success: false, error: 'Method not allowed' }
})
