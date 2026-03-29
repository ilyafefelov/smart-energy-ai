import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { useSettingsStore } from './settingsStore'

export interface BatteryMetrics {
  cyclesRemaining: number
  healthPercentage: number
  degradationCostToday: number
  degradationCostAnnual: number
  socCurrent: number
  socMin: number
  socMax: number
  chargePowerMax: number
  dischargePowerMax: number
  usableCapacity: number
}

export interface CostAnalytics {
  dailyArbitrageProfit: number
  peakAvoidanceSavings: number
  degradationCost: number
  netSavings: number
  monthlyProfit: number
  annualProfit: number
  batteryInvestment: number
  paybackPeriodYears: number
  roiPercent: number
  npv10Years: number
}

export interface MLMetrics {
  accuracy: number
  confidence: number
  featuresUsed: number
  lastTraining: Date
  modelType: string
  trainingDataPoints: number
  dataQualityScore: number
  predictionHorizonHours: number
}

export interface ArbitrageOpportunity {
  hour: number
  action: 'charge' | 'discharge' | 'hold'
  price: number
  profit: number
  confidence: number
  reason: string
}

export const useAnalyticsStore = defineStore('analytics', () => {
  const settingsStore = useSettingsStore()
  
  // State
  const isLoading = ref(false)
  const lastUpdate = ref<Date | null>(null)
  const error = ref<string | null>(null)
  
  // Analytics data
  const batteryMetrics = reactive<BatteryMetrics>({
    cyclesRemaining: 7850,
    healthPercentage: 98.5,
    degradationCostToday: 16.25,
    degradationCostAnnual: 5930,
    socCurrent: 45,
    socMin: 10,
    socMax: 90,
    chargePowerMax: 5.0,
    dischargePowerMax: 10.0,
    usableCapacity: 9.0
  })
  
  const costAnalytics = reactive<CostAnalytics>({
    dailyArbitrageProfit: 45.80,
    peakAvoidanceSavings: 12.30,
    degradationCost: 16.25,
    netSavings: 41.85,
    monthlyProfit: 1256,
    annualProfit: 15275,
    batteryInvestment: 130000,
    paybackPeriodYears: 8.5,
    roiPercent: 11.7,
    npv10Years: 24500
  })
  
  const mlMetrics = reactive<MLMetrics>({
    accuracy: 0.821,
    confidence: 0.89,
    featuresUsed: 47,
    lastTraining: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
    modelType: 'ensemble',
    trainingDataPoints: 8760,
    dataQualityScore: 0.94,
    predictionHorizonHours: 24
  })
  
  const arbitrageOpportunities = ref<ArbitrageOpportunity[]>([])
  
  // Computed properties
  const daysSinceTraining = computed(() => {
    const diffMs = Date.now() - mlMetrics.lastTraining.getTime()
    return Math.floor(diffMs / (1000 * 60 * 60 * 24))
  })
  
  const trainingStatus = computed(() => {
    const days = daysSinceTraining.value
    if (days < 3) return 'fresh'
    if (days < 7) return 'current'
    if (days < 14) return 'aging'
    return 'stale'
  })
  
  const mlStatus = computed(() => {
    return daysSinceTraining.value < 7 ? 'up-to-date' : 'needs-recalc'
  })
  
  const investmentViability = computed(() => {
    if (costAnalytics.roiPercent > 15) return 'excellent'
    if (costAnalytics.roiPercent > 8) return 'good'
    if (costAnalytics.roiPercent > 3) return 'marginal'
    return 'poor'
  })
  
  const batteryHealthStatus = computed(() => {
    if (batteryMetrics.healthPercentage >= 95) return 'excellent'
    if (batteryMetrics.healthPercentage >= 85) return 'good'
    if (batteryMetrics.healthPercentage >= 70) return 'fair'
    return 'poor'
  })
  
  // Actions
  const recalculateBatteryMetrics = async () => {
    try {
      const userConfig = settingsStore.userConfig
      if (!userConfig) return
      
      // Get battery specifications
      const batterySpecs = settingsStore.getBatterySpecs()
      
      // Calculate battery metrics based on current configuration
      const capacity = userConfig.battery_capacity_kwh
      const dodMax = userConfig.battery_dod_max
      const efficiency = userConfig.battery_efficiency
      const cRateCharge = userConfig.battery_c_rate_charge
      const cRateDischarge = userConfig.battery_c_rate_discharge
      
      // Update battery metrics
      batteryMetrics.usableCapacity = capacity * dodMax
      batteryMetrics.chargePowerMax = capacity * cRateCharge
      batteryMetrics.dischargePowerMax = capacity * cRateDischarge
      batteryMetrics.degradationCostToday = capacity * batterySpecs.cost_uah_per_kwh / batterySpecs.cycles_max
      batteryMetrics.degradationCostAnnual = batteryMetrics.degradationCostToday * 365
      batteryMetrics.cyclesRemaining = batterySpecs.cycles_max - Math.floor(Math.random() * 500)
      batteryMetrics.healthPercentage = 100 - (Math.random() * 5)
      batteryMetrics.socMin = userConfig.battery_soc_min * 100
      batteryMetrics.socMax = userConfig.battery_soc_max * 100
      
      console.log('[AnalyticsStore] Battery metrics recalculated:', batteryMetrics)
    } catch (error) {
      console.error('[AnalyticsStore] Failed to recalculate battery metrics:', error)
    }
  }
  
  const recalculateCostAnalytics = async () => {
    try {
      const userConfig = settingsStore.userConfig
      if (!userConfig) return
      
      const arbitrageMetrics = settingsStore.calculateArbitrageMetrics()
      
      // Update cost analytics
      costAnalytics.dailyArbitrageProfit = arbitrageMetrics.daily_arbitrage_gross
      costAnalytics.degradationCost = arbitrageMetrics.daily_degradation_cost
      costAnalytics.netSavings = arbitrageMetrics.daily_profit_net
      costAnalytics.monthlyProfit = arbitrageMetrics.daily_profit_net * 30
      costAnalytics.annualProfit = arbitrageMetrics.annual_profit
      costAnalytics.batteryInvestment = userConfig.battery_capacity_kwh * settingsStore.getBatterySpecs().cost_uah_per_kwh
      costAnalytics.paybackPeriodYears = arbitrageMetrics.payback_period_years || 999
      
      // Calculate ROI and NPV
      costAnalytics.roiPercent = costAnalytics.annualProfit > 0 
        ? (costAnalytics.annualProfit / costAnalytics.batteryInvestment) * 100 
        : 0
      
      // NPV calculation (10 years, 8% discount rate)
      const discountRate = 0.08
      let npv = -costAnalytics.batteryInvestment
      for (let year = 1; year <= 10; year++) {
        npv += costAnalytics.annualProfit / Math.pow(1 + discountRate, year)
      }
      costAnalytics.npv10Years = Math.round(npv)
      
      // Mock peak avoidance savings
      costAnalytics.peakAvoidanceSavings = userConfig.load_peak_kw * 2.5
      
      console.log('[AnalyticsStore] Cost analytics recalculated:', costAnalytics)
    } catch (error) {
      console.error('[AnalyticsStore] Failed to recalculate cost analytics:', error)
    }
  }
  
  const recalculateLoadAnalytics = async () => {
    try {
      const userConfig = settingsStore.userConfig
      if (!userConfig) return
      
      // Update load-dependent calculations
      await recalculateCostAnalytics()
      await generateArbitrageOpportunities()
      
      console.log('[AnalyticsStore] Load analytics recalculated')
    } catch (error) {
      console.error('[AnalyticsStore] Failed to recalculate load analytics:', error)
    }
  }
  
  const generateArbitrageOpportunities = async () => {
    try {
      const userConfig = settingsStore.userConfig
      if (!userConfig) return
      
      const opportunities: ArbitrageOpportunity[] = []
      
      // Generate 24-hour arbitrage schedule
      for (let hour = 0; hour < 24; hour++) {
        const isPeakHour = hour >= userConfig.tariff_peak_hours_start && hour <= userConfig.tariff_peak_hours_end
        const price = isPeakHour ? userConfig.tariff_peak_rate_uah_kwh : userConfig.tariff_off_peak_rate_uah_kwh
        
        let action: 'charge' | 'discharge' | 'hold' = 'hold'
        let profit = 0
        let confidence = 0.8
        let reason = 'Maintain current SOC'
        
        // Simple arbitrage logic
        if (!isPeakHour && hour >= 1 && hour <= 6) {
          // Off-peak charging window
          action = 'charge'
          profit = userConfig.tariff_peak_rate_uah_kwh - price
          confidence = 0.9
          reason = 'Off-peak charging opportunity'
        } else if (isPeakHour && hour >= 18 && hour <= 22) {
          // Peak discharging window
          action = 'discharge'
          profit = price - userConfig.tariff_off_peak_rate_uah_kwh
          confidence = 0.85
          reason = 'Peak price discharge opportunity'
        }
        
        opportunities.push({
          hour,
          action,
          price,
          profit: Math.max(0, profit),
          confidence,
          reason
        })
      }
      
      arbitrageOpportunities.value = opportunities
      console.log('[AnalyticsStore] Arbitrage opportunities generated:', opportunities.length)
    } catch (error) {
      console.error('[AnalyticsStore] Failed to generate arbitrage opportunities:', error)
    }
  }
  
  const recalculateAllMetrics = async () => {
    isLoading.value = true
    error.value = null
    
    try {
      await Promise.all([
        recalculateBatteryMetrics(),
        recalculateCostAnalytics(),
        generateArbitrageOpportunities()
      ])
      
      lastUpdate.value = new Date()
      console.log('[AnalyticsStore] All metrics recalculated successfully')
    } catch (err) {
      error.value = 'Failed to recalculate analytics'
      console.error('[AnalyticsStore] Recalculation failed:', err)
    } finally {
      isLoading.value = false
    }
  }
  
  const loadMLResults = async () => {
    try {
      // Try to load latest ML results from API
      const response = await $fetch('/api/ml/results')
      if (response.success && response.data) {
        Object.assign(mlMetrics, {
          accuracy: response.data.accuracy || mlMetrics.accuracy,
          confidence: response.data.confidence || mlMetrics.confidence,
          lastTraining: response.data.last_training ? new Date(response.data.last_training) : mlMetrics.lastTraining,
          trainingDataPoints: response.data.data_points || mlMetrics.trainingDataPoints,
          dataQualityScore: response.data.quality_score || mlMetrics.dataQualityScore
        })
      }
    } catch (error) {
      console.warn('[AnalyticsStore] Could not load ML results from API:', error)
    }
  }
  
  const refreshAllData = async () => {
    await Promise.all([
      recalculateAllMetrics(),
      loadMLResults()
    ])
  }
  
  // Generate battery SOC simulation for 24 hours
  const generateBatterySimulation = () => {
    const userConfig = settingsStore.userConfig
    if (!userConfig) return []
    
    const simulation: { hour: number, soc: number, action: string, profit: number }[] = []
    let currentSoc = 50 // Start at 50% SOC
    
    for (let hour = 0; hour < 24; hour++) {
      const opportunity = arbitrageOpportunities.value[hour]
      let socChange = 0
      
      if (opportunity?.action === 'charge' && currentSoc < userConfig.battery_soc_max * 100) {
        socChange = Math.min(
          userConfig.battery_c_rate_charge * 100 / 24, // Max charge rate per hour
          userConfig.battery_soc_max * 100 - currentSoc
        )
      } else if (opportunity?.action === 'discharge' && currentSoc > userConfig.battery_soc_min * 100) {
        socChange = -Math.min(
          userConfig.battery_c_rate_discharge * 100 / 24, // Max discharge rate per hour
          currentSoc - userConfig.battery_soc_min * 100
        )
      }
      
      currentSoc = Math.max(
        userConfig.battery_soc_min * 100,
        Math.min(userConfig.battery_soc_max * 100, currentSoc + socChange)
      )
      
      simulation.push({
        hour,
        soc: currentSoc,
        action: opportunity?.action || 'hold',
        profit: opportunity?.profit || 0
      })
    }
    
    return simulation
  }
  
  return {
    // State
    isLoading,
    lastUpdate,
    error,
    
    // Data
    batteryMetrics,
    costAnalytics,
    mlMetrics,
    arbitrageOpportunities,
    
    // Computed
    daysSinceTraining,
    trainingStatus,
    mlStatus,
    investmentViability,
    batteryHealthStatus,
    
    // Actions
    recalculateBatteryMetrics,
    recalculateCostAnalytics,
    recalculateLoadAnalytics,
    recalculateAllMetrics,
    generateArbitrageOpportunities,
    loadMLResults,
    refreshAllData,
    generateBatterySimulation
  }
})