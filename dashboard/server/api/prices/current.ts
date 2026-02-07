// server/api/prices/current.ts - Current OREE prices with standardized response

export default defineEventHandler(async (event) => {
  // GET /api/prices/current
  // STANDARDIZED RESPONSE: { success, prices: { current, today, forecast } }

  try {
    // This would normally fetch from OREE database
    // For now, returning realistic Ukrainian energy prices
    const now = new Date()
    const hour = now.getHours()

    // Simulate realistic hourly price variations
    const basePrice = 9.85
    const peakMultiplier = hour >= 8 && hour <= 20 ? 1.4 : 0.8
    const currentPrice = basePrice * peakMultiplier + (Math.random() - 0.5) * 2

    // Generate 24-hour forecast
    const forecast = Array.from({ length: 24 }, (_, i) => {
      const h = (hour + i) % 24
      const mult = h >= 8 && h <= 20 ? 1.4 : 0.8
      const price = basePrice * mult + (Math.random() - 0.5) * 2
      return {
        hour: h,
        timestamp: new Date(now.getTime() + i * 3600000).toISOString(),
        price: Math.max(5, Math.min(18, price)),
        confidence: 0.85 + Math.random() * 0.1,
        trend: i === 0 ? 'stable' : Math.random() > 0.5 ? 'up' : 'down'
      }
    })

    const prices = forecast.slice(0, 24)
    const todayPrices = prices.slice(hour)
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

    return {
      success: true,
      prices: {
        current: {
          price: Math.round(currentPrice * 100) / 100,
          timestamp: now.toISOString(),
          trend: currentPrice > avgPrice * 1.1 ? 'up' : currentPrice < avgPrice * 0.9 ? 'down' : 'stable'
        },
        today: {
          min: Math.round(minPrice * 100) / 100,
          max: Math.round(maxPrice * 100) / 100,
          avg: Math.round(avgPrice * 100) / 100,
          current: Math.round(currentPrice * 100) / 100,
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
  } catch (error: any) {
    console.error('Failed to fetch prices:', error)
    return {
      success: false,
      error: error.message || 'Failed to fetch prices',
      prices: null
    }
  }
})
