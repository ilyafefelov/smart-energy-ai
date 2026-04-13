/**
 * API Endpoint for User Optimization Strategy Management
 * 
 * Handles setting and getting user optimization preferences:
 * - Max Earn: Maximize financial returns
 * - Max Battery Health: Minimize degradation
 * - Max Charge: Maintain high charge availability
 * - Balanced: Balance all factors
 */
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'
import { existsSync } from 'fs'
import { eventHandler, readBody } from 'h3'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const execAsync = promisify(exec)
const pythonCommand = process.env.PYTHON_COMMAND || (process.platform === 'win32' ? 'python' : 'python3')

interface OptimizationStrategyRequest {
  strategy: "max_earn" | "max_battery_health" | "max_charge" | "balanced"
  custom_weights?: {
    earnings?: number
    battery_health?: number
    charge_availability?: number
  }
}

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
    applied_at: string
  }
  error?: string
}

function resolveProjectRoot(): string {
  const cwd = process.cwd()
  if (existsSync(path.join(cwd, 'workspace.yaml'))) {
    return cwd
  }
  return path.resolve(cwd, '..')
}

function resolveTenantConfig(projectRoot: string, tenantId: string, defaultTenantId: string) {
  const tenantConfigDir = path.join(projectRoot, 'energy_ml', 'configs', 'tenants', tenantId)
  const tenantConfigPath = path.join(tenantConfigDir, 'user_config.json')
  const legacyConfigDir = path.join(projectRoot, 'energy_ml', 'configs')

  if (existsSync(tenantConfigPath)) {
    return tenantConfigDir
  }

  return tenantId === defaultTenantId ? legacyConfigDir : tenantConfigDir
}

function parseJsonFromPythonStdout(stdout: string): any {
  const trimmed = stdout.trim()
  if (!trimmed) {
    throw new Error('Empty response from Python process')
  }

  try {
    return JSON.parse(trimmed)
  } catch {
    const lines = trimmed.split(/\r?\n/).reverse()
    for (const line of lines) {
      try {
        return JSON.parse(line)
      } catch {
        continue
      }
    }
  }

  throw new Error('Unable to parse Python JSON response')
}

export default eventHandler(async (event): Promise<OptimizationStrategyResponse & { tenant?: ReturnType<typeof getTenantResponseMetadata> }> => {
  try {
    const body = await readBody(event) as OptimizationStrategyRequest
    const tenant = await resolveTenantContext(event, {
      body: body as Record<string, any>,
      requireTrustedOverride: true,
    })
    
    if (!body.strategy) {
      throw new Error('Strategy is required')
    }
    
    const projectRoot = resolveProjectRoot()
    const tenantConfigDir = resolveTenantConfig(projectRoot, tenant.id, tenant.defaultTenantId)
    const pythonScript = path.join(projectRoot, 'scripts', 'ml_integration_api.py')
    if (!existsSync(pythonScript)) {
      throw new Error(`Python script not found at ${pythonScript}`)
    }
    
    console.log(`[Optimization API] Setting strategy: ${body.strategy}`)
    
    // Prepare command arguments
    let command = `${pythonCommand} "${pythonScript}" --action=set_optimization_strategy --strategy=${body.strategy} --format=json`
    
    // Add custom weights if provided
    if (body.custom_weights) {
      const weightsJson = JSON.stringify(body.custom_weights).replace(/"/g, '\\"')
      command += ` --custom_weights="${weightsJson}"`
    }
    
    // Call the Python ML pipeline
    const { stdout, stderr } = await execAsync(command, {
      cwd: projectRoot,
      timeout: 15000, // 15 second timeout
      maxBuffer: 1024 * 1024,
      env: {
        ...process.env,
        ENERGY_ML_CONFIG_DIR: tenantConfigDir,
        ENERGY_ML_TENANT_ID: tenant.id,
      },
    })
    
    if (stderr) {
      console.warn(`[Optimization API] Python stderr: ${stderr}`)
    }
    
    console.log(`[Optimization API] Python stdout: ${stdout}`)
    
    // Parse the JSON response from Python
    const mlResponse = parseJsonFromPythonStdout(stdout)
    
    if (!mlResponse.success) {
      throw new Error(mlResponse.error || 'Failed to set optimization strategy')
    }
    
    // Transform response
    const response: OptimizationStrategyResponse = {
      success: true,
      data: {
        strategy: mlResponse.strategy,
        description: mlResponse.description || `Strategy: ${mlResponse.strategy}`,
        weights: mlResponse.weights || { earnings: 0.33, battery_health: 0.33, charge_availability: 0.33 },
        constraints: mlResponse.constraints || { min_soc: 20, max_cycles_per_day: 6 },
        applied_at: new Date().toISOString()
      }
    }
    
    console.log(`[Optimization API] Strategy set successfully: ${body.strategy}`)
    return {
      ...response,
      tenant: getTenantResponseMetadata(tenant),
    }
    
  } catch (error) {
    console.error('[Optimization API] Error:', error)

    const errorData = (error as { data?: { error?: { code?: string } } })?.data
    if (errorData?.error?.code === 'INVALID_TENANT' || errorData?.error?.code === 'TENANT_AUTH_REQUIRED') {
      return errorData
    }
    
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
})