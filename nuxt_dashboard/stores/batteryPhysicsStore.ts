import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface BatteryPhysicsState {
  // Battery state
  soc: number // 0-1
  socPercentage: number // 0-100
  power: number // kW (+ = charging, - = discharging)
  voltage: number // V
  current: number // A
  temperature: number // °C
  health: number // 0-100%
  cycleCount: number
  
  // Configuration
  type: 'LFP' | 'Lead-Acid' | 'VRFB'
  capacity: number // kWh
  usableCapacity: number // kWh
  socMin: number // %
  socMax: number // %
  
  // Operational limits
  maxChargePower: number // kW
  maxDischargePower: number // kW
  
  // Status
  isCharging: boolean
  isDischarging: boolean
  isIdle: boolean
  
  // Estimates
  estimatedRuntime: number | null // minutes
  estimatedChargeTime: number | null // minutes
  
  // Control
  powerCommand: number // kW
  manualMode: boolean
  autoOptimization: boolean
  
  // Simulation
  isSimulationRunning: boolean
  lastUpdated: Date | null
}

export interface BatterySpecs {
  typeName: string
  efficiency: number
  roundTripEfficiency: number
  nominalVoltage: number
  selfDischarge: number // % per day
}

export interface PowerFlowData {
  grid: number // kW
  battery: number // kW  
  solar: number // kW
  wind: number // kW
  load: number // kW
  timestamp: Date
}

const DEFAULT_STATE: BatteryPhysicsState = {
  soc: 0.5,
  socPercentage: 50,
  power: 0,
  voltage: 0,
  current: 0,
  temperature: 25,
  health: 95,
  cycleCount: 0,
  type: 'LFP',
  capacity: 10,
  usableCapacity: 8,
  socMin: 10,
  socMax: 90,
  maxChargePower: 5,
  maxDischargePower: 10,
  isCharging: false,
  isDischarging: false,
  isIdle: true,
  estimatedRuntime: null,
  estimatedChargeTime: null,
  powerCommand: 0,
  manualMode: true,
  autoOptimization: false,
  isSimulationRunning: false,
  lastUpdated: null
}

export const useBatteryPhysicsStore = defineStore('batteryPhysics', () => {
  // State
  const state = ref<BatteryPhysicsState>({ ...DEFAULT_STATE })
  const specs = ref<BatterySpecs | null>(null)
  const powerFlowHistory = ref<PowerFlowData[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const updateInterval = ref<NodeJS.Timeout | null>(null)

  // Computed
  const socColor = computed(() => {
    if (state.value.soc < 0.2) return 'text-red-400'
    if (state.value.soc < 0.4) return 'text-orange-400'
    if (state.value.soc < 0.8) return 'text-green-400'
    return 'text-blue-400'
  })

  const socGradient = computed(() => {
    if (state.value.soc < 0.2) return 'from-red-600 to-red-400'
    if (state.value.soc < 0.4) return 'from-orange-600 to-orange-400'
    if (state.value.soc < 0.8) return 'from-green-600 to-green-400'
    return 'from-blue-600 to-blue-400'
  })

  const powerStatus = computed(() => {
    if (state.value.isCharging) return { text: 'Charging', color: 'text-green-400', icon: '⚡' }
    if (state.value.isDischarging) return { text: 'Discharging', color: 'text-orange-400', icon: '🔋' }
    return { text: 'Idle', color: 'text-slate-400', icon: '⏸️' }
  })

  const healthStatus = computed(() => {
    if (state.value.health >= 90) return { text: 'Excellent', color: 'text-green-400' }
    if (state.value.health >= 80) return { text: 'Good', color: 'text-blue-400' }
    if (state.value.health >= 70) return { text: 'Fair', color: 'text-yellow-400' }
    if (state.value.health >= 60) return { text: 'Poor', color: 'text-orange-400' }
    return { text: 'Critical', color: 'text-red-400' }
  })

  const canCharge = computed(() => {
    return state.value.soc < (state.value.socMax / 100) && state.value.health > 0
  })

  const canDischarge = computed(() => {
    return state.value.soc > (state.value.socMin / 100) && state.value.health > 0
  })

  const batteryTypeInfo = computed(() => {
    const types = {
      'LFP': {
        name: 'Lithium Iron Phosphate',
        description: 'Long life, high safety, moderate energy density',
        pros: ['8000+ cycles', 'High safety', 'Fast charging'],
        cons: ['Higher cost', 'Lower energy density']
      },
      'Lead-Acid': {
        name: 'Lead-Acid Deep Cycle', 
        description: 'Low cost, proven technology, shorter lifespan',
        pros: ['Low cost', 'Reliable', 'Recyclable'],
        cons: ['600 cycles', 'Heavy', 'Maintenance required']
      },
      'VRFB': {
        name: 'Vanadium Redox Flow Battery',
        description: 'Long duration storage, independent power/energy scaling',
        pros: ['20000+ cycles', 'No degradation', 'Long duration'],
        cons: ['Low efficiency', 'High cost', 'Complex system']
      }
    }
    return types[state.value.type] || types['LFP']
  })

  // Actions
  const fetchBatteryData = async () => {
    isLoading.value = true
    error.value = null

    try {
      const response = await $fetch('/api/battery/simulate')
      
      if (response.success && response.battery) {
        state.value = {
          ...response.battery,
          lastUpdated: new Date(response.battery.lastUpdated)
        }
        
        if (response.specs) {
          specs.value = response.specs
        }

        // Add to power flow history
        addPowerFlowData({
          grid: 0, // TODO: Get from generation/load data
          battery: state.value.power,
          solar: 0, // TODO: Get from solar API
          wind: 0, // TODO: Get from wind API  
          load: 5, // TODO: Get from load profile
          timestamp: new Date()
        })

        console.log('[BatteryPhysics] Updated battery data:', state.value)
      } else {
        throw new Error(response.error || 'Failed to fetch battery data')
      }
    } catch (e) {
      console.error('[BatteryPhysics] Fetch error:', e)
      error.value = (e as Error).message
    } finally {
      isLoading.value = false
    }
  }

  const setPowerCommand = async (power: number) => {
    error.value = null

    try {
      const response = await $fetch('/api/battery/simulate', {
        method: 'POST',
        body: {
          action: 'setPower',
          power
        }
      })

      if (response.success) {
        state.value.powerCommand = response.powerCommand
        state.value.manualMode = true
        state.value.autoOptimization = false
        console.log(`[BatteryPhysics] Power command set to ${power}kW`)
      } else {
        throw new Error(response.error || 'Failed to set power')
      }
    } catch (e) {
      console.error('[BatteryPhysics] Power command error:', e)
      error.value = (e as Error).message
    }
  }

  const setAutoMode = async (enabled: boolean) => {
    error.value = null

    try {
      const response = await $fetch('/api/battery/simulate', {
        method: 'POST',
        body: {
          action: 'setAutoMode',
          enabled
        }
      })

      if (response.success) {
        state.value.manualMode = !enabled
        state.value.autoOptimization = enabled
        if (enabled) state.value.powerCommand = 0
        console.log(`[BatteryPhysics] Auto mode ${enabled ? 'enabled' : 'disabled'}`)
      } else {
        throw new Error(response.error || 'Failed to set auto mode')
      }
    } catch (e) {
      console.error('[BatteryPhysics] Auto mode error:', e)
      error.value = (e as Error).message
    }
  }

  const updateBatteryConfig = async (config: any) => {
    error.value = null

    try {
      const response = await $fetch('/api/battery/simulate', {
        method: 'POST',
        body: {
          action: 'updateConfig',
          config
        }
      })

      if (response.success) {
        // Update local state with new config
        await fetchBatteryData()
        console.log('[BatteryPhysics] Configuration updated')
      } else {
        throw new Error(response.error || 'Failed to update config')
      }
    } catch (e) {
      console.error('[BatteryPhysics] Config update error:', e)
      error.value = (e as Error).message
    }
  }

  const resetBattery = async (resetState?: any) => {
    error.value = null

    try {
      const response = await $fetch('/api/battery/simulate', {
        method: 'POST',
        body: {
          action: 'reset',
          ...resetState
        }
      })

      if (response.success) {
        await fetchBatteryData()
        console.log('[BatteryPhysics] Battery reset')
      } else {
        throw new Error(response.error || 'Failed to reset battery')
      }
    } catch (e) {
      console.error('[BatteryPhysics] Reset error:', e)
      error.value = (e as Error).message
    }
  }

  const startRealTimeUpdates = (intervalMs: number = 5000) => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
    }

    // Initial fetch
    fetchBatteryData()

    // Set up periodic updates
    updateInterval.value = setInterval(fetchBatteryData, intervalMs)
    console.log(`[BatteryPhysics] Started real-time updates (${intervalMs}ms interval)`)
  }

  const stopRealTimeUpdates = () => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
      updateInterval.value = null
    }
    console.log('[BatteryPhysics] Stopped real-time updates')
  }

  const addPowerFlowData = (data: PowerFlowData) => {
    powerFlowHistory.value.push(data)
    
    // Keep only last 100 data points
    if (powerFlowHistory.value.length > 100) {
      powerFlowHistory.value = powerFlowHistory.value.slice(-100)
    }
  }

  const clearError = () => {
    error.value = null
  }

  const clearHistory = () => {
    powerFlowHistory.value = []
  }

  // Convenience methods for UI controls
  const charge = (power: number) => setPowerCommand(Math.abs(power))
  const discharge = (power: number) => setPowerCommand(-Math.abs(power))
  const idle = () => setPowerCommand(0)
  
  const chargeMax = () => setPowerCommand(state.value.maxChargePower)
  const dischargeMax = () => setPowerCommand(-state.value.maxDischargePower)

  // Battery operation presets
  const startArbitrageCharge = () => {
    // Charge at 80% of max power for arbitrage
    const chargePower = state.value.maxChargePower * 0.8
    setPowerCommand(chargePower)
  }

  const startArbitrageDischarge = () => {
    // Discharge at 80% of max power for arbitrage
    const dischargePower = state.value.maxDischargePower * 0.8
    setPowerCommand(-dischargePower)
  }

  const startBalancedOperation = () => {
    // Enable auto mode for balanced operation
    setAutoMode(true)
  }

  return {
    // State
    state,
    specs,
    powerFlowHistory,
    isLoading,
    error,

    // Computed
    socColor,
    socGradient,
    powerStatus,
    healthStatus,
    canCharge,
    canDischarge,
    batteryTypeInfo,

    // Actions
    fetchBatteryData,
    setPowerCommand,
    setAutoMode,
    updateBatteryConfig,
    resetBattery,
    startRealTimeUpdates,
    stopRealTimeUpdates,
    clearError,
    clearHistory,

    // Convenience methods
    charge,
    discharge,
    idle,
    chargeMax,
    dischargeMax,
    startArbitrageCharge,
    startArbitrageDischarge,
    startBalancedOperation
  }
})