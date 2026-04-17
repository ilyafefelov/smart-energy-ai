type Trend = 'up' | 'down' | 'stable'

type PriceForecastRow = {
  price?: unknown
  confidence?: unknown
  timestamp?: unknown
}

type CurrentPricesPayload = {
  prices?: {
    current?: {
      trend?: Trend
    } | null
    today?: {
      avg?: unknown
      weighted?: unknown
      min?: unknown
      max?: unknown
    } | null
    forecast?: {
      next24h?: PriceForecastRow[]
      peak?: unknown
      offPeak?: unknown
    } | null
    source?: string | null
  } | null
} | null

type MlRecommendationPayload = {
  data?: {
    confidence?: unknown
  } | null
} | null

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

const round = (value: number, digits = 2) => Number(value.toFixed(digits))
const asNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function stdDev(values: number[]): number {
  if (values.length <= 1) return 0
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length
  return Math.sqrt(variance)
}

function toDateKey(value: string): string {
  const parsed = new Date(value)
  if (!Number.isFinite(parsed.getTime())) return ''
  const y = parsed.getFullYear()
  const m = String(parsed.getMonth() + 1).padStart(2, '0')
  const d = String(parsed.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export default defineEventHandler(async (): Promise<Record<string, unknown>> => {
  // GET /api/prices - Legacy contract mapped from backend prices endpoint.
  try {
    const [currentPricesPayload, mlRecommendationPayload]: [
      CurrentPricesPayload,
      MlRecommendationPayload,
    ] = await Promise.all([
      $fetch<CurrentPricesPayload>('/api/prices/current').catch(() => null),
      $fetch<MlRecommendationPayload>('/api/ml/recommendation').catch(() => null),
    ])

    const prices = currentPricesPayload?.prices || null
    const next24h: PriceForecastRow[] = Array.isArray(prices?.forecast?.next24h) ? prices.forecast.next24h : []
    const hourlyPrices = next24h
      .map((row) => asNumber(row?.price, NaN))
      .filter((value: number) => Number.isFinite(value) && value > 0)

    const avgKwh = asNumber(
      prices?.today?.avg,
      hourlyPrices.length > 0
        ? hourlyPrices.reduce((sum: number, value: number) => sum + value, 0) / hourlyPrices.length
        : 0,
    )
    const weightedKwh = asNumber(prices?.today?.weighted, avgKwh)
    const peakKwh = asNumber(prices?.forecast?.peak, asNumber(prices?.today?.max, avgKwh))
    const offPeakKwh = asNumber(prices?.forecast?.offPeak, asNumber(prices?.today?.min, avgKwh))
    const minKwh = asNumber(prices?.today?.min, Math.min(avgKwh, offPeakKwh))
    const maxKwh = asNumber(prices?.today?.max, Math.max(avgKwh, peakKwh))
    const volatilityKwh = hourlyPrices.length > 1
      ? stdDev(hourlyPrices)
      : Math.max(0, maxKwh - minKwh) / 2

    const todayKey = toDateKey(new Date().toISOString())
    const tomorrowRows = next24h.filter((row) => {
      const ts = typeof row?.timestamp === 'string' ? row.timestamp : ''
      return ts && toDateKey(ts) !== todayKey
    })

    const tomorrowAvgKwh = tomorrowRows.length > 0
      ? tomorrowRows.reduce((sum: number, row) => sum + asNumber(row?.price), 0) / tomorrowRows.length
      : avgKwh

    const confidenceFromForecast = tomorrowRows.length > 0
      ? tomorrowRows.reduce((sum: number, row) => sum + asNumber(row?.confidence, 0.7), 0) / tomorrowRows.length
      : NaN

    const confidence = Number.isFinite(confidenceFromForecast)
      ? confidenceFromForecast
      : asNumber(mlRecommendationPayload?.data?.confidence, 0)

    const trendFromCurrent = prices?.current?.trend as Trend | undefined
    const trend: Trend = trendFromCurrent || (
      tomorrowAvgKwh > avgKwh * 1.03
        ? 'up'
        : tomorrowAvgKwh < avgKwh * 0.97
          ? 'down'
          : 'stable'
    )

    const spreadMwh = Math.max(0, (maxKwh - minKwh) * 1000)

    return {
      success: true,
      timestamp: new Date().toISOString(),
      data: {
        current: {
          base: round(avgKwh * 1000),
          peak: round(peakKwh * 1000),
          offpeak: round(offPeakKwh * 1000),
          weighted: round(weightedKwh * 1000),
          unit: 'UAH/MWh',
          pricePerKwh: round(avgKwh, 2),
        },
        daily: {
          min: round(minKwh * 1000),
          max: round(maxKwh * 1000),
          avg: round(avgKwh * 1000),
          volatility: round(volatilityKwh * 1000),
        },
        arbitrage: {
          spread: round(spreadMwh),
          daily_max: round(spreadMwh),
          unit: 'UAH',
        },
        forecast: {
          tomorrow: round(tomorrowAvgKwh * 1000),
          confidence: round(Math.max(0, Math.min(1, confidence)), 2),
          trend,
        },
      },
      source: {
        backend_priority: ['/api/prices/current', '/api/ml/recommendation'],
        prices_current_source: prices?.source || 'unavailable',
      },
    }
  } catch (error) {
    console.error('[prices] Failed to build backend-derived payload:', error)
    return {
      success: false,
      timestamp: new Date().toISOString(),
      error: getErrorMessage(error, 'Failed to fetch price data'),
    }
  }
})
