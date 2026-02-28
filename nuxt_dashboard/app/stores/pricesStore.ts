import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface PricePoint {
  hour: number
  price: number
  timestamp: Date
}

export interface PriceForecast {
  timestamp: Date
  price: number
  confidence: number
  trend: 'up' | 'down' | 'stable'
}

export interface PriceData {
  current: {
    price: number
    timestamp: Date
    trend: string
  }
  today: {
    min: number
    max: number
    avg: number
    current: number
    weighted: number
  }
  forecast: {
    next24h: PriceForecast[]
    peak: number
    offPeak: number
  }
}

const DEFAULT_DATA: PriceData = {
  current: {
    price: 0,
    timestamp: new Date(),
    trend: 'stable'
  },
  today: {
    min: 0,
    max: 0,
    avg: 0,
    current: 0,
    weighted: 0
  },
  forecast: {
    next24h: [],
    peak: 0,
    offPeak: 0
  }
}

export const usePricesStore = defineStore('prices', () => {
  const data = ref<PriceData>({ ...DEFAULT_DATA })
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastFetchTime = ref<Date | null>(null)
  const updateInterval = ref<NodeJS.Timeout | null>(null)

  // Getters
  const currentPrice = computed(() => data.value.current.price)
  const currentPriceFormatted = computed(() => `${data.value.current.price.toFixed(2)} ₴`)
  const currentPriceTimestamp = computed(() => data.value.current.timestamp)
  const todayMin = computed(() => data.value.today.min)
  const todayMax = computed(() => data.value.today.max)
  const todayAvg = computed(() => data.value.today.avg)
  const todayWeighted = computed(() => data.value.today.weighted)
  const forecast = computed(() => data.value.forecast.next24h)
  const peakPrice = computed(() => data.value.forecast.peak)
  const offPeakPrice = computed(() => data.value.forecast.offPeak)

  const priceStatus = computed(() => {
    const current = data.value.current.price
    const avg = data.value.today.avg
    const trend = data.value.current.trend || 'stable'

    if (current < avg * 0.8) return { status: 'low', icon: '📉', color: 'green', trend }
    if (current > avg * 1.2) return { status: 'high', icon: '📈', color: 'red', trend }
    return { status: 'normal', icon: '➡️', color: 'yellow', trend }
  })

  const arbitrageOpportunity = computed(() => {
    if (forecast.value.length === 0) return null
    const sortedByPrice = [...forecast.value].sort((a, b) => a.price - b.price)
    const lowestPrice = sortedByPrice[0].price
    const highestPrice = sortedByPrice[sortedByPrice.length - 1].price
    const spread = highestPrice - lowestPrice
    const spreadPercent = (spread / lowestPrice) * 100

    return {
      spread,
      spreadPercent: spreadPercent.toFixed(2),
      opportunity: spread > 2 // Meaningful opportunity if spread > 2 UAH
    }
  })

  // Actions
  const fetchPrices = async () => {
    isLoading.value = true
    error.value = null

    try {
      const response = await $fetch('/api/prices/current') as any

      if (response.success && response.prices) {
        // Standardize response format
        const prices = response.prices
        data.value = {
          current: {
            price: prices.current?.price || 0,
            timestamp: new Date(prices.current?.timestamp || new Date()),
            trend: prices.current?.trend || 'stable'
          },
          today: {
            min: prices.today?.min || 0,
            max: prices.today?.max || 0,
            avg: prices.today?.avg || 0,
            current: prices.today?.current || 0,
            weighted: prices.today?.weighted || 0
          },
          forecast: {
            next24h: (prices.forecast?.next24h || []).map((p: any) => ({
              timestamp: new Date(p.timestamp),
              price: p.price,
              confidence: p.confidence || 0.8,
              trend: p.trend || 'stable'
            })),
            peak: prices.forecast?.peak || 0,
            offPeak: prices.forecast?.offPeak || 0
          }
        }
        lastFetchTime.value = new Date()
      } else {
        throw new Error(response.error || 'Failed to fetch prices')
      }
    } catch (e) {
      console.error('Failed to fetch prices:', e)
      error.value = (e as Error).message
    } finally {
      isLoading.value = false
    }
  }

  const startRealTimeUpdates = (intervalMs: number = 60000) => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
    }

    fetchPrices()

    updateInterval.value = setInterval(() => {
      fetchPrices()
    }, intervalMs)
  }

  const stopRealTimeUpdates = () => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
      updateInterval.value = null
    }
  }

  const clearError = () => {
    error.value = null
  }

  const resetData = () => {
    data.value = { ...DEFAULT_DATA }
    error.value = null
  }

  return {
    // State
    data,
    isLoading,
    error,
    lastFetchTime,

    // Getters
    currentPrice,
    currentPriceTimestamp,
    currentPriceFormatted,
    todayMin,
    todayMax,
    todayAvg,
    todayWeighted,
    forecast,
    peakPrice,
    offPeakPrice,
    priceStatus,
    arbitrageOpportunity,

    // Actions
    fetchPrices,
    startRealTimeUpdates,
    stopRealTimeUpdates,
    clearError,
    resetData
  }
})
