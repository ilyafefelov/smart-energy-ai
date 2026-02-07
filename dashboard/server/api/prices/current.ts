// server/api/prices/current.ts - Current OREE prices with standardized response

// Simple in-memory cache to stabilize repeated requests (e.g., user clicking "Refresh" rapidly)
let PRICE_CACHE: { ts: number; data: any } | null = null
const CACHE_TTL_MS = 60 * 1000 // 1 minute

export default defineEventHandler(async (event) => {
  // GET /api/prices/current
  // STANDARDIZED RESPONSE: { success, prices: { current, today, forecast } }

  try {
    // Return cached response when available and fresh
    const nowTs = Date.now()
    if (PRICE_CACHE && (nowTs - PRICE_CACHE.ts) < CACHE_TTL_MS) {
      return PRICE_CACHE.data
    }

    // This would normally fetch from OREE database
    // For now, returning realistic Ukrainian energy prices (generated deterministically for the current hour window)
    const now = new Date()
    const hour = now.getHours()

    // Use a stable pseudo-random seed for the duration of the cache window to reduce noise
    // Create a simple seed from the current hour and minute-group (cache window)
    const seedGroup = Math.floor(nowTs / CACHE_TTL_MS)
    const seed = (hour * 31 + seedGroup) % 100000
    const rand = (n = 1) => {
      // simple xorshift-ish deterministic PRNG
      let x = (seed + 0x9e3779b9) & 0xffffffff
      x ^= x << 13
      x ^= x >>> 17
      x ^= x << 5
      return (Math.abs(x) % (n * 1000)) / 1000
    }

    // Simulate realistic hourly price variations
    const basePrice = 9.85
    const peakMultiplier = hour >= 8 && hour <= 20 ? 1.4 : 0.8
    // Use deterministic noise based on seed
    const currentPriceApprox = basePrice * peakMultiplier + (rand() - 0.5) * 2

    // Generate 24-hour forecast (deterministic within cache window)
    const forecast = Array.from({ length: 24 }, (_, i) => {
      const h = (hour + i) % 24
      const mult = h >= 8 && h <= 20 ? 1.4 : 0.8
      const noise = (rand() - 0.5) * 2
      const price = Math.max(5, Math.min(18, basePrice * mult + noise))
      return {
        hour: h,
        timestamp: new Date(now.getTime() + i * 3600000).toISOString(),
        price: Math.round(price * 100) / 100,
        confidence: Math.round((0.80 + (rand() * 0.15)) * 100) / 100,
        trend: i === 0 ? 'stable' : (rand() > 0.5 ? 'up' : 'down')
      }
    })

    const prices = forecast.slice(0, 24)

    const minPrice = Math.min(...prices.map(p => p.price))
    const maxPrice = Math.max(...prices.map(p => p.price))
    const avgPrice = prices.reduce((sum, p) => sum + p.price, 0) / prices.length
    const weightedPrice = prices.reduce((sum, p) => sum + p.price * (p.confidence || 0.9), 0) / prices.length

    // Identify peak and off-peak
    const peakPrices = prices.filter(p => p.hour >= 8 && p.hour <= 20)
    const offPeakPrices = prices.filter(p => p.hour < 8 || p.hour > 20)

    const peakPrice = peakPrices.length > 0
      ? peakPrices.reduce((sum, p) => sum + p.price, 0) / peakPrices.length
      : avgPrice

    const offPeakPrice = offPeakPrices.length > 0
      ? offPeakPrices.reduce((sum, p) => sum + p.price, 0) / offPeakPrices.length
      : avgPrice

    // Use the first forecast point as the canonical "current" price for consistency
    const canonicalCurrent = prices[0]?.price ?? Math.round(currentPriceApprox * 100) / 100

    const result = {
      success: true,
      prices: {
        current: {
          price: Math.round(canonicalCurrent * 100) / 100,
          timestamp: now.toISOString(),
          trend: canonicalCurrent > avgPrice * 1.1 ? 'up' : canonicalCurrent < avgPrice * 0.9 ? 'down' : 'stable'
        },
        today: {
          min: Math.round(minPrice * 100) / 100,
          max: Math.round(maxPrice * 100) / 100,
          avg: Math.round(avgPrice * 100) / 100,
          current: Math.round(canonicalCurrent * 100) / 100,
          weighted: Math.round(weightedPrice * 100) / 100
        },
        forecast: {
          next24h: prices.map(p => ({
            hour: p.hour,
            timestamp: p.timestamp,
            price: p.price,
            confidence: p.confidence,
            trend: p.trend
          })),
          peak: Math.round(peakPrice * 100) / 100,
          offPeak: Math.round(offPeakPrice * 100) / 100
        }
      }
    }

    // Cache the generated result for the TTL duration
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
