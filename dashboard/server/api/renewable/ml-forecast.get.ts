/**
 * API endpoint for ML-backed renewable energy forecasting.
 *
 * Exposes the Python pipeline under a dedicated route so the query-based
 * /api/renewable/forecast handler remains the single source of truth for the
 * dashboard's forecast/current/optimize contract.
 */
import { exec } from 'child_process'
import { promisify } from 'util'
import path from 'path'

const execAsync = promisify(exec)

interface RenewableForecastResponse {
  success: boolean
  data?: {
    solar_forecast: {
      current_generation_kw: number
      hourly_generation: { [key: string]: number }
      daily_total_kwh: number
      peak_generation_kw: number
      capacity_kw: number
    }
    wind_forecast: {
      current_generation_kw: number
      hourly_generation: { [key: string]: number }
      daily_total_kwh: number
      peak_generation_kw: number
      capacity_kw: number
    }
    total_renewable: {
      current_generation_kw: number
      hourly_generation: { [key: string]: number }
      daily_total_kwh: number
      peak_generation_kw: number
    }
    weather_data: {
      solar_irradiance_w_m2: number
      wind_speed_m_s: number
      temperature_c: number
      cloud_cover_fraction: number
      current_hour: number
      location: string
    }
    capacity_factors: {
      solar: number
      wind: number
      combined: number
    }
    location: {
      latitude: number
      longitude: number
    }
    installed_capacity: {
      solar_kw: number
      wind_kw: number
      total_kw: number
    }
  }
  error?: string
}

export default defineEventHandler(async (): Promise<RenewableForecastResponse> => {
  try {
    const projectRoot = path.resolve(process.cwd(), '..')
    const pythonScript = path.join(projectRoot, 'scripts', 'ml_integration_api.py')

    console.log('[Renewable API] Getting ML renewable energy forecast')

    const { stdout, stderr } = await execAsync(
      `python "${pythonScript}" --action=get_renewable_forecast --format=json`,
      {
        cwd: projectRoot,
        timeout: 30000
      }
    )

    if (stderr) {
      console.warn(`[Renewable API] Python stderr: ${stderr}`)
    }

    console.log(`[Renewable API] Python stdout: ${stdout}`)

    const mlResponse = JSON.parse(stdout.trim())

    if (!mlResponse.success) {
      throw new Error(mlResponse.error || 'Renewable forecast failed')
    }

    const forecastData = mlResponse.forecast_data || {}

    const response: RenewableForecastResponse = {
      success: true,
      data: {
        solar_forecast: {
          current_generation_kw: forecastData.solar_forecast?.current_generation_kw || 0,
          hourly_generation: forecastData.solar_forecast?.hourly_generation || {},
          daily_total_kwh: forecastData.solar_forecast?.daily_total_kwh || 0,
          peak_generation_kw: forecastData.solar_forecast?.peak_generation_kw || 0,
          capacity_kw: forecastData.solar_forecast?.capacity_kw || 0
        },
        wind_forecast: {
          current_generation_kw: forecastData.wind_forecast?.current_generation_kw || 0,
          hourly_generation: forecastData.wind_forecast?.hourly_generation || {},
          daily_total_kwh: forecastData.wind_forecast?.daily_total_kwh || 0,
          peak_generation_kw: forecastData.wind_forecast?.peak_generation_kw || 0,
          capacity_kw: forecastData.wind_forecast?.capacity_kw || 0
        },
        total_renewable: {
          current_generation_kw: forecastData.total_renewable?.current_generation_kw || 0,
          hourly_generation: forecastData.total_renewable?.hourly_generation || {},
          daily_total_kwh: forecastData.total_renewable?.daily_total_kwh || 0,
          peak_generation_kw: forecastData.total_renewable?.peak_generation_kw || 0
        },
        weather_data: {
          solar_irradiance_w_m2: forecastData.weather_data?.solar_irradiance_w_m2 || 0,
          wind_speed_m_s: forecastData.weather_data?.wind_speed_m_s || 0,
          temperature_c: forecastData.weather_data?.temperature_c || 20,
          cloud_cover_fraction: forecastData.weather_data?.cloud_cover_fraction || 0.5,
          current_hour: forecastData.weather_data?.current_hour || new Date().getHours(),
          location: forecastData.weather_data?.location || 'Unknown'
        },
        capacity_factors: {
          solar: forecastData.capacity_factors?.solar || 0,
          wind: forecastData.capacity_factors?.wind || 0,
          combined: forecastData.capacity_factors?.combined || 0
        },
        location: {
          latitude: forecastData.location?.latitude || 50.45,
          longitude: forecastData.location?.longitude || 30.52
        },
        installed_capacity: {
          solar_kw: forecastData.installed_capacity?.solar_kw || 0,
          wind_kw: forecastData.installed_capacity?.wind_kw || 0,
          total_kw: forecastData.installed_capacity?.total_kw || 0
        }
      }
    }

    console.log(`[Renewable API] ML forecast completed: ${response.data.total_renewable.current_generation_kw} kW current generation`)
    return response
  } catch (error) {
    console.error('[Renewable API] Error:', error)

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
})