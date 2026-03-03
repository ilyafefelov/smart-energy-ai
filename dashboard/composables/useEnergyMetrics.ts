import { ref, computed, onMounted, onUnmounted } from 'vue'

/**
 * Composable for real-time energy metrics
 * Connects to API endpoints and provides reactive state
 */

export const useEnergyMetrics = () => {
  const emptyMetrics = {
    baseline: { total: 0, daily_avg: 0 },
    optimized: { total: 0, daily_avg: 0 },
    savings: { total: 0, daily_avg: 0, percentage: 0 },
  }

  const emptyPrices = {
    current: {
      base: 0,
      peak: 0,
      offpeak: 0,
      weighted: 0,
      unit: 'UAH/MWh',
    },
    daily: {
      min: 0,
      max: 0,
      avg: 0,
      volatility: 0,
    },
    arbitrage: {
      spread: 0,
      daily_max: 0,
    },
  }

  const emptyBattery = {
    soc: 0,
    capacity_kwh: 0,
    energy_stored: 0,
    charging: false,
    power: 0,
    efficiency: 0,
  }

  // State
  const metrics = ref({ ...emptyMetrics })

  const prices = ref({ ...emptyPrices })

  const battery = ref({ ...emptyBattery })

  const history = ref<Array<{ date: string; cost_baseline: number; cost_optimized: number; savings: number }>>([])
  const refreshError = ref<string | null>(null)
  let refreshTimer: ReturnType<typeof setInterval> | null = null

  const asNumber = (value: unknown, fallback = 0) => {
    const numeric = Number(value)
    return Number.isFinite(numeric) ? numeric : fallback
  }

  const safePercentage = (numerator: number, denominator: number) => {
    if (!Number.isFinite(denominator) || Math.abs(denominator) < 1e-9) return '0.0'
    return ((numerator / denominator) * 100).toFixed(1)
  }

  // Computed
  const roi = computed(() => ({
    payback_months: metrics.value.savings.daily_avg > 0
      ? Number((Math.max(0, metrics.value.optimized.total) / metrics.value.savings.daily_avg / 30).toFixed(1))
      : null,
    annual_roi: metrics.value.baseline.total > 0
      ? Number(((metrics.value.savings.total / metrics.value.baseline.total) * 100).toFixed(1))
      : 0,
    confidence: metrics.value.savings.total > 0 ? 'MEDIUM' : 'N/A',
  }))

  const projections = computed(() => ({
    monthly: metrics.value.savings.daily_avg * 30,
    quarterly: metrics.value.savings.daily_avg * 30 * 3,
    annual: metrics.value.savings.daily_avg * 30 * 12
  }))

  const pricePercentages = computed(() => ({
    peak_vs_base: safePercentage(
      prices.value.current.peak - prices.value.current.base,
      prices.value.current.base,
    ),
    offpeak_vs_base: safePercentage(
      prices.value.current.offpeak - prices.value.current.base,
      prices.value.current.base,
    ),
  }))

  const mapMetricsPayload = (payload: any) => {
    const source = payload?.data || payload
    return {
      baseline: {
        total: asNumber(source?.baseline?.total),
        daily_avg: asNumber(source?.baseline?.daily_avg),
      },
      optimized: {
        total: asNumber(source?.optimized?.total),
        daily_avg: asNumber(source?.optimized?.daily_avg),
      },
      savings: {
        total: asNumber(source?.savings?.total),
        daily_avg: asNumber(source?.savings?.daily_avg),
        percentage: asNumber(source?.savings?.percentage),
      },
    }
  }

  const mapPricesPayload = (payload: any) => {
    const source = payload?.data || payload
    return {
      current: {
        base: asNumber(source?.current?.base),
        peak: asNumber(source?.current?.peak),
        offpeak: asNumber(source?.current?.offpeak),
        weighted: asNumber(source?.current?.weighted),
        unit: typeof source?.current?.unit === 'string' ? source.current.unit : 'UAH/MWh',
      },
      daily: {
        min: asNumber(source?.daily?.min),
        max: asNumber(source?.daily?.max),
        avg: asNumber(source?.daily?.avg),
        volatility: asNumber(source?.daily?.volatility),
      },
      arbitrage: {
        spread: asNumber(source?.arbitrage?.spread),
        daily_max: asNumber(source?.arbitrage?.daily_max),
      },
    }
  }

  const mapBatteryPayload = (payload: any) => {
    const source = payload?.status || payload?.battery || payload
    return {
      soc: asNumber(source?.soc),
      capacity_kwh: asNumber(source?.capacity_kwh ?? source?.capacity),
      energy_stored: asNumber(source?.energy_stored),
      charging: Boolean(source?.charging),
      power: asNumber(source?.power),
      efficiency: asNumber(source?.efficiency),
    }
  }

  // Methods
  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/metrics')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      if (data?.success === false) throw new Error(data?.error || 'Metrics API failure')
      metrics.value = mapMetricsPayload(data)
    } catch (e) {
      console.error('Error fetching metrics:', e)
      refreshError.value = e instanceof Error ? e.message : 'Error fetching metrics'
    }
  }

  const fetchPrices = async () => {
    try {
      const response = await fetch('/api/prices')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      if (data?.success === false) throw new Error(data?.error || 'Prices API failure')
      prices.value = mapPricesPayload(data)
    } catch (e) {
      console.error('Error fetching prices:', e)
      refreshError.value = e instanceof Error ? e.message : 'Error fetching prices'
    }
  }

  const fetchBattery = async () => {
    try {
      const response = await fetch('/api/battery')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      if (data?.success === false) throw new Error(data?.error || 'Battery API failure')
      battery.value = mapBatteryPayload(data)
    } catch (e) {
      console.error('Error fetching battery:', e)
      refreshError.value = e instanceof Error ? e.message : 'Error fetching battery'
    }
  }

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/history')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      if (data?.success === false) throw new Error(data?.error || 'History API failure')
      history.value = Array.isArray(data?.data)
        ? data.data.map((entry: any) => ({
            date: String(entry?.date || ''),
            cost_baseline: asNumber(entry?.cost_baseline),
            cost_optimized: asNumber(entry?.cost_optimized),
            savings: asNumber(entry?.savings),
          }))
        : []
    } catch (e) {
      console.error('Error fetching history:', e)
      refreshError.value = e instanceof Error ? e.message : 'Error fetching history'
    }
  }

  const refreshAll = async () => {
    refreshError.value = null
    await Promise.all([
      fetchMetrics(),
      fetchPrices(),
      fetchBattery(),
      fetchHistory()
    ])
  }

  // Auto-refresh every 30 seconds
  onMounted(() => {
    refreshAll()
    refreshTimer = setInterval(refreshAll, 30000)
  })

  onUnmounted(() => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  })

  return {
    // State
    metrics,
    prices,
    battery,
    history,
    refreshError,
    // Computed
    roi,
    projections,
    pricePercentages,
    // Methods
    refreshAll,
    fetchMetrics,
    fetchPrices,
    fetchBattery,
    fetchHistory
  }
}
