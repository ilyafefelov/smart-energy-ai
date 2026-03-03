/**
 * API Endpoint to Get Current User Optimization Strategy
 */
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'
import { existsSync, readFileSync } from 'fs'
import { eventHandler } from 'h3'

const execAsync = promisify(exec)
const pythonCommand = process.env.PYTHON_COMMAND || (process.platform === 'win32' ? 'python' : 'python3')

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

function resolveProjectRoot(): string {
  const cwd = process.cwd()
  if (existsSync(path.join(cwd, 'ml_integration_api.py'))) {
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

function fallbackStrategyFromConfig(projectRoot: string): OptimizationStrategyResponse['data'] | null {
  const configPath = path.join(projectRoot, 'energy_ml', 'configs', 'user_config.json')
  if (!existsSync(configPath)) return null

  try {
    const config = JSON.parse(readFileSync(configPath, 'utf-8'))
    const strategy = String(config?.optimization_strategy || 'balanced')
    const weightsByStrategy: Record<string, { earnings: number; battery_health: number; charge_availability: number }> = {
      max_earn: { earnings: 0.7, battery_health: 0.15, charge_availability: 0.15 },
      max_battery_health: { earnings: 0.15, battery_health: 0.7, charge_availability: 0.15 },
      max_charge: { earnings: 0.15, battery_health: 0.15, charge_availability: 0.7 },
      balanced: { earnings: 0.4, battery_health: 0.4, charge_availability: 0.2 },
    }

    return {
      strategy,
      description: `Strategy from user config: ${strategy}`,
      weights: weightsByStrategy[strategy] || weightsByStrategy.balanced,
      constraints: {
        min_soc: Number(config?.battery_soc_min ?? 0.1) * 100,
        max_cycles_per_day: 6,
      },
      available_strategies: ['max_earn', 'max_battery_health', 'max_charge', 'balanced'],
      current_cycles: 0,
      source: 'user_config_fallback',
    }
  } catch {
    return null
  }
}

export default eventHandler(async (): Promise<OptimizationStrategyResponse> => {
  const projectRoot = resolveProjectRoot()

  try {
    const pythonScript = path.join(projectRoot, 'ml_integration_api.py')
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
        available_strategies: mlResponse.available_strategies || ['max_earn', 'max_battery_health', 'max_charge', 'balanced'],
        current_cycles: Number(mlResponse.current_cycles || 0),
        source: 'ml_integration_api',
      }
    }
    
    console.log(`[Optimization API] Current strategy: ${response.data?.strategy}`)
    return response
    
  } catch (error) {
    console.error('[Optimization API] Error:', error)

    const fallback = fallbackStrategyFromConfig(projectRoot)
    if (fallback) {
      return {
        success: true,
        data: fallback,
      }
    }
    
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
})