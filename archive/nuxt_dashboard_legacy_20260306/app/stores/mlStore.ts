/**
 * ML Recommendations Store - Simple Version
 */
import { defineStore } from 'pinia'

export interface MLRecommendation {
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reasoning: string
  timestamp: string
}

export interface SavingsEstimate {
  daily_uah: number
  monthly_uah: number
  annual_uah: number
}

export const useMLStore = defineStore('ml', {
  state: () => ({
    currentRecommendation: null as MLRecommendation | null,
    savingsEstimate: {
      daily_uah: 0,
      monthly_uah: 0,
      annual_uah: 0
    } as SavingsEstimate,
    isLoading: false,
    error: null as string | null,
    lastUpdated: null as string | null
  }),

  actions: {
    async fetchRecommendation() {
      this.isLoading = true
      this.error = null

      try {
        const response = await $fetch('/api/ml/recommendation')
        
        if (response.success && response.data) {
          this.currentRecommendation = {
            action: response.data.action,
            confidence: response.data.confidence,
            reasoning: response.data.reasoning,
            timestamp: response.data.timestamp
          }
          
          this.savingsEstimate = response.data.savings_estimate
          this.lastUpdated = new Date().toISOString()
        } else {
          throw new Error(response.error || 'Failed to fetch recommendation')
        }
      } catch (error) {
        console.error('ML Store fetch error:', error)
        this.error = error instanceof Error ? error.message : 'Unknown error'
        
        // Set default values on error
        this.currentRecommendation = {
          action: 'HOLD',
          confidence: 0.5,
          reasoning: 'Error loading recommendation',
          timestamp: new Date().toISOString()
        }
      } finally {
        this.isLoading = false
      }
    },

    getFormattedSavings(period: 'daily' | 'monthly' | 'annual'): string {
      const value = this.savingsEstimate[`${period}_uah`]
      return `₴${value.toFixed(2)}`
    },

    getRecommendationIcon(): string {
      if (!this.currentRecommendation) return '⏸️'
      
      switch (this.currentRecommendation.action) {
        case 'BUY': return '🔋'
        case 'SELL': return '⚡'
        case 'HOLD': return '⏸️'
        default: return '❓'
      }
    }
  }
})