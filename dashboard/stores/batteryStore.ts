import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useSettingsStore } from './settingsStore'

export interface BatteryState {
  soc: number // State of Charge (0-100%)
  voltage: number
  current: number
  power: number
  temperature: number
  health: number
  capacity: number
  lastUpdated: Date | null
}

export interface BatteryHistory {
  timestamp: Date
  soc: number
  power: number
  temperature: number
}

const DEFAULT_STATE: BatteryState = {
  soc: 50,
  voltage: 0,
  current: 0,
  power: 0,
  temperature: 25,
  health: 95,
  capacity: 150,
  lastUpdated: null
}

export const useBatteryStore = defineStore('battery', () => {
  const settingsStore = useSettingsStore()
  
  const state = ref<BatteryState>({ ...DEFAULT_STATE })
  const history = ref<BatteryHistory[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const updateInterval = ref<NodeJS.Timeout | null>(null)

  // Getters
  const soc = computed(() => state.value.soc)
  const socPercentage = computed(() => `${state.value.soc.toFixed(1)}%`)
  const power = computed(() => state.value.power)
  const temperature = computed(() => state.value.temperature)
  const health = computed(() => state.value.health)
  
  // Get capacity from settings, not hardcoded
  const capacity = computed(() => {
    return settingsStore.batterySettings.capacity
  })
  
  const isCharging = computed(() => state.value.power > 0)
  const isDischarging = computed(() => state.value.power < 0)
  const isIdle = computed(() => state.value.power === 0)

  const historySummary = computed(() => {
    if (history.value.length === 0) return null
    return {
      minSoc: Math.min(...history.value.map(h => h.soc)),
      maxSoc: Math.max(...history.value.map(h => h.soc)),
      avgPower: history.value.reduce((sum, h) => sum + h.power, 0) / history.value.length,
      count: history.value.length
    }
  })

  // Actions
  const fetchBatteryStatus = async () => {
    isLoading.value = true
    error.value = null

    try {
      const response = await $fetch('/api/battery/status') as any

      if (response.success && response.battery) {
        state.value = {
          ...response.battery,
          lastUpdated: new Date()
        }

        // Add to history
        history.value.push({
          timestamp: new Date(),
          soc: response.battery.soc,
          power: response.battery.power,
          temperature: response.battery.temperature
        })

        // Keep only last 100 entries
        if (history.value.length > 100) {
          history.value = history.value.slice(-100)
        }
      } else {
        throw new Error(response.error || 'Failed to fetch battery status')
      }
    } catch (e) {
      console.error('Failed to fetch battery status:', e)
      error.value = (e as Error).message
    } finally {
      isLoading.value = false
    }
  }

  const startRealTimeUpdates = (intervalMs: number = 5000) => {
    // Clear any existing interval
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
    }

    // Fetch immediately
    fetchBatteryStatus()

    // Set up recurring updates
    updateInterval.value = setInterval(() => {
      fetchBatteryStatus()
    }, intervalMs)
  }

  const stopRealTimeUpdates = () => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
      updateInterval.value = null
    }
  }

  const clearHistory = () => {
    history.value = []
  }

  const clearError = () => {
    error.value = null
  }

  const resetState = () => {
    state.value = { ...DEFAULT_STATE }
    history.value = []
    error.value = null
  }

  return {
    // State
    state,
    history,
    isLoading,
    error,

    // Getters
    soc,
    socPercentage,
    power,
    temperature,
    health,
    capacity,
    isCharging,
    isDischarging,
    isIdle,
    historySummary,

    // Actions
    fetchBatteryStatus,
    startRealTimeUpdates,
    stopRealTimeUpdates,
    clearHistory,
    clearError,
    resetState
  }
})
