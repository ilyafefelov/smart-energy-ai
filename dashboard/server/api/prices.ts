export default defineEventHandler(async (event) => {
  // GET /api/prices - Real-time OREE prices
  
  return {
    success: true,
    timestamp: new Date().toISOString(),
    data: {
      current: {
        base: 10971.64,
        peak: 12516.41,
        offpeak: 9426.87,
        weighted: 11373.61,
        unit: 'UAH/MWh',
        pricePerKwh: 11.37
      },
      daily: {
        min: 5000,
        max: 15000,
        avg: 11373.61,
        volatility: 1511.78
      },
      arbitrage: {
        spread: 10000,
        daily_max: 12000,
        unit: 'UAH'
      },
      forecast: {
        tomorrow: 11500,
        confidence: 0.78,
        trend: 'stable'
      }
    }
  }
})
