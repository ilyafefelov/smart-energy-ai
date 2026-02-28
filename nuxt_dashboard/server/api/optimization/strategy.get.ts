/**
 * API Endpoint to Get Current User Optimization Strategy
 */
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'

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
    // Get the project root path
    const projectRoot = path.resolve(process.cwd(), '..')
    const pythonScript = path.join(projectRoot, 'ml_integration_api.py')
    
    console.log(`[Optimization API] Getting current strategy`)
    
    // Call the Python ML pipeline
    const { stdout, stderr } = await execAsync(
      `python "${pythonScript}" --action=get_optimization_strategy`,
      {
        cwd: projectRoot,
        timeout: 15000 // 15 second timeout
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
    return response
    
  } catch (error) {
    console.error('[Optimization API] Error:', error)
    
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
})