/**
 * Save Configuration API Endpoint
 * Saves tenant-scoped user configuration and triggers recalculation markers.
 */
// @ts-ignore - Node built-in types are available at runtime in Nitro server context.
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'fs'
// @ts-ignore - Node built-in types are available at runtime in Nitro server context.
import { dirname, join } from 'path'
import { createError, defineEventHandler, readBody } from 'h3'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const getCwd = () => ((globalThis as any).process?.cwd ? (globalThis as any).process.cwd() : '.')

const DEFAULT_CONFIG = {
  battery_type: 'LFP',
  battery_capacity_kwh: 10.0,
  battery_efficiency: 0.95,
  battery_c_rate_charge: 0.5,
  battery_c_rate_discharge: 1.0,
  battery_dod_max: 0.9,
  battery_soc_min: 0.1,
  battery_soc_max: 1.0,
  battery_cycles_max: 8000,
  battery_degradation_per_cycle: 0.0000125,
  load_profile_type: 'standard',
  load_peak_kw: 10.0,
  load_base_kw: 2.0,
  load_custom_hourly: null,
  load_seasonal_variation: 0.2,
  load_weekend_factor: 0.6,
  load_night_factor: 0.3,
  tariff_region: 'ukraine',
  tariff_peak_hours_start: 6,
  tariff_peak_hours_end: 23,
  tariff_peak_rate_uah_kwh: 12.5,
  tariff_off_peak_rate_uah_kwh: 8.0,
  ml_retrain_frequency_days: 7,
  ml_confidence_threshold: 0.7,
  ml_model_type: 'ensemble',
  ml_lookback_hours: 168,
  ml_forecast_horizon_hours: 24,
  dashboard_refresh_seconds: 30,
  dashboard_show_degradation_cost: true,
  dashboard_show_arbitrage_opportunities: true,
  dashboard_currency_symbol: '₴',
  dashboard_language: 'en',
  optimization_strategy: 'balanced',
  custom_optimization_weights: null,
  solar_capacity_kw: 0,
  wind_capacity_kw: 0,
  latitude: 50.45,
  longitude: 30.52,
  timezone: 'Europe/Kiev',
}

function normalizeLoadProfileType(value: unknown) {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'multi_shift' || normalized === 'multi-shift') return 'multi-shift'
  if (normalized === '24_7' || normalized === '24/7') return '24/7'
  if (normalized === 'custom') return 'custom'
  return 'standard'
}

function normalizeOptimizationStrategy(value: unknown) {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'max-earn' || normalized === 'max_earn') return 'max_earn'
  if (normalized === 'max-health' || normalized === 'max_battery_health') return 'max_battery_health'
  if (normalized === 'max-charge' || normalized === 'max_charge') return 'max_charge'
  return 'balanced'
}

function readJsonFileIfExists(filePath: string) {
  if (!existsSync(filePath)) return {}
  try {
    return JSON.parse(readFileSync(filePath, 'utf-8'))
  } catch {
    return {}
  }
}

function resolveConfigPaths(tenantId: string) {
  const tenantConfigPath = join(getCwd(), '../energy_ml/configs/tenants', tenantId, 'user_config.json')
  const legacyConfigPath = join(getCwd(), '../energy_ml/configs/user_config.json')
  const configPath = tenantConfigPath
  const sourcePath = existsSync(tenantConfigPath) ? tenantConfigPath : legacyConfigPath
  return { tenantConfigPath, legacyConfigPath, configPath, sourcePath }
}

export default defineEventHandler(async (event: any) => {
  try {
    const body = await readBody(event)
    const tenant = await resolveTenantContext(event, { body })
    const { configPath, sourcePath } = resolveConfigPaths(tenant.id)

    const sanitizedBody = { ...body }
    delete (sanitizedBody as any).tenantId
    delete (sanitizedBody as any).tenant_id
    delete (sanitizedBody as any).clientId
    delete (sanitizedBody as any).client_id

    const currentConfig = {
      ...DEFAULT_CONFIG,
      ...readJsonFileIfExists(sourcePath),
    }

    const mergedConfig = {
      ...currentConfig,
      ...sanitizedBody,
    }

    mergedConfig.load_profile_type = normalizeLoadProfileType(mergedConfig.load_profile_type)
    mergedConfig.optimization_strategy = normalizeOptimizationStrategy(mergedConfig.optimization_strategy)

    const validation = validateConfiguration(mergedConfig)
    if (!validation.valid) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Configuration validation failed',
        data: { errors: validation.errors },
      })
    }

    const configDir = dirname(configPath)
    if (!existsSync(configDir)) {
      mkdirSync(configDir, { recursive: true })
    }

    const newConfig = {
      ...mergedConfig,
      last_updated: new Date().toISOString(),
      version: '1.0',
    }

    writeFileSync(configPath, JSON.stringify(newConfig, null, 2))

    await saveConfigHistory(tenant.id, newConfig, currentConfig)

    const needsRecalculation = detectSignificantChanges(currentConfig, newConfig)
    const recalculationResult = needsRecalculation ? await triggerRecalculation(tenant.id, newConfig) : null

    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      data: newConfig,
      validation: {
        errors: validation.errors,
        warnings: validation.warnings,
      },
      recalculation: {
        triggered: needsRecalculation,
        result: recalculationResult,
      },
      message: 'Configuration saved successfully',
    }
  } catch (error: any) {
    const errorData = error?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Save config error:', error)

    if (error?.statusCode) {
      throw error
    }

    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error saving configuration',
    })
  }
})

function validateConfiguration(config: any) {
  const errors: string[] = []
  const warnings: string[] = []

  if (!['LFP', 'Lead-Acid', 'VRFB'].includes(config.battery_type)) {
    errors.push('Invalid battery type')
  }

  if (!config.battery_capacity_kwh || config.battery_capacity_kwh <= 0 || config.battery_capacity_kwh > 1000) {
    errors.push('Battery capacity must be between 0.1 and 1000 kWh')
  }

  if (!config.battery_efficiency || config.battery_efficiency < 0.7 || config.battery_efficiency > 1.0) {
    errors.push('Battery efficiency must be between 0.7 and 1.0')
  }

  if (!['standard', 'multi-shift', '24/7', 'custom'].includes(config.load_profile_type)) {
    errors.push('Invalid load profile type')
  }

  if (!config.load_peak_kw || config.load_peak_kw <= 0 || config.load_peak_kw > 500) {
    errors.push('Load peak must be between 0.1 and 500 kW')
  }

  if (config.load_profile_type === 'custom' && config.load_custom_hourly) {
    if (!Array.isArray(config.load_custom_hourly) || config.load_custom_hourly.length !== 24) {
      errors.push('Custom hourly profile must have exactly 24 values')
    } else if (config.load_custom_hourly.some((val: number) => val < 0 || val > 1)) {
      errors.push('Custom hourly coefficients must be between 0 and 1')
    }
  }

  if (config.tariff_peak_hours_start >= config.tariff_peak_hours_end) {
    errors.push('Peak hours start must be before peak hours end')
  }

  if (config.tariff_peak_rate_uah_kwh <= config.tariff_off_peak_rate_uah_kwh) {
    warnings.push('Peak rate should be higher than off-peak rate for arbitrage')
  }

  if (Number(config.latitude) < -90 || Number(config.latitude) > 90) {
    errors.push('Latitude must be between -90 and 90')
  }

  if (Number(config.longitude) < -180 || Number(config.longitude) > 180) {
    errors.push('Longitude must be between -180 and 180')
  }

  const maxDischargePower = config.battery_capacity_kwh * (config.battery_c_rate_discharge || 1.0)
  if (maxDischargePower < config.load_peak_kw) {
    warnings.push(`Battery max discharge (${maxDischargePower.toFixed(1)}kW) < peak load (${config.load_peak_kw}kW)`)
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  }
}

async function saveConfigHistory(tenantId: string, newConfig: any, oldConfig: any) {
  try {
    const historyPath = join(getCwd(), '../energy_ml/configs/tenants', tenantId, 'config_history.jsonl')
    const historyDir = dirname(historyPath)
    if (!existsSync(historyDir)) {
      mkdirSync(historyDir, { recursive: true })
    }

    const historyEntry = {
      timestamp: new Date().toISOString(),
      new_config: newConfig,
      old_config: oldConfig,
      changes: detectChanges(oldConfig, newConfig),
    }

    appendFileSync(historyPath, `${JSON.stringify(historyEntry)}\n`)
  } catch (e) {
    console.warn('Failed to save config history:', e)
  }
}

function detectSignificantChanges(oldConfig: any, newConfig: any) {
  const significantFields = [
    'battery_type',
    'battery_capacity_kwh',
    'battery_efficiency',
    'load_profile_type',
    'load_peak_kw',
    'load_custom_hourly',
    'tariff_peak_rate_uah_kwh',
    'tariff_off_peak_rate_uah_kwh',
    'optimization_strategy',
    'latitude',
    'longitude',
    'solar_capacity_kw',
    'wind_capacity_kw',
  ]

  return significantFields.some((field) => {
    const oldVal = JSON.stringify(oldConfig[field])
    const newVal = JSON.stringify(newConfig[field])
    return oldVal !== newVal
  })
}

function detectChanges(oldConfig: any, newConfig: any) {
  const changes: { field: string, old_value: any, new_value: any }[] = []

  Object.keys(newConfig).forEach((key) => {
    if (key === 'last_updated' || key === 'version') return

    const oldVal = oldConfig[key]
    const newVal = newConfig[key]

    if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
      changes.push({
        field: key,
        old_value: oldVal,
        new_value: newVal,
      })
    }
  })

  return changes
}

async function triggerRecalculation(tenantId: string, config: any) {
  try {
    const triggerPath = join(getCwd(), '../energy_ml/configs/tenants', tenantId, 'recalculation_trigger.json')
    const triggerDir = dirname(triggerPath)
    if (!existsSync(triggerDir)) {
      mkdirSync(triggerDir, { recursive: true })
    }

    const triggerData = {
      timestamp: new Date().toISOString(),
      trigger_reason: 'configuration_save',
      config_hash: JSON.stringify(config).length.toString(),
      status: 'pending',
    }

    writeFileSync(triggerPath, JSON.stringify(triggerData, null, 2))

    return {
      success: true,
      trigger_id: triggerData.config_hash,
      message: 'Recalculation triggered successfully',
    }
  } catch (e: any) {
    return {
      success: false,
      error: e.message,
      message: 'Failed to trigger recalculation',
    }
  }
}
