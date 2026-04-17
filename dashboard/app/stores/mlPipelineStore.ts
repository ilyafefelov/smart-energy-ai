// Pinia store for monitoring ML pipeline performance

import { defineStore } from 'pinia'
import { useTenantContext } from '~/composables/useTenantContext'

type PipelineRecommendationAction = 'BUY' | 'SELL' | 'HOLD'

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
  recommended_action: PipelineRecommendationAction | 'DISCHARGE'
  expected_profit_uah: number
  confidence: number
  is_peak: boolean
  rationale?: string
}

type RecommendationState = {
  action: PipelineRecommendationAction
  confidence: number
  confidence_percent: number
  rationale: string
  price: number
  battery_soc: number
}

type MlflowFeatureImportance = {
  name: string
  importance: number
}

type MlflowActiveModelState = {
  name: string | null
  version: string | null
  stage: string | null
  metrics: Record<string, unknown>
  params: Record<string, unknown>
  feature_importance: MlflowFeatureImportance[]
  last_updated: string | null
  source: string | null
  authoritative_for_runtime_serving: boolean
  accuracy: number
  backtesting_profit: number
}

type MlflowStatusState = {
  status: string
  timestamp: string | null
  service_role: string | null
  mlflow_connected: boolean
  runtime_serving_authoritative: boolean
  runtime_serving_source: string | null
  tracking_uri: string | null
  active_model: MlflowActiveModelState
  monitoring: {
    drift_detected: boolean
    accuracy_trend: number[]
    recommendations: string[]
    last_evaluation: string | null
  }
}

type DagsterRecommendationResponse = {
  recommendation?: {
    action?: string | null
    confidence?: number | null
    confidence_percent?: number | null
    rationale?: string | null
  } | null
  current_state?: {
    price_uah_kwh?: number | null
    battery_soc_percent?: number | null
  } | null
}

type MlflowStatusResponse = {
  status?: string
  timestamp?: string | null
  service_role?: string | null
  mlflow_connected?: boolean | null
  runtime_serving_authoritative?: boolean | null
  runtime_serving_source?: string | null
  tracking_uri?: string | null
  active_model?: {
    name?: string | null
    version?: string | null
    stage?: string | null
    metrics?: Record<string, unknown> | null
    params?: Record<string, unknown> | null
    feature_importance?: Array<{ name?: string | null; importance?: number | null }> | null
    last_updated?: string | null
    source?: string | null
    authoritative_for_runtime_serving?: boolean | null
  } | null
  monitoring?: {
    drift_detected?: boolean | null
    accuracy_trend?: Array<number | null> | null
    recommendations?: Array<string | null> | null
    last_evaluation?: string | null
  } | null
}

type Schedule24hResponse = {
  schedule?: Array<{
    hour?: number | null
    price_uah_kwh?: number | null
    recommended_action?: string | null
    expected_profit_uah?: number | null
    confidence?: number | null
    is_peak?: boolean | null
    rationale?: string | null
  }> | null
}

type TenantRequest = {
  query: {
    tenantId: string
  }
  headers: {
    'x-tenant-id': string
  }
}

const DEFAULT_RECOMMENDATION: RecommendationState = {
  action: 'HOLD',
  confidence: 0.5,
  confidence_percent: 50,
  rationale: 'Loading...',
  price: 14.26,
  battery_soc: 72.6,
}

const DEFAULT_MLFLOW_STATUS: MlflowStatusState = {
  status: 'unknown',
  timestamp: null,
  service_role: null,
  mlflow_connected: false,
  runtime_serving_authoritative: false,
  runtime_serving_source: null,
  tracking_uri: null,
  active_model: {
    name: null,
    version: '1.0.0',
    stage: null,
    metrics: {},
    params: {},
    feature_importance: [],
    last_updated: null,
    source: null,
    authoritative_for_runtime_serving: false,
    accuracy: 0.725,
    backtesting_profit: 1826.5,
  },
  monitoring: {
    drift_detected: false,
    accuracy_trend: [0.695, 0.71, 0.718, 0.725],
    recommendations: [],
    last_evaluation: null,
  },
}

function normalizeAction(value: unknown): PipelineRecommendationAction {
  const normalized = String(value || '').trim().toUpperCase()
  if (normalized === 'BUY') return 'BUY'
  if (normalized === 'SELL' || normalized === 'DISCHARGE') return 'SELL'
  return 'HOLD'
}

function toFiniteNumber(value: unknown, fallback = 0): number {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  if (typeof error === 'string' && error.trim()) {
    return error
  }
  return fallback
}

function normalizeRecommendationResponse(response: DagsterRecommendationResponse): RecommendationState | null {
  if (!response.recommendation) {
    return null
  }

  return {
    action: normalizeAction(response.recommendation.action),
    confidence: toFiniteNumber(response.recommendation.confidence, DEFAULT_RECOMMENDATION.confidence),
    confidence_percent: toFiniteNumber(response.recommendation.confidence_percent, DEFAULT_RECOMMENDATION.confidence_percent),
    rationale: String(response.recommendation.rationale || DEFAULT_RECOMMENDATION.rationale),
    price: toFiniteNumber(response.current_state?.price_uah_kwh, DEFAULT_RECOMMENDATION.price),
    battery_soc: toFiniteNumber(response.current_state?.battery_soc_percent, DEFAULT_RECOMMENDATION.battery_soc),
  }
}

function normalizeMlflowStatus(response: MlflowStatusResponse): MlflowStatusState {
  const metrics = response.active_model?.metrics && typeof response.active_model.metrics === 'object'
    ? response.active_model.metrics
    : {}
  const accuracyMetric = toFiniteNumber(metrics.test_accuracy, DEFAULT_MLFLOW_STATUS.active_model.accuracy)
  const profitMetric = toFiniteNumber(metrics.backtesting_profit, DEFAULT_MLFLOW_STATUS.active_model.backtesting_profit)
  const featureImportance = Array.isArray(response.active_model?.feature_importance)
    ? response.active_model.feature_importance.map((item, index) => ({
        name: typeof item?.name === 'string' && item.name.trim() ? item.name : `feature_${index + 1}`,
        importance: toFiniteNumber(item?.importance),
      }))
    : DEFAULT_MLFLOW_STATUS.active_model.feature_importance
  const accuracyTrend = Array.isArray(response.monitoring?.accuracy_trend)
    ? response.monitoring.accuracy_trend.map((value) => toFiniteNumber(value)).filter((value) => Number.isFinite(value))
    : DEFAULT_MLFLOW_STATUS.monitoring.accuracy_trend
  const recommendations = Array.isArray(response.monitoring?.recommendations)
    ? response.monitoring.recommendations.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
    : []

  return {
    status: String(response.status || DEFAULT_MLFLOW_STATUS.status),
    timestamp: typeof response.timestamp === 'string' ? response.timestamp : DEFAULT_MLFLOW_STATUS.timestamp,
    service_role: typeof response.service_role === 'string' ? response.service_role : DEFAULT_MLFLOW_STATUS.service_role,
    mlflow_connected: Boolean(response.mlflow_connected),
    runtime_serving_authoritative: Boolean(response.runtime_serving_authoritative),
    runtime_serving_source: typeof response.runtime_serving_source === 'string'
      ? response.runtime_serving_source
      : DEFAULT_MLFLOW_STATUS.runtime_serving_source,
    tracking_uri: typeof response.tracking_uri === 'string' ? response.tracking_uri : DEFAULT_MLFLOW_STATUS.tracking_uri,
    active_model: {
      name: typeof response.active_model?.name === 'string' ? response.active_model.name : null,
      version: typeof response.active_model?.version === 'string' ? response.active_model.version : DEFAULT_MLFLOW_STATUS.active_model.version,
      stage: typeof response.active_model?.stage === 'string' ? response.active_model.stage : null,
      metrics,
      params: response.active_model?.params && typeof response.active_model.params === 'object' ? response.active_model.params : {},
      feature_importance: featureImportance,
      last_updated: typeof response.active_model?.last_updated === 'string' ? response.active_model.last_updated : null,
      source: typeof response.active_model?.source === 'string' ? response.active_model.source : null,
      authoritative_for_runtime_serving: Boolean(response.active_model?.authoritative_for_runtime_serving),
      accuracy: accuracyMetric,
      backtesting_profit: profitMetric,
    },
    monitoring: {
      drift_detected: Boolean(response.monitoring?.drift_detected),
      accuracy_trend: accuracyTrend.length > 0 ? accuracyTrend : DEFAULT_MLFLOW_STATUS.monitoring.accuracy_trend,
      recommendations,
      last_evaluation: typeof response.monitoring?.last_evaluation === 'string' ? response.monitoring.last_evaluation : null,
    },
  }
}

function resolveTenantRequest(tenantId?: string): TenantRequest | undefined {
  const normalized = typeof tenantId === 'string' ? tenantId.trim().toLowerCase() : ''
  if (!normalized) {
    return undefined
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

  const recommendation = ref<RecommendationState>({ ...DEFAULT_RECOMMENDATION })
  
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
  
  const mlflowStatus = ref<MlflowStatusState>({ ...DEFAULT_MLFLOW_STATUS })
  
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdate = ref<Date | null>(null)
  
  // Fetch current recommendation from Dagster
  const fetchRecommendation = async (tenantId?: string) => {
    loading.value = true
    error.value = null
    
    try {
      const request = resolveTenantRequest(tenantId)
      const response = request
        ? await $fetch<DagsterRecommendationResponse>('/api/dagster/recommendation', request)
        : await $fetch<DagsterRecommendationResponse>('/api/dagster/recommendation')
      const normalized = normalizeRecommendationResponse(response)
      if (normalized) {
        recommendation.value = normalized
      }
      lastUpdate.value = new Date()
    } catch (e) {
      error.value = `Failed to fetch recommendation: ${getErrorMessage(e, 'unknown error')}`
      console.error('[MLPipeline] Error:', e)
    } finally {
      loading.value = false
    }
  }
  
  // Fetch 24-hour schedule
  const fetchSchedule24h = async (tenantId?: string) => {
    try {
      const request = resolveTenantRequest(tenantId)
      const response = request
        ? await $fetch<Schedule24hResponse>('/api/dagster/schedule-24h', request)
        : await $fetch<Schedule24hResponse>('/api/dagster/schedule-24h')
      if (Array.isArray(response.schedule)) {
        schedule24h.value = response.schedule.map((row) => ({
          hour: toFiniteNumber(row?.hour),
          time: `${String(Math.max(0, Math.min(23, toFiniteNumber(row?.hour)))).padStart(2, '0')}:00`,
          price_uah_kwh: toFiniteNumber(row?.price_uah_kwh),
          recommended_action: String(row?.recommended_action || 'HOLD').toUpperCase() as Schedule24hRow['recommended_action'],
          expected_profit_uah: toFiniteNumber(row?.expected_profit_uah),
          confidence: toFiniteNumber(row?.confidence),
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
      const request = resolveTenantRequest(tenantId)
      const response = request
        ? await $fetch<MlflowStatusResponse>('/api/mlflow/status', request)
        : await $fetch<MlflowStatusResponse>('/api/mlflow/status')
      mlflowStatus.value = normalizeMlflowStatus(response)
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
  const logMetrics = async (metrics: Record<string, unknown>) => {
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
    if (recommendation.value.action === 'BUY') return 'text-green-500'
    if (recommendation.value.action === 'SELL') return 'text-yellow-500'
    return 'text-gray-500'
  })
  
  const confidenceLevel = computed(() => {
    const conf = recommendation.value.confidence
    if (conf >= 0.8) return 'High'
    if (conf >= 0.6) return 'Medium'
    return 'Low'
  })
  
  const modelAccuracy = computed(() => {
    return toFiniteNumber(mlflowStatus.value.active_model.metrics.test_accuracy, mlflowStatus.value.active_model.accuracy)
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
