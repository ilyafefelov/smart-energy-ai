/**
 * Current Configuration API Endpoint
 * Returns the current user configuration
 */
import { readFileSync, existsSync } from 'fs'
import { join } from 'path'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

export default defineEventHandler(async (event) => {
  try {
    const tenant = await resolveTenantContext(event)
    const tenantConfigPath = join(process.cwd(), '../energy_ml/configs/tenants', tenant.id, 'user_config.json')
    const legacyConfigPath = join(process.cwd(), '../energy_ml/configs/user_config.json')
    const configPath = existsSync(tenantConfigPath) ? tenantConfigPath : legacyConfigPath
    
    // Default configuration
    const defaultConfig = {
      // Battery Configuration
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
      
      // Load Profile Configuration
      load_profile_type: 'standard',
      load_peak_kw: 10.0,
      load_base_kw: 2.0,
      load_custom_hourly: null,
      load_seasonal_variation: 0.2,
      load_weekend_factor: 0.6,
      load_night_factor: 0.3,
      
      // Tariff Configuration
      tariff_region: 'ukraine',
      tariff_peak_hours_start: 6,
      tariff_peak_hours_end: 23,
      tariff_peak_rate_uah_kwh: 12.5,
      tariff_off_peak_rate_uah_kwh: 8.0,
      
      // ML Configuration
      ml_retrain_frequency_days: 7,
      ml_confidence_threshold: 0.7,
      ml_model_type: 'ensemble',
      ml_lookback_hours: 168,
      ml_forecast_horizon_hours: 24,
      
      // Dashboard Preferences
      dashboard_refresh_seconds: 30,
      dashboard_show_degradation_cost: true,
      dashboard_show_arbitrage_opportunities: true,
      dashboard_currency_symbol: '₴',
      dashboard_language: 'en'
    }
    
    let currentConfig = defaultConfig
    
    // Try to load saved configuration
    if (existsSync(configPath)) {
      try {
        const configData = readFileSync(configPath, 'utf-8')
        const savedConfig = JSON.parse(configData)
        
        // Merge saved config with defaults (in case new fields were added)
        currentConfig = { ...defaultConfig, ...savedConfig }
      } catch (e) {
        console.warn('Could not parse saved config, using defaults:', e)
      }
    }
    
    // Calculate derived metrics
    const batterySpecs = getBatterySpecs(currentConfig.battery_type)
    const arbitrageMetrics = calculateArbitrageMetrics(currentConfig, batterySpecs)
    
    return {
      success: true,
      tenant: getTenantResponseMetadata(tenant),
      data: currentConfig,
      metadata: {
        config_scope: existsSync(tenantConfigPath) ? 'tenant' : 'legacy_default',
        tenant_config_path: tenantConfigPath,
        config_file_exists: existsSync(configPath),
        last_modified: existsSync(configPath) ? getFileModifiedTime(configPath) : null,
        battery_specs: batterySpecs,
        arbitrage_metrics: arbitrageMetrics
      },
      timestamp: new Date().toISOString()
    }
    
  } catch (error) {
    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return errorData
    }

    console.error('Current config fetch error:', error)
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error fetching current configuration'
    })
  }
})

function getBatterySpecs(batteryType: string) {
  const specs = {
    'LFP': {
      full_name: 'Lithium Iron Phosphate',
      expected_cycles: 8000,
      degradation_cost_uah_per_cycle: 16.25,
      recommended_dod: 0.9,
      efficiency_typical: 0.95
    },
    'Lead-Acid': {
      full_name: 'Lead-Acid Deep Cycle',
      expected_cycles: 600,
      degradation_cost_uah_per_cycle: 45.83,
      recommended_dod: 0.5,
      efficiency_typical: 0.85
    },
    'VRFB': {
      full_name: 'Vanadium Redox Flow Battery',
      expected_cycles: 20000,
      degradation_cost_uah_per_cycle: 55.0,
      recommended_dod: 1.0,
      efficiency_typical: 0.75
    }
  }
  
  return specs[batteryType] || specs['LFP']
}

function calculateArbitrageMetrics(config: any, batterySpecs: any) {
  const usableCapacity = config.battery_capacity_kwh * config.battery_dod_max
  const priceSpread = config.tariff_peak_rate_uah_kwh - config.tariff_off_peak_rate_uah_kwh
  
  const dailyArbitrageGross = usableCapacity * priceSpread * config.battery_efficiency
  const degradationCost = batterySpecs.degradation_cost_uah_per_cycle * config.battery_capacity_kwh / 10 // Normalized
  const dailyProfitNet = dailyArbitrageGross - degradationCost
  
  return {
    daily_arbitrage_gross_uah: Math.round(dailyArbitrageGross * 100) / 100,
    daily_degradation_cost_uah: Math.round(degradationCost * 100) / 100,
    daily_profit_net_uah: Math.round(dailyProfitNet * 100) / 100,
    annual_profit_uah: Math.round(dailyProfitNet * 365),
    payback_period_years: dailyProfitNet > 0 
      ? Math.round((config.battery_capacity_kwh * 13000) / (dailyProfitNet * 365) * 10) / 10
      : null,
    usable_capacity_kwh: Math.round(usableCapacity * 100) / 100,
    price_spread_uah: priceSpread
  }
}

function getFileModifiedTime(filePath: string): string | null {
  try {
    const stats = require('fs').statSync(filePath)
    return stats.mtime.toISOString()
  } catch (e) {
    return null
  }
}