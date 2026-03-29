export default defineEventHandler(async (event) => {
  // GET /api/history - Optimization history
  
  return {
    success: true,
    timestamp: new Date().toISOString(),
    data: [
      {
        date: '2026-02-06',
        cost_baseline: 13648,
        cost_optimized: 5746,
        savings: 7902,
        battery_actions: 8,
        price_min: 5000,
        price_max: 15000
      },
      {
        date: '2026-02-05',
        cost_baseline: 13648,
        cost_optimized: 5745,
        savings: 7903,
        battery_actions: 7,
        price_min: 5100,
        price_max: 14900
      },
      {
        date: '2026-02-04',
        cost_baseline: 13648,
        cost_optimized: 5747,
        savings: 7901,
        battery_actions: 9,
        price_min: 5440,
        price_max: 15000
      },
      {
        date: '2026-02-03',
        cost_baseline: 13648,
        cost_optimized: 5741,
        savings: 7907,
        battery_actions: 6,
        price_min: 5000,
        price_max: 15000
      },
      {
        date: '2026-02-02',
        cost_baseline: 13648,
        cost_optimized: 5746,
        savings: 7902,
        battery_actions: 8,
        price_min: 5400,
        price_max: 14973
      },
      {
        date: '2026-02-01',
        cost_baseline: 13648,
        cost_optimized: 5741,
        savings: 7907,
        battery_actions: 7,
        price_min: 6500,
        price_max: 15000
      }
    ]
  }
})
