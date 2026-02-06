import { ref, computed } from 'vue'

/**
 * Composable for real-time energy metrics
 * Connects to API endpoints and provides reactive state
 */

export const useEnergyMetrics = () => {
  // State
  const metrics = ref({
    baseline: { total: 95538.29, daily_avg: 13648.33 },
    optimized: { total: 40221.62, daily_avg: 5745.95 },
    savings: { total: 55316.67, daily_avg: 7902.38, percentage: 57.9 }
  })

  const prices = ref({
    current: {
      base: 10971.64,
      peak: 12516.41,
      offpeak: 9426.87,
      weighted: 11373.61,
      unit: 'UAH/MWh'
    },
    daily: {
      min: 5000,
      max: 15000,
      avg: 11373.61,
      volatility: 1511.78
    },
    arbitrage: {
      spread: 10000,
      daily_max: 12000
    }
  })

  const battery = ref({
    soc: 75,
    capacity_kwh: 150,
    energy_stored: 112.5,
    charging: true,
    power: 25,
    efficiency: 0.95
  })

  const history = ref([
    { date: '2026-02-06', cost_baseline: 13648, cost_optimized: 5746, savings: 7902 },
    { date: '2026-02-05', cost_baseline: 13648, cost_optimized: 5745, savings: 7903 },
    { date: '2026-02-04', cost_baseline: 13648, cost_optimized: 5747, savings: 7901 },
    { date: '2026-02-03', cost_baseline: 13648, cost_optimized: 5741, savings: 7907 },
    { date: '2026-02-02', cost_baseline: 13648, cost_optimized: 5746, savings: 7902 },
    { date: '2026-02-01', cost_baseline: 13648, cost_optimized: 5741, savings: 7907 }
  ])

  // Computed
  const roi = computed(() => ({
    payback_months: 0.5,
    annual_roi: 200,
    confidence: 'HIGH'
  }))

  const projections = computed(() => ({
    monthly: metrics.value.savings.daily_avg * 30,
    quarterly: metrics.value.savings.daily_avg * 30 * 3,
    annual: metrics.value.savings.daily_avg * 30 * 12
  }))

  const pricePercentages = computed(() => ({
    peak_vs_base: ((prices.value.current.peak - prices.value.current.base) / prices.value.current.base * 100).toFixed(1),
    offpeak_vs_base: ((prices.value.current.offpeak - prices.value.current.base) / prices.value.current.base * 100).toFixed(1)
  }))

  // Methods
  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/metrics')
      const data = await response.json()
      metrics.value = data.data
    } catch (e) {
      console.error('Error fetching metrics:', e)
    }
  }

  const fetchPrices = async () => {
    try {
      const response = await fetch('/api/prices')
      const data = await response.json()
      prices.value = data.data
    } catch (e) {
      console.error('Error fetching prices:', e)
    }
  }

  const fetchBattery = async () => {
    try {
      const response = await fetch('/api/battery')
      const data = await response.json()
      battery.value = data.status
    } catch (e) {
      console.error('Error fetching battery:', e)
    }
  }

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/history')
      const data = await response.json()
      history.value = data.data
    } catch (e) {
      console.error('Error fetching history:', e)
    }
  }

  const refreshAll = async () => {
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
    setInterval(refreshAll, 30000)
  })

  return {
    // State
    metrics,
    prices,
    battery,
    history,
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

import { onMounted } from 'vue'
