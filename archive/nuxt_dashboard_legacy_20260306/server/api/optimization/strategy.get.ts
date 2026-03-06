/**
 * API Endpoint to Get Current User Optimization Strategy
 */
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'
import { existsSync, readFileSync } from 'fs'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const execAsync = promisify(exec)

interface OptimizationStrategyResponse {
  success: boolean
  data?: {
    strategy: string
    description: string
    weights: {
      earnings: number
      battery_health: number
      charge_availability: number
    }
    constraints: {
      min_soc: number
      max_cycles_per_day: number
    }
    available_strategies: string[]
    current_cycles: number
  }
  error?: string
}

export default defineEventHandler(async (event): Promise<OptimizationStrategyResponse> => {
  try {
    const tenant = await resolveTenantContext(event, { requireTrustedOverride: true })
    // Get the project root path
    const projectRoot = path.resolve(process.cwd(), '..')
    const pythonScript = path.join(projectRoot, 'ml_integration_api.py')
    const tenantConfigDir = path.join(projectRoot, 'energy_ml', 'configs', 'tenants', tenant.id)
    const tenantConfigPath = path.join(tenantConfigDir, 'user_config.json')
    const legacyConfigDir = path.join(projectRoot, 'energy_ml', 'configs')
    const legacyConfigPath = path.join(legacyConfigDir, 'user_config.json')
    const configDir = existsSync(tenantConfigPath) || tenant.id !== tenant.defaultTenantId ? tenantConfigDir : legacyConfigDir
    
    console.log(`[Optimization API] Getting current strategy`)
    
    // Call the Python ML pipeline
    const { stdout, stderr } = await execAsync(
      `python "${pythonScript}" --action=get_optimization_strategy`,
      {
        cwd: projectRoot,
        timeout: 15000, // 15 second timeout
        env: {
          ...process.env,
          ENERGY_ML_CONFIG_DIR: configDir,
          ENERGY_ML_TENANT_ID: tenant.id,
        },
      }
    )
    
    if (stderr) {
      console.warn(`[Optimization API] Python stderr: ${stderr}`)
    }
    
    console.log(`[Optimization API] Python stdout: ${stdout}`)
    
    // Parse the JSON response from Python
    const mlResponse = JSON.parse(stdout.trim())
    
    if (!mlResponse.success) {
      throw new Error(mlResponse.error || 'Failed to get optimization strategy')
    }
    
    // Transform response
    const response: OptimizationStrategyResponse = {
      success: true,
      data: {
        strategy: mlResponse.strategy || 'balanced',
        description: mlResponse.description || 'Balanced optimization strategy',
        weights: mlResponse.weights || { earnings: 0.4, battery_health: 0.4, charge_availability: 0.2 },
        constraints: mlResponse.constraints || { min_soc: 30, max_cycles_per_day: 6 },
        available_strategies: mlResponse.available_strategies || ['max_earn', 'max_battery_health', 'max_charge', 'balanced'],
        current_cycles: mlResponse.current_cycles || 0
      }
    }
    
    console.log(`[Optimization API] Current strategy: ${response.data?.strategy}`)
    return {
      ...response,
      tenant: getTenantResponseMetadata(tenant),
    } as OptimizationStrategyResponse
    
  } catch (error) {
    console.error('[Optimization API] Error:', error)

    const errorData = (error as { data?: { error?: { code?: string } } })?.data
    if (errorData?.error?.code === 'INVALID_TENANT' || errorData?.error?.code === 'TENANT_AUTH_REQUIRED') {
      return errorData as OptimizationStrategyResponse
    }

    try {
      const tenant = await resolveTenantContext(event)
      const projectRoot = path.resolve(process.cwd(), '..')
      const tenantConfigPath = path.join(projectRoot, 'energy_ml', 'configs', 'tenants', tenant.id, 'user_config.json')
      const legacyConfigPath = path.join(projectRoot, 'energy_ml', 'configs', 'user_config.json')
      const configPath = existsSync(tenantConfigPath) ? tenantConfigPath : tenant.id === tenant.defaultTenantId ? legacyConfigPath : tenantConfigPath
      if (existsSync(configPath)) {
        const config = JSON.parse(readFileSync(configPath, 'utf-8'))
        const strategy = String(config?.optimization_strategy || 'balanced')
        return {
          success: true,
          data: {
            strategy,
            description: `Strategy from user config: ${strategy}`,
            weights: {
              earnings: strategy === 'max_earn' ? 0.7 : strategy === 'balanced' ? 0.4 : 0.15,
              battery_health: strategy === 'max_battery_health' ? 0.7 : strategy === 'balanced' ? 0.4 : 0.15,
              charge_availability: strategy === 'max_charge' ? 0.7 : strategy === 'balanced' ? 0.2 : 0.15,
            },
            constraints: {
              min_soc: Number(config?.battery_soc_min ?? 0.1) * 100,
              max_cycles_per_day: 6,
            },
            available_strategies: ['max_earn', 'max_battery_health', 'max_charge', 'balanced'],
            current_cycles: 0,
          },
          tenant: getTenantResponseMetadata(tenant),
        } as OptimizationStrategyResponse
      }
    } catch {
      // Fall through to generic error response.
    }
    
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
})