/**
 * Renewable Energy API endpoint - Solar and Wind generation forecasting
 * Phase 5: Complete renewable energy modeling integration
 */

export default defineEventHandler(async (event) => {
  const method = getMethod(event)
  const query = getQuery(event)
  
  if (method === 'GET') {
    try {
      const {
        forecast_hours = '24',
        solar_capacity = '0',
        wind_capacity = '0',
        type = 'forecast' // 'current', 'forecast', 'optimize'
      } = query
      
      const solarCapacityKw = parseFloat(solar_capacity as string)
      const windCapacityKw = parseFloat(wind_capacity as string)
      const forecastHours = parseInt(forecast_hours as string)
      
      // Validate inputs
      if (solarCapacityKw < 0 || windCapacityKw < 0) {
        throw createError({
          statusCode: 400,
          statusMessage: 'Solar and wind capacities must be non-negative'
        })
      }
      
      if (forecastHours < 1 || forecastHours > 168) { // Max 1 week
        throw createError({
          statusCode: 400,
          statusMessage: 'Forecast hours must be between 1 and 168'
        })
      }
      
      // Get current time and weather conditions
      const now = new Date()
      const currentHour = now.getHours()
      
      // Generate realistic weather and generation data for Ukraine
      const generateWeatherForecast = (hours: number) => {
        const forecast = []
        
        for (let h = 0; h < hours; h++) {
          const timestamp = new Date(now.getTime() + h * 3600000)
          const hour = timestamp.getHours()
          const dayOfYear = Math.floor((timestamp.getTime() - new Date(timestamp.getFullYear(), 0, 0).getTime()) / (1000 * 60 * 60 * 24))
          
          // Seasonal temperature variation (Kiev climate)
          const seasonalTemp = 10 + 15 * Math.sin(2 * Math.PI * (dayOfYear - 90) / 365)
          const dailyTempVariation = 8 * Math.sin(2 * Math.PI * hour / 24)
          const temperature = seasonalTemp + dailyTempVariation + (Math.random() - 0.5) * 6
          
          // Solar irradiance calculation
          let ghi = 0
          let solarGeneration = 0
          
          if (hour >= 6 && hour <= 18) { // Daylight hours
            const sunAngle = Math.sin(Math.PI * (hour - 6) / 12)
            const seasonalFactor = 0.7 + 0.3 * Math.sin(2 * Math.PI * (dayOfYear - 80) / 365)
            const cloudFactor = 0.4 + 0.6 * (1 - Math.pow(Math.random(), 2)) // More clear than cloudy
            
            ghi = 1000 * sunAngle * seasonalFactor * cloudFactor
            
            if (solarCapacityKw > 0) {
              // Solar PV calculation with temperature derating
              const tempDerating = 1 - 0.004 * (temperature - 25)
              const systemEfficiency = 0.85 // 15% system losses
              solarGeneration = solarCapacityKw * (ghi / 1000) * tempDerating * systemEfficiency
            }
          }
          
          // Wind generation calculation
          const baseWindSpeed = 4 + 8 * Math.pow(Math.random(), 0.7) // 4-12 m/s typical
          const windSpeed = Math.max(0, baseWindSpeed + (Math.random() - 0.5) * 2)
          
          let windGeneration = 0
          if (windCapacityKw > 0 && windSpeed >= 3) { // Cut-in speed
            if (windSpeed >= 25) {
              windGeneration = 0 // Cut-out for safety
            } else if (windSpeed <= 12) {
              // Cubic relationship below rated speed
              windGeneration = windCapacityKw * Math.pow(windSpeed / 12, 3)
            } else {
              windGeneration = windCapacityKw // Rated power
            }
          }
          
          forecast.push({
            timestamp: timestamp.toISOString(),
            hour: hour,
            temperature_celsius: Math.round(temperature * 10) / 10,
            wind_speed_ms: Math.round(windSpeed * 10) / 10,
            ghi_wm2: Math.round(ghi),
            cloud_cover_percent: Math.round((1 - cloudFactor) * 100),
            solar_generation_kw: Math.round(solarGeneration * 100) / 100,
            wind_generation_kw: Math.round(windGeneration * 100) / 100,
            total_generation_kw: Math.round((solarGeneration + windGeneration) * 100) / 100
          })
        }
        
        return forecast
      }
      
      if (type === 'current') {
        // Current generation only
        const currentWeather = generateWeatherForecast(1)[0]
        
        return {
          timestamp: currentWeather.timestamp,
          current_generation: {
            solar_kw: currentWeather.solar_generation_kw,
            wind_kw: currentWeather.wind_generation_kw,
            total_kw: currentWeather.total_generation_kw
          },
          weather_conditions: {
            temperature_celsius: currentWeather.temperature_celsius,
            wind_speed_ms: currentWeather.wind_speed_ms,
            solar_irradiance_wm2: currentWeather.ghi_wm2,
            cloud_cover_percent: currentWeather.cloud_cover_percent
          },
          system_specs: {
            solar_capacity_kw: solarCapacityKw,
            wind_capacity_kw: windCapacityKw,
            total_capacity_kw: solarCapacityKw + windCapacityKw
          }
        }
        
      } else if (type === 'forecast') {
        // Full forecast
        const forecast = generateWeatherForecast(forecastHours)
        
        // Calculate summary statistics
        const totalSolarKwh = forecast.reduce((sum, f) => sum + f.solar_generation_kw, 0)
        const totalWindKwh = forecast.reduce((sum, f) => sum + f.wind_generation_kw, 0)
        const totalRenewableKwh = totalSolarKwh + totalWindKwh
        
        const maxSolar = Math.max(...forecast.map(f => f.solar_generation_kw))
        const maxWind = Math.max(...forecast.map(f => f.wind_generation_kw))
        const maxTotal = Math.max(...forecast.map(f => f.total_generation_kw))
        
        const solarCapacityFactor = solarCapacityKw > 0 ? totalSolarKwh / (solarCapacityKw * forecastHours) : 0
        const windCapacityFactor = windCapacityKw > 0 ? totalWindKwh / (windCapacityKw * forecastHours) : 0
        
        // Find peak generation hours
        const peakSolarHour = forecast.find(f => f.solar_generation_kw === maxSolar)
        const peakWindHour = forecast.find(f => f.wind_generation_kw === maxWind)
        
        return {
          forecast_period_hours: forecastHours,
          location: { lat: 50.4501, lon: 30.5234, city: 'Kiev, Ukraine' },
          timestamp: now.toISOString(),
          
          summary: {
            total_solar_kwh: Math.round(totalSolarKwh * 100) / 100,
            total_wind_kwh: Math.round(totalWindKwh * 100) / 100,
            total_renewable_kwh: Math.round(totalRenewableKwh * 100) / 100,
            average_generation_kw: Math.round((totalRenewableKwh / forecastHours) * 100) / 100,
            peak_solar_kw: maxSolar,
            peak_wind_kw: maxWind,
            peak_total_kw: maxTotal,
            solar_capacity_factor: Math.round(solarCapacityFactor * 1000) / 10, // Percentage
            wind_capacity_factor: Math.round(windCapacityFactor * 1000) / 10,
            peak_solar_hour: peakSolarHour?.timestamp || null,
            peak_wind_hour: peakWindHour?.timestamp || null
          },
          
          system_specs: {
            solar_capacity_kw: solarCapacityKw,
            wind_capacity_kw: windCapacityKw,
            total_capacity_kw: solarCapacityKw + windCapacityKw,
            solar_panel_efficiency: 22.0, // %
            wind_hub_height_m: 30.0,
            system_losses_percent: 15.0
          },
          
          hourly_forecast: forecast,
          
          // Daily breakdown for multi-day forecasts
          daily_summary: forecastHours > 24 ? getDailySummary(forecast) : null
        }
        
      } else if (type === 'optimize') {
        // System optimization
        const targetDailyKwh = parseFloat(query.target_daily_kwh as string) || 50
        const budgetUsd = parseFloat(query.budget_usd as string) || 20000
        
        const solarCostPerKw = 1200 // USD/kW
        const windCostPerKw = 2000  // USD/kW
        
        let bestConfig = null
        let bestScore = 0
        
        // Test different solar/wind combinations
        for (let solarRatio = 0; solarRatio <= 1; solarRatio += 0.1) {
          const windRatio = 1 - solarRatio
          
          const solarBudget = budgetUsd * solarRatio
          const windBudget = budgetUsd * windRatio
          
          const solarCapacity = solarBudget / solarCostPerKw
          const windCapacity = windBudget / windCostPerKw
          
          // Estimate daily generation (Ukraine averages)
          const dailySolar = solarCapacity * 4.5 // 4.5 kWh/kW/day average
          const dailyWind = windCapacity * 7.0   // 7.0 kWh/kW/day average
          const totalDaily = dailySolar + dailyWind
          
          // Score based on target achievement and cost efficiency
          const targetAchievement = Math.min(1, totalDaily / targetDailyKwh)
          const costEfficiency = totalDaily / budgetUsd * 1000 // Normalize
          const score = targetAchievement * 0.7 + costEfficiency * 0.3
          
          if (score > bestScore) {
            bestScore = score
            bestConfig = {
              solar_capacity_kw: Math.round(solarCapacity * 10) / 10,
              wind_capacity_kw: Math.round(windCapacity * 10) / 10,
              solar_ratio_percent: Math.round(solarRatio * 100),
              wind_ratio_percent: Math.round(windRatio * 100),
              estimated_daily_kwh: Math.round(totalDaily * 10) / 10,
              target_achievement_percent: Math.round(targetAchievement * 100),
              total_cost_usd: budgetUsd,
              cost_per_daily_kwh: Math.round(budgetUsd / totalDaily * 100) / 100,
              payback_years: Math.round((budgetUsd / (totalDaily * 365 * 0.1)) * 10) / 10 // Assume $0.1/kWh
            }
          }
        }
        
        return {
          optimization_result: bestConfig,
          input_parameters: {
            target_daily_kwh: targetDailyKwh,
            budget_usd: budgetUsd,
            location: 'Kiev, Ukraine'
          },
          assumptions: {
            solar_cost_per_kw_usd: solarCostPerKw,
            wind_cost_per_kw_usd: windCostPerKw,
            ukraine_solar_daily_kwh_per_kw: 4.5,
            ukraine_wind_daily_kwh_per_kw: 7.0,
            electricity_price_usd_per_kwh: 0.1
          },
          recommendations: {
            prioritize_solar: bestConfig?.solar_ratio_percent > 70 ? 'High solar ratio recommended due to cost efficiency' : null,
            prioritize_wind: bestConfig?.wind_ratio_percent > 70 ? 'High wind ratio recommended for steady generation' : null,
            balanced_approach: bestConfig && bestConfig.solar_ratio_percent >= 30 && bestConfig.wind_ratio_percent >= 30 ? 'Balanced solar/wind approach recommended' : null
          }
        }
        
      } else {
        throw createError({
          statusCode: 400,
          statusMessage: 'Invalid type parameter. Use: current, forecast, or optimize'
        })
      }
      
    } catch (error) {
      console.error('Renewable energy API error:', error)
      
      throw createError({
        statusCode: error.statusCode || 500,
        statusMessage: error.statusMessage || `Renewable energy forecast failed: ${error.message}`
      })
    }
  }
  
  throw createError({
    statusCode: 405,
    statusMessage: 'Method not allowed. Use GET to retrieve renewable energy data.'
  })
})

// Helper function to calculate daily summaries
function getDailySummary(forecast: any[]) {
  const dailyData: { [key: string]: any } = {}
  
  forecast.forEach(hourly => {
    const date = hourly.timestamp.split('T')[0]
    
    if (!dailyData[date]) {
      dailyData[date] = {
        date,
        solar_kwh: 0,
        wind_kwh: 0,
        total_kwh: 0,
        peak_solar_kw: 0,
        peak_wind_kw: 0,
        avg_temperature: 0,
        avg_wind_speed: 0,
        hours: 0
      }
    }
    
    const day = dailyData[date]
    day.solar_kwh += hourly.solar_generation_kw
    day.wind_kwh += hourly.wind_generation_kw
    day.total_kwh += hourly.total_generation_kw
    day.peak_solar_kw = Math.max(day.peak_solar_kw, hourly.solar_generation_kw)
    day.peak_wind_kw = Math.max(day.peak_wind_kw, hourly.wind_generation_kw)
    day.avg_temperature += hourly.temperature_celsius
    day.avg_wind_speed += hourly.wind_speed_ms
    day.hours += 1
  })
  
  // Calculate averages
  Object.values(dailyData).forEach((day: any) => {
    day.avg_temperature = Math.round((day.avg_temperature / day.hours) * 10) / 10
    day.avg_wind_speed = Math.round((day.avg_wind_speed / day.hours) * 10) / 10
    day.solar_kwh = Math.round(day.solar_kwh * 100) / 100
    day.wind_kwh = Math.round(day.wind_kwh * 100) / 100
    day.total_kwh = Math.round(day.total_kwh * 100) / 100
    delete day.hours
  })
  
  return Object.values(dailyData)
}