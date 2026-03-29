/**
 * ML Recommendations Pinia Store
 * 
 * Manages ML recommendation state and auto-refresh functionality
 */
import { defineStore } from 'pinia'

export interface MLRecommendation {
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reasoning: string
  timestamp: string
}

export interface DailyForecast {
  hour: number
  action: string
  price_uah_mwh: number
  reasoning: string
}

export interface SavingsEstimate {
  daily_uah: number
  monthly_uah: number
  annual_uah: number
}

export interface BatteryImpact {
  current_soc: number
  health_impact: number
  cycles_remaining: number
}

export interface MLModelInfo {
  version: string
  confidence_level: string
}

export interface MLRecommendationData {
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reasoning: string
  daily_forecast: DailyForecast[]
  savings_estimate: SavingsEstimate
  battery_impact: BatteryImpact
  timestamp: string
  model_info: MLModelInfo
}

export const useMLStore = defineStore('ml', {
  state: () => ({
    // Current recommendation state
    currentRecommendation: null as MLRecommendation | null,
    dailyForecast: [] as DailyForecast[],
    savingsEstimate: null as SavingsEstimate | null,
    batteryImpact: null as BatteryImpact | null,
    modelInfo: null as MLModelInfo | null,
    
    // UI state
    loading: false,
    error: null as string | null,
    lastUpdated: null as Date | null,
    autoRefresh: false,
    refreshInterval: 5 * 60 * 1000, // 5 minutes
    
    // Auto-refresh timer
    refreshTimer: null as NodeJS.Timeout | null
  }),

  getters: {
    // Get recommendation color based on action
    recommendationColor: (state): string => {
      if (!state.currentRecommendation) return 'gray'
      
      switch (state.currentRecommendation.action) {
        case 'BUY': return 'green'
        case 'SELL': return 'blue' 
        case 'HOLD': return 'gray'
        default: return 'gray'
      }
    },
    
    // Get recommendation icon
    recommendationIcon: (state): string => {
      if (!state.currentRecommendation) return '⚪'
      
      switch (state.currentRecommendation.action) {
        case 'BUY': return '🟢'
        case 'SELL': return '🔵'
        case 'HOLD': return '⚪'
        default: return '⚪'
      }
    },
    
    // Check if data is fresh (less than 10 minutes old)
    isDataFresh: (state): boolean => {
      if (!state.lastUpdated) return false
      const now = new Date()
      const diffMinutes = (now.getTime() - state.lastUpdated.getTime()) / (1000 * 60)
      return diffMinutes < 10
    },
    
    // Get confidence level description
    confidenceLevel: (state): string => {
      if (!state.currentRecommendation) return 'Unknown'
      
      const confidence = state.currentRecommendation.confidence
      if (confidence > 0.8) return 'High'
      if (confidence > 0.6) return 'Medium'
      return 'Low'
    },
    
    // Format last updated time
    lastUpdatedFormatted: (state): string => {
      if (!state.lastUpdated) return 'Never'
      return state.lastUpdated.toLocaleTimeString()
    }
  },

  actions: {
    // Fetch ML recommendation from API
    async fetchRecommendation(): Promise<void> {
      this.loading = true
      this.error = null
      
      try {
        const response = await $fetch<{success: boolean, data?: MLRecommendationData, error?: string}>('/api/ml/recommendation')
        
        if (!response.success || !response.data) {
          throw new Error(response.error || 'Failed to fetch ML recommendation')
        }
        
        const data = response.data
        
        // Update state with new data
        this.currentRecommendation = {
          action: data.action,
          confidence: data.confidence,
          reasoning: data.reasoning,
          timestamp: data.timestamp
        }
        
        this.dailyForecast = data.daily_forecast
        this.savingsEstimate = data.savings_estimate
        this.batteryImpact = data.battery_impact
        this.modelInfo = data.model_info
        this.lastUpdated = new Date()
        
        console.log(`[ML Store] Updated recommendation: ${data.action} (confidence: ${data.confidence})`)
        
      } catch (error) {
        console.error('[ML Store] Error fetching recommendation:', error)
        this.error = error instanceof Error ? error.message : 'Unknown error occurred'
      } finally {
        this.loading = false
      }
    },
    
    // Start auto-refresh
    startAutoRefresh(): void {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer)
      }
      
      this.autoRefresh = true
      this.refreshTimer = setInterval(() => {
        console.log('[ML Store] Auto-refreshing recommendation...')
        this.fetchRecommendation()
      }, this.refreshInterval)
      
      // Fetch immediately
      this.fetchRecommendation()
    },
    
    // Stop auto-refresh
    stopAutoRefresh(): void {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer)
        this.refreshTimer = null
      }
      this.autoRefresh = false
    },
    
    // Update refresh interval (in minutes)
    updateRefreshInterval(minutes: number): void {
      this.refreshInterval = minutes * 60 * 1000
      
      // Restart auto-refresh with new interval if currently active
      if (this.autoRefresh) {
        this.startAutoRefresh()
      }
    },
    
    // Clear error
    clearError(): void {
      this.error = null
    },
    
    // Get formatted savings for display
    getFormattedSavings(period: 'daily' | 'monthly' | 'annual'): string {
      if (!this.savingsEstimate) return '₴0.00'
      
      const amount = this.savingsEstimate[`${period}_uah`]
      return new Intl.NumberFormat('uk-UA', {
        style: 'currency',
        currency: 'UAH',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(amount)
    },
    
    // Get battery health percentage
    getBatteryHealthPercent(): number {
      if (!this.batteryImpact) return 100
      
      // Convert cycles remaining to health percentage (rough estimate)
      const maxCycles = 6000 // Typical LFP battery
      const cyclesRemaining = this.batteryImpact.cycles_remaining
      return Math.max(0, Math.min(100, (cyclesRemaining / maxCycles) * 100))
    }
  }
})