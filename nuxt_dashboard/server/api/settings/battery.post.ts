/**
 * Battery Configuration API Endpoint
 * Updates battery settings and triggers ML pipeline recalculation
 */
import { execSync } from 'child_process'
import { writeFileSync, readFileSync, existsSync } from 'fs'
import { join } from 'path'

interface BatteryConfig {
  battery_type: 'LFP' | 'Lead-Acid' | 'VRFB'
  battery_capacity_kwh: number
  battery_efficiency: number
  battery_c_rate_charge?: number
  battery_c_rate_discharge?: number
  battery_dod_max?: number
  battery_soc_min?: number
  battery_soc_max?: number
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event) as BatteryConfig
    
    // Validate required fields
    if (!body.battery_type || !body.battery_capacity_kwh || !body.battery_efficiency) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Missing required battery configuration fields'
      })
    }
    
    // Validate battery type
    if (!['LFP', 'Lead-Acid', 'VRFB'].includes(body.battery_type)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid battery type'
      })
    }
    
    // Validate ranges
    if (body.battery_capacity_kwh <= 0 || body.battery_capacity_kwh > 1000) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Battery capacity must be between 0.1 and 1000 kWh'
      })
    }
    
    if (body.battery_efficiency < 0.7 || body.battery_efficiency > 1.0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Battery efficiency must be between 0.7 and 1.0'
      })
    }
    
    // Get current config
    const configPath = join(process.cwd(), '../energy_ml/configs/user_config.json')
    let currentConfig = {}
    
    if (existsSync(configPath)) {
      try {
        const configData = readFileSync(configPath, 'utf-8')
        currentConfig = JSON.parse(configData)
      } catch (e) {
        console.warn('Could not read existing config:', e)
      }
    }
    
    // Merge battery config with existing config
    const updatedConfig = {
      ...currentConfig,
      ...body,
      // Set defaults for advanced parameters if not provided
      battery_c_rate_charge: body.battery_c_rate_charge || getBatteryDefaults(body.battery_type).c_rate_charge,
      battery_c_rate_discharge: body.battery_c_rate_discharge || getBatteryDefaults(body.battery_type).c_rate_discharge,
      battery_dod_max: body.battery_dod_max || getBatteryDefaults(body.battery_type).dod_max,
      battery_soc_min: body.battery_soc_min || 0.1,
      battery_soc_max: body.battery_soc_max || 1.0,
    }
    
    // Save configuration
    try {
      writeFileSync(configPath, JSON.stringify(updatedConfig, null, 2))
    } catch (e) {
      throw createError({
        statusCode: 500,
        statusMessage: 'Failed to save battery configuration'
      })
    }
    
    // Trigger ML pipeline recalculation
    const triggerResult = await triggerPipelineRecalculation(updatedConfig)
    
    return {
      success: true,
      config: updatedConfig,
      recalculation: triggerResult,
      message: 'Battery configuration updated successfully'
    }
    
  } catch (error) {
    console.error('Battery config update error:', error)
    
    if (error.statusCode) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error updating battery configuration'
    })
  }
})

function getBatteryDefaults(batteryType: string) {
  const defaults = {
    'LFP': {
      c_rate_charge: 0.5,
      c_rate_discharge: 1.0,
      dod_max: 0.9
    },
    'Lead-Acid': {
      c_rate_charge: 0.2,
      c_rate_discharge: 0.3,
      dod_max: 0.5
    },
    'VRFB': {
      c_rate_charge: 0.25,
      c_rate_discharge: 0.25,
      dod_max: 1.0
    }
  }
  
  return defaults[batteryType] || defaults['LFP']
}

async function triggerPipelineRecalculation(config: any) {
  try {
    // Create recalculation trigger file
    const triggerPath = join(process.cwd(), '../energy_ml/configs/recalculation_trigger.json')
    const triggerData = {
      timestamp: new Date().toISOString(),
      trigger_reason: 'battery_config_update',
      config_hash: JSON.stringify(config).length.toString(), // Simple hash
      status: 'pending'
    }
    
    writeFileSync(triggerPath, JSON.stringify(triggerData, null, 2))
    
    // Try to execute Python recalculation script in background
    try {
      const pythonCommand = process.platform === 'win32' ? 'python' : 'python3'
      const scriptPath = join(process.cwd(), '../recalculate_pipeline.py')
      
      // Run in background - don't wait for completion
      setTimeout(() => {
        try {
          execSync(`${pythonCommand} "${scriptPath}"`, {
            cwd: join(process.cwd(), '..'),
            stdio: 'ignore',  // Run silently
            timeout: 5000     // 5 second timeout
          })
        } catch (e) {
          console.warn('Background recalculation failed:', e.message)
        }
      }, 100)
      
      return {
        success: true,
        jobId: triggerData.config_hash,
        status: 'triggered'
      }
    } catch (e) {
      return {
        success: false,
        error: 'Failed to trigger recalculation: ' + e.message,
        status: 'failed'
      }
    }
  } catch (e) {
    return {
      success: false,
      error: 'Failed to create trigger: ' + e.message,
      status: 'failed'
    }
  }
}