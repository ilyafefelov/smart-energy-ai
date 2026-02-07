import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Metric {
  label: string
  value: string | number
  unit?: string
  trend?: 'up' | 'down' | 'stable'
  trendValue?: number
  color?: string
}

export interface DashboardMetrics {
  savingsToday: Metric
  savingsThisMonth: Metric
  forecastAccuracy: Metric
  batteryHealth: Metric
  nextCycleIn: Metric
  averagePrice: Metric
  peakPrice: Metric
  offPeakPrice: Metric
}

const DEFAULT_METRICS: DashboardMetrics = {
  savingsToday: {
    label: 'Daily Savings',
    value: '₴ 125.50',
    unit: 'UAH',
    trend: 'up',
    trendValue: 12.5,
    color: 'green'
  },
  savingsThisMonth: {
    label: 'Monthly Savings',
    value: '₴ 3,450',
    unit: 'UAH',
    color: 'green'
  },
  forecastAccuracy: {
    label: 'Forecast Accuracy',
    value: '92.3%',
    unit: '%',
    trend: 'stable',
    color: 'blue'
  },
  batteryHealth: {
    label: 'Battery SOC',
    value: '75%',
    unit: '%',
    trend: 'stable',
    color: 'yellow'
  },
  nextCycleIn: {
    label: 'Next Cycle In',
    value: '3h 45m',
    color: 'purple'
  },
  averagePrice: {
    label: 'Today\'s Avg Price',
    value: '9.85',
    unit: '₴/kWh',
    color: 'slate'
  },
  peakPrice: {
    label: 'Peak Price',
    value: '14.50',
    unit: '₴/kWh',
    color: 'red'
  },
  offPeakPrice: {
    label: 'Off-Peak Price',
    value: '6.20',
    unit: '₴/kWh',
    color: 'green'
  }
}

export interface TooltipInfo {
  [key: string]: {
    title: string
    description: string
    formula?: string
  }
}

const TOOLTIPS: TooltipInfo = {
  savingsToday: {
    title: 'Daily Savings',
    description: 'Total savings achieved today',
    formula: 'Baseline Cost - Optimized Cost'
  },
  savingsThisMonth: {
    title: 'Monthly Savings',
    description: 'Cumulative savings since the start of the month',
    formula: 'Sum of daily savings'
  },
  forecastAccuracy: {
    title: 'Forecast Accuracy',
    description: 'Forecasting model accuracy',
    formula: '(Accurate Predictions / Total Predictions) × 100'
  },
  batteryHealth: {
    title: 'Battery SOC',
    description: 'Battery state of charge',
    formula: 'Measured by battery telemetry (SOC%)'
  },
  nextCycleIn: {
    title: 'Next Cycle',
    description: 'Time until next peak/off-peak cycle',
    formula: 'Based on price forecast and battery state'
  },
  currentPrice: {
    title: 'Current Price',
    description: 'Current electricity price',
    formula: 'Real-time market price (₴/kWh)'
  },
  averagePrice: {
    title: 'Average Price',
    description: 'Daily weighted average electricity price',
    formula: 'Sum(Price × Hours) / 24'
  },
  peakPrice: {
    title: 'Peak Price',
    description: 'Highest price today',
    formula: 'Max hourly price'
  },
  offPeakPrice: {
    title: 'Off-Peak Price',
    description: 'Lowest price today',
    formula: 'Min hourly price'
  }
}

export const useMetricsStore = defineStore('metrics', () => {
  const metrics = ref<DashboardMetrics>({ ...DEFAULT_METRICS })
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastFetchTime = ref<Date | null>(null)
  const updateInterval = ref<NodeJS.Timeout | null>(null)

  // Getters
  const savingsToday = computed(() => metrics.value.savingsToday)
  const savingsMonth = computed(() => metrics.value.savingsThisMonth)
  const accuracy = computed(() => metrics.value.forecastAccuracy)
  const batteryHealth = computed(() => metrics.value.batteryHealth)

  const allMetrics = computed(() => Object.values(metrics.value))

  const getTooltip = (key: string) => TOOLTIPS[key] || null

  // Actions
  const fetchMetrics = async () => {
    isLoading.value = true
    error.value = null

    try {
      const response = await $fetch('/api/metrics/dashboard') as any

      if (response.success && response.metrics) {
        const m = response.metrics

        metrics.value = {
          savingsToday: {
            label: 'Daily Savings',
            value: `₴ ${(m.savingsToday || 0).toFixed(2)}`,
            unit: 'UAH',
            trend: m.savingsTrend || 'stable',
            trendValue: m.savingsTrendValue,
            color: 'green'
          },
          savingsThisMonth: {
            label: 'Monthly Savings',
            value: `₴ ${(m.savingsMonth || 0).toFixed(2)}`,
            unit: 'UAH',
            color: 'green'
          },
          forecastAccuracy: {
            label: 'Forecast Accuracy',
            value: `${(m.forecastAccuracy || 0).toFixed(1)}%`,
            unit: '%',
            trend: 'stable',
            color: 'blue'
          },
          batteryHealth: {
            label: 'Battery SOC',
            value: `${(m.batteryHealth || 95).toFixed(0)}%`,
            unit: '%',
            trend: 'stable',
            color: 'yellow'
          },
          nextCycleIn: {
            label: 'Next Cycle In',
            value: m.nextCycleIn || '—',
            color: 'purple'
          },
          averagePrice: {
            label: 'Today\'s Avg Price',
            value: `${(m.averagePrice || 0).toFixed(2)}`,
            unit: '₴/kWh',
            color: 'slate'
          },
          peakPrice: {
            label: 'Peak Price',
            value: `${(m.peakPrice || 0).toFixed(2)}`,
            unit: '₴/kWh',
            color: 'red'
          },
          offPeakPrice: {
            label: 'Off-Peak Price',
            value: `${(m.offPeakPrice || 0).toFixed(2)}`,
            unit: '₴/kWh',
            color: 'green'
          }
        }
        lastFetchTime.value = new Date()
      } else {
        throw new Error(response.error || 'Failed to fetch metrics')
      }
    } catch (e) {
      console.error('Failed to fetch metrics:', e)
      error.value = (e as Error).message
    } finally {
      isLoading.value = false
    }
  }

  const startRealTimeUpdates = (intervalMs: number = 30000) => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
    }

    fetchMetrics()

    updateInterval.value = setInterval(() => {
      fetchMetrics()
    }, intervalMs)
  }

  const stopRealTimeUpdates = () => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
      updateInterval.value = null
    }
  }

  const updateMetric = (key: keyof DashboardMetrics, value: Partial<Metric>) => {
    if (metrics.value[key]) {
      metrics.value[key] = { ...metrics.value[key], ...value }
    }
  }

  const clearError = () => {
    error.value = null
  }

  const resetMetrics = () => {
    metrics.value = { ...DEFAULT_METRICS }
    error.value = null
  }

  return {
    // State
    metrics,
    isLoading,
    error,
    lastFetchTime,

    // Getters
    savingsToday,
    savingsMonth,
    accuracy,
    batteryHealth,
    allMetrics,
    getTooltip,

    // Actions
    fetchMetrics,
    startRealTimeUpdates,
    stopRealTimeUpdates,
    updateMetric,
    clearError,
    resetMetrics
  }
})
