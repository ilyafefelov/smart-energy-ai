/**
 * Load Profile Configuration API Endpoint
 * Updates load profile settings and triggers ML pipeline recalculation
 */
import { execSync } from 'child_process'
import { writeFileSync, readFileSync, existsSync } from 'fs'
import { join } from 'path'

interface LoadProfileConfig {
  load_profile_type: 'standard' | 'multi_shift' | '24_7' | 'custom'
  load_peak_kw: number
  load_base_kw?: number
  load_custom_hourly?: number[]
  load_seasonal_variation?: number
  load_weekend_factor?: number
  load_night_factor?: number
}

type LoadProfileDefaults = {
  base_kw: number
  seasonal_variation: number
  weekend_factor: number
  night_factor: number
  hourly_coefficients: number[]
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

function isHttpErrorLike(error: unknown): error is { statusCode: number } {
  return typeof error === 'object' && error !== null && 'statusCode' in error
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event) as LoadProfileConfig
    
    // Validate required fields
    if (!body.load_profile_type || !body.load_peak_kw) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Missing required load profile configuration fields'
      })
    }
    
    // Validate profile type
    if (!['standard', 'multi_shift', '24_7', 'custom'].includes(body.load_profile_type)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid load profile type'
      })
    }
    
    // Validate peak load
    if (body.load_peak_kw <= 0 || body.load_peak_kw > 500) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Load peak must be between 0.1 and 500 kW'
      })
    }
    
    // Validate custom hourly profile if provided
    if (body.load_profile_type === 'custom' && body.load_custom_hourly) {
      if (body.load_custom_hourly.length !== 24) {
        throw createError({
          statusCode: 400,
          statusMessage: 'Custom hourly profile must have exactly 24 values'
        })
      }
      
      if (body.load_custom_hourly.some(val => val < 0 || val > 1)) {
        throw createError({
          statusCode: 400,
          statusMessage: 'Custom hourly coefficients must be between 0 and 1'
        })
      }
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
    
    // Get load profile template defaults
    const templateDefaults = getLoadProfileDefaults(body.load_profile_type)
    
    // Merge load profile config with existing config
    const updatedConfig = {
      ...currentConfig,
      ...body,
      // Set defaults for optional parameters
      load_base_kw: body.load_base_kw || templateDefaults.base_kw,
      load_seasonal_variation: body.load_seasonal_variation || templateDefaults.seasonal_variation,
      load_weekend_factor: body.load_weekend_factor || templateDefaults.weekend_factor,
      load_night_factor: body.load_night_factor || templateDefaults.night_factor,
      // Use template hourly coefficients if not custom
      load_custom_hourly: body.load_profile_type === 'custom' 
        ? body.load_custom_hourly || new Array(24).fill(0.5)
        : templateDefaults.hourly_coefficients
    }
    
    // Save configuration
    try {
      writeFileSync(configPath, JSON.stringify(updatedConfig, null, 2))
    } catch (e) {
      throw createError({
        statusCode: 500,
        statusMessage: 'Failed to save load profile configuration'
      })
    }
    
    // Trigger ML pipeline recalculation
    const triggerResult = await triggerPipelineRecalculation(updatedConfig)
    
    return {
      success: true,
      config: updatedConfig,
      recalculation: triggerResult,
      message: 'Load profile configuration updated successfully'
    }
    
  } catch (error) {
    console.error('Load profile config update error:', error)
    
    if (isHttpErrorLike(error)) {
      throw error
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Internal server error updating load profile configuration'
    })
  }
})

function getLoadProfileDefaults(profileType: LoadProfileConfig['load_profile_type']): LoadProfileDefaults {
  const defaults: Record<LoadProfileConfig['load_profile_type'], LoadProfileDefaults> = {
    'standard': {
      base_kw: 2.0,
      seasonal_variation: 0.15,
      weekend_factor: 0.3,
      night_factor: 0.2,
      hourly_coefficients: [
        // Hour 0-5: Night (low load)
        0.2, 0.2, 0.2, 0.2, 0.2, 0.3,
        // Hour 6-8: Morning ramp-up
        0.4, 0.6, 0.8,
        // Hour 9-17: Business hours (high load)
        1.0, 1.0, 0.9, 0.8, 0.9, 1.0, 1.0, 0.9, 0.8,
        // Hour 18-23: Evening wind-down
        0.6, 0.5, 0.4, 0.3, 0.3, 0.2
      ]
    },
    'multi_shift': {
      base_kw: 3.0,
      seasonal_variation: 0.25,
      weekend_factor: 0.7,
      night_factor: 0.8,
      hourly_coefficients: [
        // Hour 0-5: Night shift
        0.8, 0.8, 0.7, 0.6, 0.5, 0.4,
        // Hour 6-13: Day shift (peak)
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
        // Hour 14-21: Shift change + break
        0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3,
        // Hour 22-23: Night shift start
        0.9, 0.9
      ]
    },
    '24_7': {
      base_kw: 18.0,
      seasonal_variation: 0.1,
      weekend_factor: 0.95,
      night_factor: 0.9,
      hourly_coefficients: [
        // Minimal variation throughout day
        0.9, 0.9, 0.9, 0.9, 0.9, 0.95,
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
        1.0, 1.0, 0.95, 0.95, 0.9, 0.9
      ]
    },
    'custom': {
      base_kw: 2.0,
      seasonal_variation: 0.2,
      weekend_factor: 0.6,
      night_factor: 0.5,
      hourly_coefficients: new Array(24).fill(0.5)
    }
  }
  
  return defaults[profileType] || defaults['standard']
}

async function triggerPipelineRecalculation(config: any) {
  try {
    // Create recalculation trigger file
    const triggerPath = join(process.cwd(), '../energy_ml/configs/recalculation_trigger.json')
    const triggerData = {
      timestamp: new Date().toISOString(),
      trigger_reason: 'load_profile_config_update',
      config_hash: JSON.stringify(config).length.toString(),
      status: 'pending'
    }
    
    writeFileSync(triggerPath, JSON.stringify(triggerData, null, 2))
    
    // Try to execute Python recalculation script in background
    try {
      const pythonCommand = process.platform === 'win32' ? 'python' : 'python3'
      const scriptPath = join(process.cwd(), '../scripts/recalculate_pipeline.py')
      
      // Run in background - don't wait for completion
      setTimeout(() => {
        try {
          execSync(`${pythonCommand} "${scriptPath}"`, {
            cwd: join(process.cwd(), '..'),
            stdio: 'ignore',  // Run silently
            timeout: 5000     // 5 second timeout
          })
        } catch (e) {
          console.warn('Background recalculation failed:', getErrorMessage(e, 'unknown error'))
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
        error: 'Failed to trigger recalculation: ' + getErrorMessage(e, 'unknown error'),
        status: 'failed'
      }
    }
  } catch (e) {
    return {
      success: false,
      error: 'Failed to create trigger: ' + getErrorMessage(e, 'unknown error'),
      status: 'failed'
    }
  }
}