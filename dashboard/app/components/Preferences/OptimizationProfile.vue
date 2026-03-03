<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Optimization Strategy</h2>
        <p class="text-sm text-slate-400">Canonical strategy control. The battery control tab no longer duplicates this setting.</p>
      </div>
      <button class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm" @click="loadConfig" :disabled="isLoading">
        {{ isLoading ? 'Loading...' : 'Reload' }}
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
      <button
        v-for="strategy in strategies"
        :key="strategy.id"
        class="p-4 rounded border text-left transition"
        :class="selectedStrategy === strategy.id ? 'border-energy-400 bg-energy-400 bg-opacity-10' : 'border-slate-700 hover:border-slate-500'"
        @click="selectedStrategy = strategy.id"
      >
        <p class="font-semibold text-white">{{ strategy.name }}</p>
        <p class="text-xs text-slate-400 mt-1">{{ strategy.description }}</p>
      </button>
    </div>

    <div v-if="selectedStrategy === 'custom'" class="rounded-lg border border-slate-700 bg-slate-900 bg-opacity-50 p-4 space-y-4">
      <p class="text-sm text-slate-300">Custom priority weights (must total 100%)</p>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <label class="block">
          <span class="text-sm text-slate-300">Profit %</span>
          <input v-model.number="customWeights.profit" type="number" min="0" max="100" step="1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
        </label>
        <label class="block">
          <span class="text-sm text-slate-300">Health %</span>
          <input v-model.number="customWeights.health" type="number" min="0" max="100" step="1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
        </label>
        <label class="block">
          <span class="text-sm text-slate-300">Reliability %</span>
          <input v-model.number="customWeights.reliability" type="number" min="0" max="100" step="1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
        </label>
      </div>
      <p class="text-xs" :class="customWeightSum === 100 ? 'text-green-300' : 'text-yellow-300'">Total: {{ customWeightSum }}%</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <label class="block">
        <span class="text-sm text-slate-300">Minimum SOC reserve (0..1)</span>
        <input v-model.number="batterySocMin" type="number" min="0.05" max="0.5" step="0.01" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>
      <label class="block">
        <span class="text-sm text-slate-300">Max discharge C-rate</span>
        <input v-model.number="batteryCRateDischarge" type="number" min="0.1" max="3" step="0.1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>
      <label class="block">
        <span class="text-sm text-slate-300">Forecast horizon (hours)</span>
        <input v-model.number="forecastHorizonHours" type="number" min="1" max="72" step="1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
      </label>
    </div>

    <div class="flex items-center gap-3">
      <button class="px-6 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded" @click="save" :disabled="isSaving">
        {{ isSaving ? 'Saving...' : 'Save Optimization Settings' }}
      </button>
      <p v-if="message" class="text-sm" :class="messageClass">{{ message }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useTenantContext } from '../../composables/useTenantContext'

type StrategyId = 'max-earn' | 'balanced' | 'max-health' | 'max-charge' | 'custom'

const tenantContext = useTenantContext()

const strategies: Array<{ id: StrategyId, name: string, description: string }> = [
  { id: 'max-earn', name: 'Max Earn', description: 'Prioritize arbitrage profit.' },
  { id: 'balanced', name: 'Balanced', description: 'Balance economics and battery care.' },
  { id: 'max-health', name: 'Max Battery Health', description: 'Reduce degradation and cycling stress.' },
  { id: 'max-charge', name: 'Max Charge', description: 'Keep reserve for reliability.' },
  { id: 'custom', name: 'Custom', description: 'Use custom weights.' },
]

const selectedStrategy = ref<StrategyId>('balanced')
const customWeights = ref({ profit: 33, health: 33, reliability: 34 })
const batterySocMin = ref(0.1)
const batteryCRateDischarge = ref(1)
const forecastHorizonHours = ref(24)

const isLoading = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const customWeightSum = computed(() => customWeights.value.profit + customWeights.value.health + customWeights.value.reliability)
const messageClass = computed(() => (messageType.value === 'success' ? 'text-green-300' : 'text-red-300'))

const showMessage = (text: string, type: 'success' | 'error') => {
  message.value = text
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 4000)
}

const fromApiStrategy = (value: string | undefined): StrategyId => {
  if (value === 'max_earn') return 'max-earn'
  if (value === 'max_battery_health') return 'max-health'
  if (value === 'max_charge') return 'max-charge'
  return 'balanced'
}

const toApiStrategy = (value: StrategyId): 'max_earn' | 'balanced' | 'max_battery_health' | 'max_charge' => {
  if (value === 'max-earn') return 'max_earn'
  if (value === 'max-health') return 'max_battery_health'
  if (value === 'max-charge') return 'max_charge'
  if (value === 'custom') return 'balanced'
  return 'balanced'
}

const loadConfig = async () => {
  isLoading.value = true
  try {
    await tenantContext.loadTenants()
    const tenantId = tenantContext.currentTenantId.value
    const response = await $fetch<any>('/api/config/current', {
      query: { tenantId },
      headers: { 'x-tenant-id': tenantId },
    })
    if (response?.success && response?.data) {
      selectedStrategy.value = fromApiStrategy(response.data.optimization_strategy)
      batterySocMin.value = Number(response.data.battery_soc_min ?? 0.1)
      batteryCRateDischarge.value = Number(response.data.battery_c_rate_discharge ?? 1)
      forecastHorizonHours.value = Number(response.data.ml_forecast_horizon_hours ?? 24)

      const weights = response.data.custom_optimization_weights
      if (weights && typeof weights === 'object') {
        customWeights.value = {
          profit: Number(weights.profit ?? 33),
          health: Number(weights.health ?? 33),
          reliability: Number(weights.reliability ?? 34),
        }
      }
    }
  } catch (error) {
    console.error('[OptimizationProfile] load failed', error)
    showMessage('Failed to load optimization settings', 'error')
  } finally {
    isLoading.value = false
  }
}

const save = async () => {
  if (selectedStrategy.value === 'custom' && customWeightSum.value !== 100) {
    showMessage('Custom weights must total 100%', 'error')
    return
  }

  isSaving.value = true
  try {
    await tenantContext.loadTenants()
    const tenantId = tenantContext.currentTenantId.value

    const response = await $fetch<any>('/api/config/save', {
      method: 'POST',
      query: { tenantId },
      headers: { 'x-tenant-id': tenantId },
      body: {
        tenantId,
        optimization_strategy: toApiStrategy(selectedStrategy.value),
        custom_optimization_weights: selectedStrategy.value === 'custom' ? customWeights.value : null,
        battery_soc_min: batterySocMin.value,
        battery_c_rate_discharge: batteryCRateDischarge.value,
        ml_forecast_horizon_hours: forecastHorizonHours.value,
      },
    })

    if (!response?.success) {
      throw new Error(response?.error || 'Save failed')
    }

    showMessage('Optimization settings saved', 'success')
  } catch (error) {
    console.error('[OptimizationProfile] save failed', error)
    showMessage('Failed to save optimization settings', 'error')
  } finally {
    isSaving.value = false
  }
}

onMounted(loadConfig)
</script>
