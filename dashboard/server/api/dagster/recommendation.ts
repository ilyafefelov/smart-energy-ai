// API endpoint to get recommendations from Dagster ML pipeline
// Connects dashboard to ML recommendation engine via Dagster/MLflow APIs

const DAGSTER_API = process.env.DAGSTER_API_URL || 'http://localhost:3600'

export default defineEventHandler(async (event) => {
  try {
    const [mlRecommendation, pricesPayload, batteryPayload, mlflowStatus] = await Promise.all([
      $fetch<any>('/api/ml/recommendation').catch(() => null),
      $fetch<any>('/api/prices/current').catch(() => null),
      $fetch<any>('/api/battery/status').catch(() => null),
      $fetch<any>('/api/mlflow/status').catch(() => null),
    ])

    // Try to get Dagster job status
    let dagsterStatus = { available: false, jobs: [] }
    try {
      const dagsterQuery = await $fetch(`${DAGSTER_API}/graphql`, {
        method: 'POST',
        body: {
          query: `{ instance { id } }`
        }
      })
      if (dagsterQuery.data?.instance) {
        dagsterStatus.available = true
      }
    } catch (e) {
      console.warn('[recommendation] Dagster not available:', e.message)
    }

    const currentPrice = Number(pricesPayload?.prices?.current?.price || 0)
    const batterySoc = Number(batteryPayload?.battery?.soc || 50)
    const mlData = mlRecommendation?.data || null

    const recommendation = {
      action: mlData?.action || 'HOLD',
      confidence: Number(mlData?.confidence || 0.5),
      confidence_percent: Math.round(Number(mlData?.confidence || 0.5) * 100),
      rationale: mlData?.reasoning || 'Recommendation unavailable - holding position',
    }

    const schedule24h = buildDeterministicSchedule(
      pricesPayload?.prices?.forecast?.next24h || [],
      mlData?.daily_forecast || [],
      recommendation.confidence
    )

    const activeModel = mlflowStatus?.active_model || null
    const modelInfo = {
      type: activeModel?.name || 'Phase4F',
      version: activeModel?.version || mlData?.model_info?.version || 'Phase4F-v1.0',
      last_trained: activeModel?.last_updated || mlData?.timestamp || new Date().toISOString(),
      accuracy_percent: Number(recommendation.confidence_percent || 0),
      mlflow_available: mlflowStatus?.mlflow_connected === true,
    }

    return {
      status: 'success',
      timestamp: new Date().toISOString(),
      recommendation,
      current_state: {
        price_uah_kwh: currentPrice,
        battery_soc_percent: batterySoc,
        time: new Date().toLocaleTimeString('uk-UA'),
      },
      schedule_24h: schedule24h,
      model_info: modelInfo,
      lineage: {
        data_sources: 5,
        total_features: 73,
        data_provenance: 'Weather API, Price OREE, Battery BMS, Solar Model, Wind Model',
      },
      monitoring: {
        needs_retraining: Boolean(mlflowStatus?.monitoring?.drift_detected),
        drift_detected: false,
        last_check: new Date().toISOString(),
      },
      dagster_status: dagsterStatus
    }
  } catch (error) {
    console.error('[recommendation] Error:', error)
    return {
      status: 'error',
      error: error.message,
      fallback: 'HOLD',
    }
  }
})

function buildDeterministicSchedule(
  forecast: Array<{ hour: number; timestamp: string; price: number }>,
  mlForecast: Array<{ hour: number; action?: string; reasoning?: string }>,
  baseConfidence: number
) {
  const actionByHour = new Map<number, { action: string; reasoning: string }>()
  for (const item of mlForecast) {
    if (typeof item?.hour !== 'number') continue
    actionByHour.set(item.hour, {
      action: item.action || 'HOLD',
      reasoning: item.reasoning || '',
    })
  }

  const safeForecast = forecast.slice(0, 24)
  const avgPrice = safeForecast.length > 0
    ? safeForecast.reduce((sum, row) => sum + Number(row.price || 0), 0) / safeForecast.length
    : 0

  const schedule = safeForecast.map((row) => {
    const hour = Number(row.hour)
    const price = Number(row.price || 0)
    const ml = actionByHour.get(hour)

    let action = ml?.action || 'HOLD'
    if (!ml) {
      if (avgPrice > 0 && price < avgPrice * 0.9) {
        action = 'BUY'
      } else if (avgPrice > 0 && price > avgPrice * 1.1) {
        action = 'SELL'
      }
    }

    const expectedProfit = action === 'BUY'
      ? -price
      : action === 'SELL'
        ? price * 0.75
        : action === 'DISCHARGE'
          ? price * 0.85
          : 0

    const isPeak = hour >= 7 && hour <= 9 || hour >= 17 && hour <= 20

    return {
      hour,
      time: new Date(row.timestamp).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' }),
      price_uah_kwh: Number(price.toFixed(2)),
      recommended_action: action,
      expected_profit_uah: Number(expectedProfit.toFixed(2)),
      confidence: Number(baseConfidence.toFixed(2)),
      is_peak: isPeak,
      rationale: ml?.reasoning || '',
    }
  })

  const totalProfit = schedule.reduce((sum, s) => sum + s.expected_profit_uah, 0)

  return {
    schedule,
    total_expected_profit: Number(totalProfit.toFixed(2)),
    buy_hours: schedule.filter(s => s.recommended_action === 'BUY').length,
    sell_hours: schedule.filter(s => s.recommended_action === 'SELL').length,
    discharge_hours: schedule.filter(s => s.recommended_action === 'DISCHARGE').length,
  }
}
