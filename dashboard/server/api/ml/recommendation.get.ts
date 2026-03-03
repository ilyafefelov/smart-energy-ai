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
    current?: {
      price?: number
    }
    forecast?: {
      next24h?: PriceForecastPoint[]
    }
  }
}

interface OpenMeteoSnapshot {
  source: string
  latitude: number
  longitude: number
  timezone: string
  captured_at: string
  current: {
    temperature_c: number | null
    shortwave_radiation_w_m2: number | null
    wind_speed_m_s: number | null
    cloud_cover_percent: number | null
  }
  next24h: Array<{
    hour_offset: number
    timestamp: string
    temperature_c: number | null
    shortwave_radiation_w_m2: number | null
    wind_speed_m_s: number | null
    cloud_cover_percent: number | null
  }>
}

interface DriftDiagnostics {
  status: 'stable' | 'warning' | 'drifted'
  score: number
  thresholds: {
    warning: number
    drifted: number
  }
  signals: Array<{
    name: string
    value: number
    weight: number
    contribution: number
  }>
  recommendation: string
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
    feature_provenance?: Record<string, any>
    model_inputs?: Record<string, any>
    inference_lineage?: Record<string, any>
    drift_diagnostics?: DriftDiagnostics
  }
  error?: string
}

function average(values: number[]): number {
  if (!values.length) return 0
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0
  if (value < 0) return 0
  if (value > 1) return 1
  return value
}

function computeDriftDiagnostics(input: {
  currentPriceUahKwh: number | null
  priceForecastRows: Array<{ price?: number | null }>
  weatherCurrent: OpenMeteoSnapshot['current'] | null
  batterySocPercent: number | null
}): DriftDiagnostics {
  const priceRows = input.priceForecastRows
    .map((row) => toFiniteNumber(row?.price))
    .filter((value): value is number => value != null)

  const avgPrice = average(priceRows)
  const currentPrice = input.currentPriceUahKwh ?? avgPrice
  const priceDrift = avgPrice > 0 ? Math.abs(currentPrice - avgPrice) / avgPrice : 0

  const temp = toFiniteNumber(input.weatherCurrent?.temperature_c)
  const weatherDrift = temp != null ? Math.abs(temp - 15) / 35 : 0

  const soc = input.batterySocPercent ?? 50
  const socDrift = Math.abs(soc - 50) / 50

  const signals = [
    { name: 'price_distribution_shift', value: clamp01(priceDrift), weight: 0.5 },
    { name: 'weather_temperature_shift', value: clamp01(weatherDrift), weight: 0.25 },
    { name: 'battery_soc_shift', value: clamp01(socDrift), weight: 0.25 },
  ]

  const score = signals.reduce((sum, signal) => sum + signal.value * signal.weight, 0)
  const withContrib = signals.map((signal) => ({
    ...signal,
    contribution: Number((signal.value * signal.weight).toFixed(4)),
    value: Number(signal.value.toFixed(4)),
  }))

  const warning = 0.2
  const drifted = 0.35
  const status: DriftDiagnostics['status'] = score >= drifted ? 'drifted' : score >= warning ? 'warning' : 'stable'
  const recommendation = status === 'drifted'
    ? 'Trigger accelerated retraining and validate feature normalization windows.'
    : status === 'warning'
      ? 'Increase monitoring cadence and compare against recent training cohort.'
      : 'Distribution is stable; continue normal monitoring interval.'

  return {
    status,
    score: Number(score.toFixed(4)),
    thresholds: {
      warning,
      drifted,
    },
    signals: withContrib,
    recommendation,
  }
}

function sanitizeTimezone(timezone: string | null | undefined): string {
  const fallback = 'Europe/Kiev'
  if (!timezone || typeof timezone !== 'string') return fallback
  const normalized = timezone.trim()
  if (!normalized) return fallback
  return normalized.replace(/[^A-Za-z0-9_\-/+]/g, '') || fallback
}

async function fetchOpenMeteoSnapshot(latitude: number, longitude: number, timezone: string): Promise<OpenMeteoSnapshot | null> {
  try {
    const safeTimezone = sanitizeTimezone(timezone)
    const query = new URLSearchParams({
      latitude: latitude.toFixed(4),
      longitude: longitude.toFixed(4),
      timezone: safeTimezone,
      forecast_days: '2',
      hourly: 'temperature_2m,shortwave_radiation,wind_speed_10m,cloud_cover',
    })

    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${query.toString()}`, {
      headers: {
        accept: 'application/json',
      },
    })

    if (!response.ok) {
      return null
    }

    const payload = await response.json() as any
    const hourly = payload?.hourly
    if (!hourly?.time || !Array.isArray(hourly.time)) {
      return null
    }

    const now = Date.now()
    const times: Array<string> = hourly.time
    const pickIndex = times.findIndex((item) => {
      const ts = new Date(item).getTime()
      return Number.isFinite(ts) && ts >= now
    })

    const currentIndex = pickIndex >= 0 ? pickIndex : 0
    const rowAt = (idx: number, key: string) => {
      const value = hourly?.[key]?.[idx]
      return toFiniteNumber(value)
    }

    const next24h = Array.from({ length: 24 }, (_, offset) => {
      const idx = currentIndex + offset
      return {
        hour_offset: offset,
        timestamp: String(times[idx] || times[currentIndex] || new Date().toISOString()),
        temperature_c: rowAt(idx, 'temperature_2m'),
        shortwave_radiation_w_m2: rowAt(idx, 'shortwave_radiation'),
        wind_speed_m_s: rowAt(idx, 'wind_speed_10m'),
        cloud_cover_percent: rowAt(idx, 'cloud_cover'),
      }
    })

    return {
      source: 'open-meteo',
      latitude,
      longitude,
      timezone: safeTimezone,
      captured_at: new Date().toISOString(),
      current: {
        temperature_c: rowAt(currentIndex, 'temperature_2m'),
        shortwave_radiation_w_m2: rowAt(currentIndex, 'shortwave_radiation'),
        wind_speed_m_s: rowAt(currentIndex, 'wind_speed_10m'),
        cloud_cover_percent: rowAt(currentIndex, 'cloud_cover'),
      },
      next24h,
    }
  } catch {
    return null
  }
}

export default defineEventHandler(async (event): Promise<MLRecommendationResponse> => {
  try {
    const tenant = await resolveTenantContext(event)
    const tenantRequest = {
      query: {
        tenantId: tenant.id,
      },
      headers: {
        'x-tenant-id': tenant.id,
      },
    }

    const [configPayload, pricesPayload, batteryPayload, mlflowStatus] = await Promise.all([
      $fetch<any>('/api/config/current', tenantRequest).catch(() => null),
      $fetch<PricesCurrentResponse>('/api/prices/current', tenantRequest).catch(() => null),
      $fetch<any>('/api/battery/status', tenantRequest).catch(() => null),
      $fetch<any>('/api/mlflow/status', tenantRequest).catch(() => null),
    ])

    const latitude = toFiniteNumber(configPayload?.data?.latitude) ?? 50.45
    const longitude = toFiniteNumber(configPayload?.data?.longitude) ?? 30.52
    const timezone = sanitizeTimezone(configPayload?.data?.timezone)
    const weatherPayload = await fetchOpenMeteoSnapshot(latitude, longitude, timezone)

    const liveContext = {
      tenant_id: tenant.id,
      captured_at: new Date().toISOString(),
      config: {
        battery_type: configPayload?.data?.battery_type,
        battery_capacity_kwh: configPayload?.data?.battery_capacity_kwh,
        battery_soc_min: configPayload?.data?.battery_soc_min,
        battery_soc_max: configPayload?.data?.battery_soc_max,
        optimization_strategy: configPayload?.data?.optimization_strategy,
        load_profile_type: configPayload?.data?.load_profile_type,
        load_peak_kw: configPayload?.data?.load_peak_kw,
        load_base_kw: configPayload?.data?.load_base_kw,
        has_solar: configPayload?.data?.has_solar,
        has_wind: configPayload?.data?.has_wind,
        solar_capacity_kw: configPayload?.data?.solar_capacity_kw,
        wind_capacity_kw: configPayload?.data?.wind_capacity_kw,
        solar_efficiency: configPayload?.data?.solar_efficiency,
        wind_efficiency: configPayload?.data?.wind_efficiency,
        latitude,
        longitude,
        timezone,
      },
      price_signal: {
        source: 'api/prices/current',
        current_uah_kwh: toFiniteNumber(pricesPayload?.prices?.current?.price),
        forecast_next24h: pricesPayload?.prices?.forecast?.next24h || [],
      },
      battery_signal: {
        source: 'api/battery/status',
        soc_percent: toFiniteNumber(batteryPayload?.battery?.soc),
        health_percent: toFiniteNumber(batteryPayload?.battery?.health),
        cycles_remaining: toFiniteNumber(configPayload?.data?.battery_cycles_max)
          ? Number((Number(configPayload?.data?.battery_cycles_max) * Math.max(0.1, Number(batteryPayload?.battery?.health || 100) / 100)).toFixed(0))
          : null,
      },
      weather_signal: weatherPayload,
    }

    const inferenceContextId = [
      tenant.id,
      Math.round(new Date(liveContext.captured_at).getTime() / 1000),
      Math.round((liveContext.price_signal.current_uah_kwh || 0) * 100),
    ].join(':')

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
          ENERGY_ML_LIVE_CONTEXT_JSON: JSON.stringify(liveContext),
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
    
    const hourlyPriceMap = buildHourlyPriceMap(pricesPayload)
    const dailySavings = toFiniteNumber(mlResponse.daily_savings_estimate) ?? 0
    const monthlySavings = toFiniteNumber(mlResponse.monthly_savings_estimate) ?? (dailySavings * 30)
    const annualSavings = toFiniteNumber(mlResponse.annual_savings_estimate) ?? (dailySavings * 365)
    const driftDiagnostics = computeDriftDiagnostics({
      currentPriceUahKwh: toFiniteNumber(liveContext.price_signal.current_uah_kwh),
      priceForecastRows: liveContext.price_signal.forecast_next24h || [],
      weatherCurrent: weatherPayload?.current || null,
      batterySocPercent: toFiniteNumber(liveContext.battery_signal.soc_percent),
    })

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
        },
        feature_provenance: mlResponse.feature_provenance || {
          config_source: 'tenant_config',
          price_source: liveContext.price_signal.source,
          weather_source: weatherPayload?.source || 'weather_unavailable',
          captured_at: liveContext.captured_at,
          tenant_id: tenant.id,
        },
        model_inputs: mlResponse.model_inputs || {
          profile: liveContext.config,
          live_price: liveContext.price_signal.current_uah_kwh,
          live_battery: liveContext.battery_signal,
          live_weather: weatherPayload?.current || null,
        },
        inference_lineage: {
          inference_context_id: inferenceContextId,
          tenant_id: tenant.id,
          captured_at: liveContext.captured_at,
          training_reference: {
            mlflow_connected: mlflowStatus?.mlflow_connected === true,
            model_name: mlflowStatus?.active_model?.name || null,
            model_version: mlflowStatus?.active_model?.version || null,
            model_stage: mlflowStatus?.active_model?.stage || null,
            trained_at: mlflowStatus?.active_model?.last_updated || null,
          },
          inference_sources: {
            profile: 'tenant_config',
            prices: liveContext.price_signal.source,
            weather: weatherPayload?.source || 'weather_unavailable',
            battery: liveContext.battery_signal.source,
          },
          feature_vector_signature: {
            strategy: String(liveContext.config.optimization_strategy || 'balanced'),
            load_profile: String(liveContext.config.load_profile_type || 'standard'),
            horizon_hours: 24,
          },
        },
        drift_diagnostics: driftDiagnostics,
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