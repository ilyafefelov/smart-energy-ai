/**
 * API Endpoint to Get Current User Optimization Strategy
 */
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'
import { existsSync, readFileSync } from 'fs'
import { eventHandler } from 'h3'
import { getTenantResponseMetadata, resolveTenantContext } from '../../utils/tenant-context'

const execAsync = promisify(exec)
const pythonCommand = process.env.PYTHON_COMMAND || (process.platform === 'win32' ? 'python' : 'python3')

const STRATEGY_NAMES = ['max_earn', 'max_battery_health', 'max_charge', 'balanced'] as const

type StrategyName = (typeof STRATEGY_NAMES)[number]

type StrategyWeights = {
  earnings: number
  battery_health: number
  charge_availability: number
}

type TenantErrorResponse = {
  success: false
  error: {
    code?: string
    message?: string
  }
  tenant?: {
    id: string | null
    validated: boolean
  }
  available_tenants?: string[]
  default_tenant_id?: string
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
    available_strategies: string[]
    current_cycles: number
    source?: string
  }
  error?: string
}

type StrategyGetHandlerResponse =
  | (OptimizationStrategyResponse & { tenant?: ReturnType<typeof getTenantResponseMetadata> })
  | TenantErrorResponse

function resolveProjectRoot(): string {
  const cwd = process.cwd()
  if (existsSync(path.join(cwd, 'workspace.yaml'))) {
    return cwd
  }
  return path.resolve(cwd, '..')
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

function resolveTenantConfig(projectRoot: string, tenantId: string, defaultTenantId: string) {
  const tenantConfigDir = path.join(projectRoot, 'energy_ml', 'configs', 'tenants', tenantId)
  const tenantConfigPath = path.join(tenantConfigDir, 'user_config.json')
  const legacyConfigDir = path.join(projectRoot, 'energy_ml', 'configs')
  const legacyConfigPath = path.join(legacyConfigDir, 'user_config.json')

  if (existsSync(tenantConfigPath)) {
    return { configDir: tenantConfigDir, configPath: tenantConfigPath }
  }

  if (tenantId === defaultTenantId) {
    return { configDir: legacyConfigDir, configPath: legacyConfigPath }
  }

  return { configDir: tenantConfigDir, configPath: tenantConfigPath }
}

function fallbackStrategyFromConfig(projectRoot: string, tenantId: string, defaultTenantId: string): OptimizationStrategyResponse['data'] | null {
  const { configPath } = resolveTenantConfig(projectRoot, tenantId, defaultTenantId)
  if (!existsSync(configPath)) return null

  try {
    const config = JSON.parse(readFileSync(configPath, 'utf-8'))
    const strategy = String(config?.optimization_strategy || 'balanced')
    const weightsByStrategy: Record<StrategyName, StrategyWeights> = {
      max_earn: { earnings: 0.7, battery_health: 0.15, charge_availability: 0.15 },
      max_battery_health: { earnings: 0.15, battery_health: 0.7, charge_availability: 0.15 },
      max_charge: { earnings: 0.15, battery_health: 0.15, charge_availability: 0.7 },
      balanced: { earnings: 0.4, battery_health: 0.4, charge_availability: 0.2 },
    }
    const strategyKey: StrategyName = strategy in weightsByStrategy
      ? strategy as StrategyName
      : 'balanced'

    return {
      strategy,
      description: `Strategy from user config: ${strategy}`,
      weights: weightsByStrategy[strategyKey],
      constraints: {
        min_soc: Number(config?.battery_soc_min ?? 0.1) * 100,
        max_cycles_per_day: 6,
      },
      available_strategies: [...STRATEGY_NAMES],
      current_cycles: 0,
      source: 'user_config_fallback',
    }
  } catch {
    return null
  }
}

export default eventHandler(async (event): Promise<StrategyGetHandlerResponse> => {
  const projectRoot = resolveProjectRoot()

  try {
    const tenant = await resolveTenantContext(event, { requireTrustedOverride: true })
    const tenantConfig = resolveTenantConfig(projectRoot, tenant.id, tenant.defaultTenantId)
    const pythonScript = path.join(projectRoot, 'scripts', 'ml_integration_api.py')
    if (!existsSync(pythonScript)) {
      throw new Error(`Python script not found at ${pythonScript}`)
    }
    
    console.log(`[Optimization API] Getting current strategy`)
    
    // Call the Python ML pipeline
    const { stdout, stderr } = await execAsync(
      `${pythonCommand} "${pythonScript}" --action=get_optimization_strategy --format=json`,
      {
        cwd: projectRoot,
        timeout: 15000, // 15 second timeout
        maxBuffer: 1024 * 1024,
        env: {
          ...process.env,
          ENERGY_ML_CONFIG_DIR: tenantConfig.configDir,
          ENERGY_ML_TENANT_ID: tenant.id,
        },
      }
    )
    
    if (stderr) {
      console.warn(`[Optimization API] Python stderr: ${stderr}`)
    }
    
    console.log(`[Optimization API] Python stdout: ${stdout}`)
    
    // Parse the JSON response from Python
    const mlResponse = parseJsonFromPythonStdout(stdout)
    
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
        available_strategies: mlResponse.available_strategies || [...STRATEGY_NAMES],
        current_cycles: Number(mlResponse.current_cycles || 0),
        source: 'ml_integration_api',
      }
    }
    
    console.log(`[Optimization API] Current strategy: ${response.data?.strategy}`)
    return {
      ...response,
      tenant: getTenantResponseMetadata(tenant),
    }
    
  } catch (error) {
    console.error('[Optimization API] Error:', error)

    const errorData = typeof error === 'object' && error !== null && 'data' in error
      ? (error as { data?: TenantErrorResponse }).data
      : undefined
    if (errorData?.error?.code === 'INVALID_TENANT' || errorData?.error?.code === 'TENANT_AUTH_REQUIRED') {
      return errorData
    }

    const tenant = await resolveTenantContext(event).catch(() => null)
    const fallback = tenant ? fallbackStrategyFromConfig(projectRoot, tenant.id, tenant.defaultTenantId) : null
    if (fallback) {
      return {
        success: true,
        data: fallback,
        tenant: tenant ? getTenantResponseMetadata(tenant) : undefined,
      }
    }
    
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
})