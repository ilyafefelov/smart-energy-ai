/**
 * Save Configuration API Endpoint
 * Saves user configuration and triggers recalculation
 */
import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    
    // Validation
    const validation = validateConfiguration(body)
    if (!validation.valid) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Configuration validation failed',
        data: { errors: validation.errors }
      })
    }
    
    const configPath = join(process.cwd(), '../energy_ml/configs/user_config.json')
    const configDir = dirname(configPath)
    
    // Ensure config directory exists
    if (!existsSync(configDir)) {
      mkdirSync(configDir, { recursive: true })
    }
    
    // Get current config for comparison
    let currentConfig = {}
    if (existsSync(configPath)) {
      try {
        const currentData = readFileSync(configPath, 'utf-8')
        currentConfig = JSON.parse(currentData)
      } catch (e) {
        console.warn('Could not read current config:', e)
      }
    }
    
    // Prepare new configuration with timestamp
    const newConfig = {
      ...body,
      last_updated: new Date().toISOString(),
      version: '1.0'
    }
    
    // Save configuration
    try {
      writeFileSync(configPath, JSON.stringify(newConfig, null, 2))
    } catch (e) {
      throw createError({
        statusCode: 500,
        statusMessage: 'Failed to save configuration file'
      })
    }
    
    // Save to history
    await saveConfigHistory(newConfig, currentConfig)
    
    // Detect significant changes that require recalculation
    const needsRecalculation = detectSignificantChanges(currentConfig, newConfig)
    
    let recalculationResult = null
    if (needsRecalculation) {
      recalculationResult = await triggerRecalculation(newConfig)
    }
    
    return {
      success: true,
      data: newConfig,
      validation: {
        errors: validation.errors,
        warnings: validation.warnings
      },
      recalculation: {
        triggered: needsRecalculation,
        result: recalculationResult
      },
      message: 'Configuration saved successfully'
    }
    
  } catch (error) {
    console.error('Save config error:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error saving configuration'
    })
  }
})

function validateConfiguration(config: any) {
  const errors: string[] = []
  const warnings: string[] = []
  
  // Battery validation
  if (!['LFP', 'Lead-Acid', 'VRFB'].includes(config.battery_type)) {
    errors.push('Invalid battery type')
  }
  
  if (!config.battery_capacity_kwh || config.battery_capacity_kwh <= 0 || config.battery_capacity_kwh > 1000) {
    errors.push('Battery capacity must be between 0.1 and 1000 kWh')
  }
  
  if (!config.battery_efficiency || config.battery_efficiency < 0.7 || config.battery_efficiency > 1.0) {
    errors.push('Battery efficiency must be between 0.7 and 1.0')
  }
  
  // Load profile validation
  if (!['standard', 'multi_shift', '24_7', 'custom'].includes(config.load_profile_type)) {
    errors.push('Invalid load profile type')
  }
  
  if (!config.load_peak_kw || config.load_peak_kw <= 0 || config.load_peak_kw > 500) {
    errors.push('Load peak must be between 0.1 and 500 kW')
  }
  
  // Custom hourly validation
  if (config.load_profile_type === 'custom' && config.load_custom_hourly) {
    if (!Array.isArray(config.load_custom_hourly) || config.load_custom_hourly.length !== 24) {
      errors.push('Custom hourly profile must have exactly 24 values')
    } else if (config.load_custom_hourly.some((val: number) => val < 0 || val > 1)) {
      errors.push('Custom hourly coefficients must be between 0 and 1')
    }
  }
  
  // Tariff validation
  if (config.tariff_peak_hours_start >= config.tariff_peak_hours_end) {
    errors.push('Peak hours start must be before peak hours end')
  }
  
  if (config.tariff_peak_rate_uah_kwh <= config.tariff_off_peak_rate_uah_kwh) {
    warnings.push('Peak rate should be higher than off-peak rate for arbitrage')
  }
  
  // Battery-load compatibility
  const maxDischargePower = config.battery_capacity_kwh * (config.battery_c_rate_discharge || 1.0)
  if (maxDischargePower < config.load_peak_kw) {
    warnings.push(`Battery max discharge (${maxDischargePower.toFixed(1)}kW) < peak load (${config.load_peak_kw}kW)`)
  }
  
  return {
    valid: errors.length === 0,
    errors,
    warnings
  }
}

async function saveConfigHistory(newConfig: any, oldConfig: any) {
  try {
    const historyPath = join(process.cwd(), '../energy_ml/configs/config_history.jsonl')
    
    const historyEntry = {
      timestamp: new Date().toISOString(),
      new_config: newConfig,
      old_config: oldConfig,
      changes: detectChanges(oldConfig, newConfig)
    }
    
    const historyLine = JSON.stringify(historyEntry) + '\n'
    require('fs').appendFileSync(historyPath, historyLine)
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
    'tariff_off_peak_rate_uah_kwh'
  ]
  
  return significantFields.some(field => {
    const oldVal = JSON.stringify(oldConfig[field])
    const newVal = JSON.stringify(newConfig[field])
    return oldVal !== newVal
  })
}

function detectChanges(oldConfig: any, newConfig: any) {
  const changes: { field: string, old_value: any, new_value: any }[] = []
  
  Object.keys(newConfig).forEach(key => {
    if (key === 'last_updated' || key === 'version') return
    
    const oldVal = oldConfig[key]
    const newVal = newConfig[key]
    
    if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
      changes.push({
        field: key,
        old_value: oldVal,
        new_value: newVal
      })
    }
  })
  
  return changes
}

async function triggerRecalculation(config: any) {
  try {
    // Create trigger file
    const triggerPath = join(process.cwd(), '../energy_ml/configs/recalculation_trigger.json')
    const triggerData = {
      timestamp: new Date().toISOString(),
      trigger_reason: 'configuration_save',
      config_hash: JSON.stringify(config).length.toString(),
      status: 'pending'
    }
    
    writeFileSync(triggerPath, JSON.stringify(triggerData, null, 2))
    
    return {
      success: true,
      trigger_id: triggerData.config_hash,
      message: 'Recalculation triggered successfully'
    }
  } catch (e) {
    return {
      success: false,
      error: e.message,
      message: 'Failed to trigger recalculation'
    }
  }
}