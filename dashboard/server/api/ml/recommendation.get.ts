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

interface PriceForecastPoint {
  hour: number
  price: number
}

interface PricesCurrentResponse {
  success?: boolean
  prices?: {
    forecast?: {
      next24h?: PriceForecastPoint[]
    }
  }
}

function toFiniteNumber(value: unknown): number | null {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : null
}

function buildHourlyPriceMap(pricesPayload: PricesCurrentResponse | null | undefined): Map<number, number> {
  const map = new Map<number, number>()
  const rows = pricesPayload?.prices?.forecast?.next24h
  if (!Array.isArray(rows)) {
    return map
  }

  for (const row of rows) {
    const hour = toFiniteNumber((row as any)?.hour)
    const price = toFiniteNumber((row as any)?.price)
    if (hour == null || price == null) {
      continue
    }
    if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
      continue
    }
    map.set(hour, price)
  }

  return map
}

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
    
    let pricesPayload: PricesCurrentResponse | null = null
    try {
      pricesPayload = await $fetch<PricesCurrentResponse>('/api/prices/current')
    } catch (pricesError) {
      console.warn('[ML API] Failed to load /api/prices/current for hourly forecast price mapping:', pricesError)
    }

    const hourlyPriceMap = buildHourlyPriceMap(pricesPayload)
    const dailySavings = toFiniteNumber(mlResponse.daily_savings_estimate) ?? 0
    const monthlySavings = toFiniteNumber(mlResponse.monthly_savings_estimate) ?? (dailySavings * 30)
    const annualSavings = toFiniteNumber(mlResponse.annual_savings_estimate) ?? (dailySavings * 365)

    // Transform the response to match our interface
    const response: MLRecommendationResponse = {
      success: true,
      data: {
        action: mlResponse.action,
        confidence: mlResponse.confidence,
        reasoning: mlResponse.reasoning,
        daily_forecast: mlResponse.hourly_forecast?.map((item: any) => {
          const itemHour = toFiniteNumber(item?.hour)
          const hour = itemHour != null ? Math.max(0, Math.min(23, Math.floor(itemHour))) : 0

          const explicitPriceMwh = toFiniteNumber(item?.price_uah_mwh)
          const explicitPriceKwh = toFiniteNumber(item?.price_uah_kwh)
          const mappedPriceKwh = hourlyPriceMap.get(hour)

          const priceUahMwh = explicitPriceMwh
            ?? (explicitPriceKwh != null ? explicitPriceKwh * 1000 : null)
            ?? (mappedPriceKwh != null ? mappedPriceKwh * 1000 : 0)

          return {
            hour,
            action: item.action,
            price_uah_mwh: Number(priceUahMwh.toFixed(2)),
            reasoning: item.reasoning
          }
        }) || [],
        savings_estimate: {
          daily_uah: Number(dailySavings.toFixed(2)),
          monthly_uah: Number(monthlySavings.toFixed(2)),
          annual_uah: Number(annualSavings.toFixed(2))
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