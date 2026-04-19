import { defineStore } from 'pinia'
import { useTenantContext } from '~/composables/useTenantContext'

type MLAction = 'BUY' | 'SELL' | 'HOLD'

export interface MLRecommendation {
  action: MLAction
  confidence: number
  reasoning: string
  timestamp: string
}

export interface SavingsEstimate {
  daily_uah: number
  monthly_uah: number
  annual_uah: number
}

export interface MLForecastHour {
  hour: number
  action: MLAction
  price_uah_mwh: number
  reasoning: string
}

export interface BatteryImpact {
  current_soc: number
  health_impact: number
  cycles_remaining: number
  health_percent?: number
}

export interface MLModelInfo {
  version: string
  confidence_level: string
}

interface MLRecommendationData {
  action: string
  confidence: number
  reasoning: string
  daily_forecast?: Array<{
    hour: number
    action: string
    price_uah_mwh: number
    reasoning: string
  }>
  savings_estimate?: Partial<SavingsEstimate>
  battery_impact?: Partial<BatteryImpact>
  timestamp: string
  model_info?: Partial<MLModelInfo>
}

interface MLRecommendationApiResponse {
  success: boolean
  data?: MLRecommendationData
  error?: string
}

type TenantRequest = {
  query: {
    tenantId: string
  }
  headers: {
    'x-tenant-id': string
  }
}

const normalizeTenantId = (tenantId?: string) => {
  return typeof tenantId === 'string' ? tenantId.trim().toLowerCase() : ''
}

const buildTenantRequest = (tenantId?: string): TenantRequest | undefined => {
  const normalized = normalizeTenantId(tenantId)
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

const normalizeAction = (action: unknown): MLAction => {
  const normalized = String(action || '').trim().toUpperCase()
  if (normalized === 'BUY') return 'BUY'
  if (normalized === 'SELL' || normalized === 'DISCHARGE') return 'SELL'
  return 'HOLD'
}

const toFiniteNumber = (value: unknown, fallback = 0) => {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : fallback
}

const normalizeSavingsEstimate = (value?: Partial<SavingsEstimate> | null): SavingsEstimate => ({
  daily_uah: toFiniteNumber(value?.daily_uah),
  monthly_uah: toFiniteNumber(value?.monthly_uah),
  annual_uah: toFiniteNumber(value?.annual_uah),
})

const normalizeBatteryImpact = (value?: Partial<BatteryImpact> | null): BatteryImpact => ({
  current_soc: toFiniteNumber(value?.current_soc),
  health_impact: toFiniteNumber(value?.health_impact),
  cycles_remaining: toFiniteNumber(value?.cycles_remaining),
  health_percent: value?.health_percent === undefined ? undefined : toFiniteNumber(value.health_percent),
})

const normalizeModelInfo = (value?: Partial<MLModelInfo> | null): MLModelInfo => ({
  version: String(value?.version || 'unknown'),
  confidence_level: String(value?.confidence_level || 'unknown'),
})

export const useMLStore = defineStore('ml', {
  state: () => ({
    currentRecommendation: null as MLRecommendation | null,
    dailyForecast: [] as MLForecastHour[],
    savingsEstimate: null as SavingsEstimate | null,
    batteryImpact: null as BatteryImpact | null,
    modelInfo: null as MLModelInfo | null,
    isLoading: false,
    error: null as string | null,
    lastUpdated: null as string | null,
    autoRefresh: false,
    refreshInterval: 5 * 60 * 1000,
    refreshTimer: null as ReturnType<typeof setInterval> | null,
  }),

  getters: {
    loading: (state): boolean => state.isLoading,

    recommendationColor: (state): string => {
      if (!state.currentRecommendation) return 'gray'

      switch (state.currentRecommendation.action) {
        case 'BUY':
          return 'green'
        case 'SELL':
          return 'blue'
        default:
          return 'gray'
      }
    },

    recommendationIcon: (state): string => {
      if (!state.currentRecommendation) return '⚪'

      switch (state.currentRecommendation.action) {
        case 'BUY':
          return '🟢'
        case 'SELL':
          return '🔵'
        default:
          return '⚪'
      }
    },

    isDataFresh: (state): boolean => {
      if (!state.lastUpdated) return false

      const lastUpdated = new Date(state.lastUpdated)
      if (Number.isNaN(lastUpdated.getTime())) return false

      const diffMinutes = (Date.now() - lastUpdated.getTime()) / (1000 * 60)
      return diffMinutes < 10
    },

    confidenceLevel: (state): string => {
      if (!state.currentRecommendation) return 'Unknown'

      const confidence = state.currentRecommendation.confidence
      if (confidence > 0.8) return 'High'
      if (confidence > 0.6) return 'Medium'
      return 'Low'
    },

    lastUpdatedFormatted: (state): string => {
      if (!state.lastUpdated) return 'Never'

      const lastUpdated = new Date(state.lastUpdated)
      if (Number.isNaN(lastUpdated.getTime())) return 'Never'
      return lastUpdated.toLocaleTimeString()
    },
  },

  actions: {
    async fetchRecommendation(tenantId?: string): Promise<void> {
      this.isLoading = true
      this.error = null

      try {
        const tenantContext = useTenantContext()
        let resolvedTenantId = normalizeTenantId(tenantId || tenantContext.currentTenantId.value)

        if (!resolvedTenantId) {
          await tenantContext.loadTenants().catch(() => undefined)
          resolvedTenantId = normalizeTenantId(tenantContext.currentTenantId.value)
        }

        const request = buildTenantRequest(resolvedTenantId)
        // This store intentionally uses the live ML route because the UI still renders
        // ML-specific enrichment fields such as savings and battery impact that are not
        // yet exposed by `/api/dagster/recommendation`. Do not treat this store as the
        // execution-authority source for auto-mode decisions.
        const response = request
          ? await $fetch<MLRecommendationApiResponse>('/api/ml/recommendation', request)
          : await $fetch<MLRecommendationApiResponse>('/api/ml/recommendation')

        if (!response.success || !response.data) {
          throw new Error(response.error || 'Failed to fetch ML recommendation')
        }

        const data = response.data

        this.currentRecommendation = {
          action: normalizeAction(data.action),
          confidence: toFiniteNumber(data.confidence),
          reasoning: String(data.reasoning || ''),
          timestamp: String(data.timestamp || new Date().toISOString()),
        }
        this.dailyForecast = Array.isArray(data.daily_forecast)
          ? data.daily_forecast.map((point) => ({
              hour: toFiniteNumber(point?.hour),
              action: normalizeAction(point?.action),
              price_uah_mwh: toFiniteNumber(point?.price_uah_mwh),
              reasoning: String(point?.reasoning || ''),
            }))
          : []
        this.savingsEstimate = normalizeSavingsEstimate(data.savings_estimate)
        this.batteryImpact = data.battery_impact ? normalizeBatteryImpact(data.battery_impact) : null
        this.modelInfo = data.model_info ? normalizeModelInfo(data.model_info) : null
        this.lastUpdated = new Date().toISOString()
      } catch (error) {
        console.error('[ML Store] Error fetching recommendation:', error)
        this.error = error instanceof Error ? error.message : 'Unknown error occurred'

        if (!this.currentRecommendation) {
          this.currentRecommendation = {
            action: 'HOLD',
            confidence: 0.5,
            reasoning: 'Error loading recommendation',
            timestamp: new Date().toISOString(),
          }
        }

        this.dailyForecast = []
      } finally {
        this.isLoading = false
      }
    },

    startAutoRefresh(intervalMs?: number, tenantId?: string): void {
      if (typeof intervalMs === 'number' && intervalMs > 0) {
        this.refreshInterval = intervalMs
      }

      if (this.refreshTimer) {
        clearInterval(this.refreshTimer)
      }

      this.autoRefresh = true
      void this.fetchRecommendation(tenantId)
      this.refreshTimer = setInterval(() => {
        void this.fetchRecommendation(tenantId)
      }, this.refreshInterval)
    },

    stopAutoRefresh(): void {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer)
        this.refreshTimer = null
      }
      this.autoRefresh = false
    },

    clearError(): void {
      this.error = null
    },

    getFormattedSavings(period: 'daily' | 'monthly' | 'annual'): string {
      const amount = this.savingsEstimate?.[`${period}_uah`] ?? 0
      return new Intl.NumberFormat('uk-UA', {
        style: 'currency',
        currency: 'UAH',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(amount)
    },

    getBatteryHealthPercent(): number {
      if (!this.batteryImpact) return 100
      if (typeof this.batteryImpact.health_percent === 'number') {
        return Math.max(0, Math.min(100, this.batteryImpact.health_percent))
      }

      const maxCycles = 6000
      return Math.max(0, Math.min(100, (this.batteryImpact.cycles_remaining / maxCycles) * 100))
    },

    getRecommendationIcon(): string {
      return this.recommendationIcon
    },
  },
})