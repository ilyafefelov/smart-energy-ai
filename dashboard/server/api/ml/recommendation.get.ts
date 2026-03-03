/**
 * Phase 4F ML Integration API Endpoint
 * 
 * Connects Nuxt Dashboard to Phase 4A-4F ML Pipeline for real-time recommendations
 */
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'
import { resolveTenantContext } from '../../utils/tenant-context'

const execAsync = promisify(exec)

// Types for API response
interface MLRecommendationResponse {
  success: boolean
  data?: {
    action: "BUY" | "SELL" | "HOLD"
    confidence: number // 0-1
    reasoning: string
    daily_forecast: Array<{
      hour: number
      action: string
      price_uah_mwh: number
      reasoning: string
    }>
    savings_estimate: {
      daily_uah: number
      monthly_uah: number
      annual_uah: number
    }
    battery_impact: {
      current_soc: number
      health_impact: number
      cycles_remaining: number
    }
    timestamp: string
    model_info: {
      version: string
      confidence_level: string
    }
  }
  error?: string
}

export default defineEventHandler(async (event): Promise<MLRecommendationResponse> => {
  try {
    const tenant = await resolveTenantContext(event)
    // Get the project root path (dashboard/../ = project root)
    const projectRoot = path.resolve(process.cwd(), '..')
    const pythonScript = path.join(projectRoot, 'ml_integration_api.py')
    const tenantConfigDir = path.join(projectRoot, 'energy_ml', 'configs', 'tenants', tenant.id)
    
    console.log(`[ML API] Project root: ${projectRoot}`)
    console.log(`[ML API] Python script: ${pythonScript}`)
    console.log(`[ML API] Calling ML pipeline...`)
    
    // Call the Python ML pipeline with enhanced features
    const { stdout, stderr } = await execAsync(
      `python "${pythonScript}" --action=get_recommendation --format=json --enhanced=true`,
      { 
        cwd: projectRoot,
        timeout: 30000, // 30 second timeout
        env: {
          ...process.env,
          ENERGY_ML_CONFIG_DIR: tenantConfigDir,
          ENERGY_ML_TENANT_ID: tenant.id,
        },
      }
    )
    
    if (stderr) {
      console.error(`[ML API] Python stderr: ${stderr}`)
    }
    
    console.log(`[ML API] Python stdout: ${stdout}`)
    
    // Parse the JSON response from Python
    const mlResponse = JSON.parse(stdout.trim())
    
    if (!mlResponse.success) {
      throw new Error(mlResponse.error || 'ML pipeline failed')
    }
    
    // Transform the response to match our interface
    const response: MLRecommendationResponse = {
      success: true,
      data: {
        action: mlResponse.action,
        confidence: mlResponse.confidence,
        reasoning: mlResponse.reasoning,
        daily_forecast: mlResponse.hourly_forecast?.map((item: any) => ({
          hour: item.hour,
          action: item.action,
          price_uah_mwh: item.savings_estimate * 1000, // Convert kWh to MWh
          reasoning: item.reasoning
        })) || [],
        savings_estimate: {
          daily_uah: mlResponse.estimated_savings * 24, // Estimate daily from hourly
          monthly_uah: mlResponse.estimated_savings * 24 * 30,
          annual_uah: mlResponse.estimated_savings * 24 * 365
        },
        battery_impact: {
          current_soc: mlResponse.battery_impact?.current_soc || 50,
          health_impact: mlResponse.battery_impact?.health_loss || 0,
          cycles_remaining: mlResponse.battery_impact?.cycles_remaining || 5000
        },
        timestamp: new Date().toISOString(),
        model_info: {
          version: "Phase4F-v1.0",
          confidence_level: mlResponse.confidence > 0.8 ? "High" : 
                           mlResponse.confidence > 0.6 ? "Medium" : "Low"
        }
      }
    }
    
    console.log(`[ML API] Returning recommendation: ${response.data.action} (${response.data.confidence})`)
    return response
    
  } catch (error) {
    console.error('[ML API] Error:', error)

    const errorData = (error as any)?.data
    if (errorData?.error?.code === 'INVALID_TENANT') {
      return {
        success: false,
        error: errorData.error.message,
      }
    }
    
    // Return error response
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
})