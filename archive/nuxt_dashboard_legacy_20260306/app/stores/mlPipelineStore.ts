// Pinia store for monitoring ML pipeline performance

import { defineStore } from 'pinia'

export const useMLPipelineStore = defineStore('mlPipeline', () => {
  const recommendation = ref({
    action: 'HOLD',
    confidence: 0.5,
    rationale: 'Loading...',
    price: 14.26,
    battery_soc: 72.6,
  })
  
  const schedule24h = ref([])
  
  const mlflowStatus = ref({
    active_model: {
      version: '1.0.0',
      accuracy: 0.725,
      backtesting_profit: 1826.50,
    },
    monitoring: {
      drift_detected: false,
      accuracy_trend: [0.695, 0.710, 0.718, 0.725],
    },
  })
  
  const loading = ref(false)
  const error = ref(null)
  const lastUpdate = ref(null)
  
  // Fetch current recommendation from Dagster
  const fetchRecommendation = async () => {
    loading.value = true
    error.value = null
    
    try {
      const response = await $fetch('/api/dagster/recommendation')
      if (response.recommendation) {
        recommendation.value = {
          action: response.recommendation.action,
          confidence: response.recommendation.confidence,
          confidence_percent: response.recommendation.confidence_percent,
          rationale: response.recommendation.rationale,
          price: response.current_state.price_uah_kwh,
          battery_soc: response.current_state.battery_soc_percent,
        }
      }
      lastUpdate.value = new Date()
    } catch (e) {
      error.value = `Failed to fetch recommendation: ${e.message}`
      console.error('[MLPipeline] Error:', e)
    } finally {
      loading.value = false
    }
  }
  
  // Fetch 24-hour schedule
  const fetchSchedule24h = async () => {
    try {
      const response = await $fetch('/api/dagster/schedule-24h')
      if (response.schedule) {
        schedule24h.value = response.schedule
      }
    } catch (e) {
      console.error('[MLPipeline] Schedule fetch error:', e)
    }
  }
  
  // Fetch MLflow metrics
  const fetchMLflowStatus = async () => {
    try {
      const response = await $fetch('/api/mlflow/status')
      if (response.active_model) {
        mlflowStatus.value = response
      }
    } catch (e) {
      console.error('[MLPipeline] MLflow status error:', e)
    }
  }
  
  // Log metrics to MLflow
  const logMetrics = async (metrics) => {
    try {
      await $fetch('/api/mlflow/log-metrics', {
        method: 'POST',
        body: metrics,
      })
    } catch (e) {
      console.error('[MLPipeline] Metrics logging error:', e)
    }
  }
  
  // Initialize pipeline (fetch all data)
  const initialize = async () => {
    await Promise.all([
      fetchRecommendation(),
      fetchSchedule24h(),
      fetchMLflowStatus(),
    ])
  }
  
  // Auto-refresh every 5 minutes
  const startAutoRefresh = (interval = 5 * 60 * 1000) => {
    setInterval(() => {
      fetchRecommendation()
      fetchMLflowStatus()
    }, interval)
  }
  
  // Computed properties
  const actionColor = computed(() => {
    const actions = {
      'BUY': 'text-green-500',
      'SELL': 'text-yellow-500',
      'DISCHARGE': 'text-orange-500',
      'HOLD': 'text-gray-500',
    }
    return actions[recommendation.value.action] || 'text-gray-500'
  })
  
  const confidenceLevel = computed(() => {
    const conf = recommendation.value.confidence
    if (conf >= 0.8) return 'High'
    if (conf >= 0.6) return 'Medium'
    return 'Low'
  })
  
  const modelAccuracy = computed(() => {
    return mlflowStatus.value.active_model?.metrics?.test_accuracy || 0
  })
  
  const accuracyTrend = computed(() => {
    return mlflowStatus.value.monitoring?.accuracy_trend || []
  })
  
  const driftDetected = computed(() => {
    return mlflowStatus.value.monitoring?.drift_detected || false
  })
  
  return {
    // State
    recommendation,
    schedule24h,
    mlflowStatus,
    loading,
    error,
    lastUpdate,
    
    // Methods
    fetchRecommendation,
    fetchSchedule24h,
    fetchMLflowStatus,
    logMetrics,
    initialize,
    startAutoRefresh,
    
    // Computed
    actionColor,
    confidenceLevel,
    modelAccuracy,
    accuracyTrend,
    driftDetected,
  }
})
