import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { createBatteryPhysics, type BatteryConfig, type BatteryState } from '~/utils/batteryPhysics'

const DEFAULT_CONFIG: BatteryConfig = {
  type: 'LFP',
  capacity: 150,
  efficiency: 0.95,
  cRateCharge: 0.5,
  cRateDischarge: 0.5,
  socMin: 0.15,
  socMax: 0.95,
  temperature: 25,
  degradationRate: 0.0001,
  maxCycles: 8000
}

interface ExtendedBatteryState extends BatteryState {
  socPercentage: number
  maxChargePower: number
  maxDischargePower: number
}

export const useBatteryPhysicsStore = defineStore('batteryPhysics', () => {
  const config = ref<BatteryConfig>({ ...DEFAULT_CONFIG })
  const rawState = ref<BatteryState>({
    soc: 0.5,
    temperature: 25,
    voltage: 0,
    current: 0,
    power: 0,
    health: 1.0,
    cycleCount: 0,
    lastUpdated: new Date()
  })
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const updateInterval = ref<NodeJS.Timeout | null>(null)
  const engine = ref(createBatteryPhysics(config.value, rawState.value))

  const state = computed<ExtendedBatteryState>(() => ({
    ...rawState.value,
    socPercentage: rawState.value.soc * 100,
    maxChargePower: config.value.capacity * config.value.cRateCharge,
    maxDischargePower: config.value.capacity * config.value.cRateDischarge
  }))

  const socColor = computed(() => {
    const soc = rawState.value.soc
    if (soc < 0.2) return 'text-red-400'
    if (soc < 0.4) return 'text-yellow-400'
    if (soc > 0.8) return 'text-green-400'
    return 'text-cyan-400'
  })

  const healthStatus = computed(() => {
    const h = rawState.value.health
    if (h > 0.9) return { color: 'text-green-400', text: 'Excellent' }
    if (h > 0.8) return { color: 'text-yellow-400', text: 'Good' }
    if (h > 0.7) return { color: 'text-orange-400', text: 'Fair' }
    return { color: 'text-red-400', text: 'Poor' }
  })

  const powerStatus = computed(() => {
    const p = rawState.value.power
    if (p > 0) return { icon: '⚡', color: 'text-green-400', text: 'Charging' }
    if (p < 0) return { icon: '🔋', color: 'text-orange-400', text: 'Discharging' }
    return { icon: '⏸️', color: 'text-slate-400', text: 'Idle' }
  })

  const canCharge = computed(() => rawState.value.soc < config.value.socMax)
  const canDischarge = computed(() => rawState.value.soc > config.value.socMin)

  const charge = (power: number) => {
    if (!canCharge.value) return
    const maxCharge = config.value.capacity * config.value.cRateCharge
    rawState.value = engine.value.simulate(Math.min(Math.max(0, power), maxCharge), 0.1)
  }

  const discharge = (power: number) => {
    if (!canDischarge.value) return
    const maxDischarge = config.value.capacity * config.value.cRateDischarge
    rawState.value = engine.value.simulate(Math.max(Math.min(0, -power), -maxDischarge), 0.1)
  }

  const idle = () => {
    rawState.value = engine.value.simulate(0, 0.1)
  }

  const startBalancedOperation = () => {
    console.log('Starting balanced operation')
  }

  const updateConfig = (newConfig: Partial<BatteryConfig>) => {
    config.value = { ...config.value, ...newConfig }
    engine.value.updateConfig(newConfig)
  }

  const reset = (newState?: Partial<BatteryState>) => {
    engine.value.reset(newState)
    rawState.value = engine.value.getState()
  }

  const startRealTimeUpdates = (intervalMs: number = 5000) => {
    if (updateInterval.value) clearInterval(updateInterval.value)
    updateInterval.value = setInterval(() => {
      rawState.value = engine.value.simulate(rawState.value.power, intervalMs / 3600000)
    }, intervalMs)
  }

  const stopRealTimeUpdates = () => {
    if (updateInterval.value) {
      clearInterval(updateInterval.value)
      updateInterval.value = null
    }
  }

  const clearError = () => { error.value = null }

  return {
    config, state, isLoading, error,
    socColor, healthStatus, powerStatus, canCharge, canDischarge,
    charge, discharge, idle, startBalancedOperation,
    updateConfig, reset, startRealTimeUpdates, stopRealTimeUpdates, clearError
  }
})
