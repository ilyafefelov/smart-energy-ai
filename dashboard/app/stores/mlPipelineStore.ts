// Pinia store for monitoring ML pipeline performance

import { defineStore } from 'pinia'
import { useTenantContext } from '~/composables/useTenantContext'

type RecommendationExecutionLink = {
  mode: string
  active_command: string
  requested_command: string | null
  decision_source: string
  realized_net_today_uah: number
  auto_transitions_today: number
  economics_source: string
  last_history_date: string | null
  last_control_update: string | null
  synced_at: string | null
}

type Schedule24hRow = {
  hour: number
  time: string
  price_uah_kwh: number
  recommended_action: 'BUY' | 'SELL' | 'HOLD' | 'DISCHARGE'
  expected_profit_uah: number
  confidence: number
  is_peak: boolean
  rationale?: string
}

function resolveTenantRequest(tenantId?: string) {
  const normalized = typeof tenantId === 'string' ? tenantId.trim().toLowerCase() : ''
  if (!normalized) {
    return {}
  }

  return {
    query: {
      tenantId: normalized,
    },
    headers: {
      'x-tenant-id': normalized,
    },
  }
}

export const useMLPipelineStore = defineStore('mlPipeline', () => {
  const tenantContext = useTenantContext()

  const recommendation = ref({
    action: 'HOLD',
    confidence: 0.5,
    rationale: 'Loading...',
    price: 14.26,
    battery_soc: 72.6,
  })
  
  const schedule24h = ref<Schedule24hRow[]>([])

  const recommendationExecutionLink = ref<RecommendationExecutionLink>({
    mode: 'unknown',
    active_command: 'idle',
    requested_command: null,
    decision_source: 'unknown',
    realized_net_today_uah: 0,
    auto_transitions_today: 0,
    economics_source: 'unknown',
    last_history_date: null,
    last_control_update: null,
    synced_at: null,
  })
  
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
  const fetchRecommendation = async (tenantId?: string) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await $fetch('/api/dagster/recommendation', resolveTenantRequest(tenantId))
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
      error.value = `Failed to fetch recommendation: ${e?.message || 'unknown error'}`
      console.error('[MLPipeline] Error:', e)
    } finally {
      loading.value = false
    }
  }
  
  // Fetch 24-hour schedule
  const fetchSchedule24h = async (tenantId?: string) => {
    try {
      const response = await $fetch('/api/dagster/schedule-24h', resolveTenantRequest(tenantId))
      if (Array.isArray(response.schedule)) {
        schedule24h.value = response.schedule.map((row: any) => ({
          hour: Number(row?.hour ?? 0),
          time: String(row?.time || `${String(Number(row?.hour ?? 0)).padStart(2, '0')}:00`),
          price_uah_kwh: Number(row?.price_uah_kwh || 0),
          recommended_action: String(row?.recommended_action || 'HOLD').toUpperCase() as Schedule24hRow['recommended_action'],
          expected_profit_uah: Number(row?.expected_profit_uah || 0),
          confidence: Number(row?.confidence || 0),
          is_peak: Boolean(row?.is_peak),
          rationale: typeof row?.rationale === 'string' ? row.rationale : undefined,
        }))
      }
    } catch (e) {
      console.error('[MLPipeline] Schedule fetch error:', e)
    }
  }
  
  // Fetch MLflow metrics
  const fetchMLflowStatus = async (tenantId?: string) => {
    try {
      const response = await $fetch('/api/mlflow/status', resolveTenantRequest(tenantId))
      if (response.active_model) {
        mlflowStatus.value = response
      }
    } catch (e) {
      console.error('[MLPipeline] MLflow status error:', e)
    }
  }

  const fetchRecommendationExecutionLink = async (tenantId?: string) => {
    try {
      const request = resolveTenantRequest(tenantId)
      const historyQuery = {
        ...(request as any).query,
        days: 1,
        limit: 2,
      }

      const [statusResponse, historyResponse] = await Promise.all([
        $fetch<any>('/api/control/status', request).catch(() => null),
        $fetch<any>('/api/history', {
          ...(request as any),
          query: historyQuery,
        }).catch(() => null),
      ])

      const historyRows = Array.isArray(historyResponse?.data) ? historyResponse.data : []
      const latestHistory = historyRows.length > 0 ? historyRows[historyRows.length - 1] : null

      recommendationExecutionLink.value = {
        mode: String(statusResponse?.mode || 'unknown'),
        active_command: String(statusResponse?.active_command || 'idle'),
        requested_command: statusResponse?.requested_command ? String(statusResponse.requested_command) : null,
        decision_source: String(statusResponse?.decision_source || 'unknown'),
        realized_net_today_uah: Number(latestHistory?.realized_net_uah || latestHistory?.savings || 0),
        auto_transitions_today: Number(latestHistory?.auto_transitions || 0),
        economics_source: String(historyResponse?.source?.economics_source || 'unknown'),
        last_history_date: latestHistory?.date ? String(latestHistory.date) : null,
        last_control_update: statusResponse?.last_update ? String(statusResponse.last_update) : null,
        synced_at: new Date().toISOString(),
      }
    } catch (e) {
      console.error('[MLPipeline] Recommendation execution link error:', e)
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
    await tenantContext.loadTenants()
    const tenantId = tenantContext.currentTenantId.value
    await Promise.all([
      fetchRecommendation(tenantId),
      fetchSchedule24h(tenantId),
      fetchMLflowStatus(tenantId),
      fetchRecommendationExecutionLink(tenantId),
    ])
  }
  
  // Auto-refresh every 5 minutes
  const startAutoRefresh = (interval = 5 * 60 * 1000) => {
    setInterval(() => {
      const tenantId = tenantContext.currentTenantId.value
      fetchRecommendation(tenantId)
      fetchSchedule24h(tenantId)
      fetchMLflowStatus(tenantId)
      fetchRecommendationExecutionLink(tenantId)
    }, interval)
  }

  const executionLinkSummary = computed(() => {
    const link = recommendationExecutionLink.value
    const mode = String(link.mode || 'unknown').toUpperCase()
    const action = String(link.active_command || 'idle').toUpperCase()
    const source = String(link.decision_source || 'unknown').toUpperCase()
    const net = Number(link.realized_net_today_uah || 0).toFixed(0)
    return `Mode ${mode} | Action ${action} | Source ${source} | Net today ${net} UAH`
  })
  
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
    recommendationExecutionLink,
    mlflowStatus,
    loading,
    error,
    lastUpdate,
    
    // Methods
    fetchRecommendation,
    fetchSchedule24h,
    fetchMLflowStatus,
    fetchRecommendationExecutionLink,
    logMetrics,
    initialize,
    startAutoRefresh,
    
    // Computed
    actionColor,
    confidenceLevel,
    modelAccuracy,
    accuracyTrend,
    driftDetected,
    executionLinkSummary,
  }
})
