// server/api/prices/current.ts - Current OREE prices with stabilized responses

let PRICE_CACHE: { ts: number; data: any } | null = null
const CACHE_TTL_MS = 60 * 1000 // 1 minute cache

export default defineEventHandler(async (event) => {
  try {
    // Return cached response when available and fresh
    const nowTs = Date.now()
    if (PRICE_CACHE && (nowTs - PRICE_CACHE.ts) < CACHE_TTL_MS) {
      return PRICE_CACHE.data
    }

    const now = new Date()
    const hour = now.getHours()

    // Simple deterministic pricing based on time of day
    // Peak hours (8-20): higher prices; Off-peak: lower prices
    const basePrice = 9.85
    const isPeak = hour >= 8 && hour <= 20
    const peakMultiplier = isPeak ? 1.35 : 0.75

    // Deterministic variation based on hour (same result within cache TTL)
    const hourSeed = hour % 12
    const variation = (Math.sin(hourSeed * 0.5) * 2) // -2 to +2

    // Generate 24-hour forecast
    const prices = Array.from({ length: 24 }, (_, i) => {
      const h = (hour + i) % 24
      const hPeak = h >= 8 && h <= 20
      const hMult = hPeak ? 1.35 : 0.75
      const hSeed = h % 12
      const hVar = Math.sin(hSeed * 0.5) * 2
      const price = Math.max(5, Math.min(18, basePrice * hMult + hVar))

      return {
        hour: h,
        timestamp: new Date(now.getTime() + i * 3600000).toISOString(),
        price: Math.round(price * 100) / 100,
        confidence: 0.85 + (Math.abs(Math.cos(hSeed)) * 0.1), // 0.75-0.95
        trend: hVar > 0.5 ? 'up' : hVar < -0.5 ? 'down' : 'stable'
      }
    })

    // Calculate statistics
    const minPrice = Math.min(...prices.map(p => p.price))
    const maxPrice = Math.max(...prices.map(p => p.price))
    const avgPrice = Math.round((prices.reduce((sum, p) => sum + p.price, 0) / prices.length) * 100) / 100
    const weightedPrice = Math.round((prices.reduce((sum, p) => sum + p.price * p.confidence, 0) / prices.reduce((sum, p) => sum + p.confidence, 0)) * 100) / 100

    // Peak and off-peak averages
    const peakPrices = prices.filter(p => p.hour >= 8 && p.hour <= 20)
    const offPeakPrices = prices.filter(p => p.hour < 8 || p.hour > 20)

    const peakPrice = peakPrices.length > 0
      ? Math.round((peakPrices.reduce((sum, p) => sum + p.price, 0) / peakPrices.length) * 100) / 100
      : avgPrice

    const offPeakPrice = offPeakPrices.length > 0
      ? Math.round((offPeakPrices.reduce((sum, p) => sum + p.price, 0) / offPeakPrices.length) * 100) / 100
      : avgPrice

    // Current price is the first forecast entry (canonical)
    const currentPrice = prices[0].price

    const result = {
      success: true,
      prices: {
        current: {
          price: currentPrice,
          timestamp: now.toISOString(),
          trend: currentPrice > avgPrice * 1.05 ? 'up' : currentPrice < avgPrice * 0.95 ? 'down' : 'stable'
        },
        today: {
          min: Math.round(minPrice * 100) / 100,
          max: Math.round(maxPrice * 100) / 100,
          avg: avgPrice,
          current: currentPrice,
          weighted: weightedPrice
        },
        forecast: {
          next24h: prices,
          peak: peakPrice,
          offPeak: offPeakPrice
        }
      }
    }

    // Cache for next 60 seconds
    PRICE_CACHE = { ts: nowTs, data: result }

    return result
  } catch (error: any) {
    console.error('Failed to fetch prices:', error)
    return {
      success: false,
      error: error.message || 'Failed to fetch prices',
      prices: null
    }
  }
})
