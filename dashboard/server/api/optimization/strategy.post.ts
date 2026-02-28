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

const execAsync = promisify(exec)

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

export default defineEventHandler(async (event): Promise<OptimizationStrategyResponse> => {
  try {
    const body = await readBody(event) as OptimizationStrategyRequest
    
    if (!body.strategy) {
      throw new Error('Strategy is required')
    }
    
    // Get the project root path
    const projectRoot = path.resolve(process.cwd(), '..')
    const pythonScript = path.join(projectRoot, 'ml_integration_api.py')
    
    console.log(`[Optimization API] Setting strategy: ${body.strategy}`)
    
    // Prepare command arguments
    let command = `python "${pythonScript}" --action=set_optimization_strategy --strategy=${body.strategy}`
    
    // Add custom weights if provided
    if (body.custom_weights) {
      const weightsJson = JSON.stringify(body.custom_weights).replace(/"/g, '\\"')
      command += ` --custom_weights="${weightsJson}"`
    }
    
    // Call the Python ML pipeline
    const { stdout, stderr } = await execAsync(command, {
      cwd: projectRoot,
      timeout: 15000 // 15 second timeout
    })
    
    if (stderr) {
      console.warn(`[Optimization API] Python stderr: ${stderr}`)
    }
    
    console.log(`[Optimization API] Python stdout: ${stdout}`)
    
    // Parse the JSON response from Python
    const mlResponse = JSON.parse(stdout.trim())
    
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
    return response
    
  } catch (error) {
    console.error('[Optimization API] Error:', error)
    
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
})