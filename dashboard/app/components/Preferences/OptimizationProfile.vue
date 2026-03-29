<template>
  <div class="rounded-xl border border-slate-700 bg-slate-800/40 p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-white">Optimization Strategy</h2>
        <p class="text-sm text-slate-400">Define how the controller trades profit, battery health, and reliability.</p>
      </div>
      <button class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded text-sm" @click="loadConfig" :disabled="isLoading">
        {{ isLoading ? 'Loading...' : 'Reload' }}
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <button
        v-for="strategy in strategies"
        :key="strategy.id"
        class="rounded-xl border p-4 text-left transition"
        :class="selectedStrategy === strategy.id
          ? 'border-emerald-400 bg-emerald-500/10 shadow-[0_0_0_1px_rgba(52,211,153,0.25)]'
          : 'border-slate-700 bg-slate-900/50 hover:border-slate-500 hover:bg-slate-900'"
        @click="selectedStrategy = strategy.id"
      >
        <div class="flex items-start justify-between">
          <div>
            <p class="text-2xl">{{ strategy.emoji }}</p>
            <p class="mt-2 font-semibold text-white">{{ strategy.name }}</p>
            <p class="mt-1 text-xs text-slate-400">{{ strategy.description }}</p>
          </div>
          <span
            class="rounded-full px-2 py-1 text-[10px] uppercase tracking-wide"
            :class="selectedStrategy === strategy.id ? 'bg-emerald-400/20 text-emerald-200' : 'bg-slate-700 text-slate-300'"
          >
            {{ strategy.temperament }}
          </span>
        </div>

        <div class="mt-4 grid grid-cols-3 gap-2 text-[11px]">
          <div class="rounded bg-slate-800/70 p-2">
            <p class="text-slate-400">Profit</p>
            <p class="font-semibold text-white">{{ strategy.bias.profit }}%</p>
          </div>
          <div class="rounded bg-slate-800/70 p-2">
            <p class="text-slate-400">Health</p>
            <p class="font-semibold text-white">{{ strategy.bias.health }}%</p>
          </div>
          <div class="rounded bg-slate-800/70 p-2">
            <p class="text-slate-400">Reserve</p>
            <p class="font-semibold text-white">{{ strategy.bias.reliability }}%</p>
          </div>
        </div>
      </button>
    </div>

    <div v-if="selectedStrategy === 'custom'" class="rounded-lg border border-slate-700 bg-slate-900/60 p-4 space-y-4">
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

    <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-4 space-y-4">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="text-sm text-slate-300">Stage 2 operator inputs</p>
          <p class="text-xs text-slate-400">These values drive the effective market regime used by policy guards and financial analytics.</p>
        </div>
        <span class="rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide" :class="effectiveMarketRegimeBadgeClass">
          {{ effectiveMarketRegimeLabel }}
        </span>
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label class="block">
          <span class="text-sm text-slate-300">Connected site power (kW)</span>
          <input v-model.number="connectedPowerKw" type="number" min="1" max="10000" step="1" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2" />
          <p class="mt-1 text-xs text-slate-400">Auto mode treats values above 50 kW as Market Premium and lower values as Net Billing.</p>
        </label>

        <label class="block">
          <span class="text-sm text-slate-300">Market regime override</span>
          <select v-model="marketRegimeOverride" class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-3 py-2">
            <option value="auto">Auto by 50 kW threshold</option>
            <option value="net_billing">Force Net Billing scenario</option>
            <option value="market_premium">Force Market Premium scenario</option>
          </select>
          <p class="mt-1 text-xs text-slate-400">Use forced mode for diploma comparisons without changing the rest of the tenant model.</p>
        </label>
      </div>

      <p class="text-xs text-slate-300">{{ effectiveMarketRegimeSummary }}</p>
    </div>

    <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
      <p class="text-sm text-slate-300">Controller preview</p>
      <div class="mt-3 grid grid-cols-1 gap-3 text-sm md:grid-cols-4">
        <div>
          <p class="text-slate-400">SOC reserve floor</p>
          <p class="font-semibold text-white">{{ Math.round(batterySocMin * 100) }}%</p>
        </div>
        <div>
          <p class="text-slate-400">Peak dispatch capability</p>
          <p class="font-semibold text-white">{{ batteryCRateDischarge.toFixed(2) }}C</p>
        </div>
        <div>
          <p class="text-slate-400">Forecast horizon</p>
          <p class="font-semibold text-emerald-300">{{ forecastHorizonHours }}h</p>
        </div>
        <div>
          <p class="text-slate-400">Connected site power</p>
          <p class="font-semibold text-white">{{ connectedPowerKw.toFixed(0) }} kW</p>
        </div>
      </div>
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
type Stage2MarketRegimeChoice = 'auto' | 'net_billing' | 'market_premium'

const tenantContext = useTenantContext()

const strategies: Array<{
  id: StrategyId
  emoji: string
  name: string
  description: string
  temperament: string
  bias: {
    profit: number
    health: number
    reliability: number
  }
}> = [
  {
    id: 'max-earn',
    emoji: '🚀',
    name: 'Max Earn',
    description: 'Chase spreads aggressively and prioritize arbitrage margin.',
    temperament: 'Aggressive',
    bias: { profit: 70, health: 15, reliability: 15 },
  },
  {
    id: 'balanced',
    emoji: '⚖️',
    name: 'Balanced',
    description: 'Trade profit and degradation intelligently for steady output.',
    temperament: 'Adaptive',
    bias: { profit: 45, health: 30, reliability: 25 },
  },
  {
    id: 'max-health',
    emoji: '🛡️',
    name: 'Max Battery Health',
    description: 'Reduce cycle stress and preserve long-term battery value.',
    temperament: 'Conservative',
    bias: { profit: 20, health: 65, reliability: 15 },
  },
  {
    id: 'max-charge',
    emoji: '🔋',
    name: 'Max Reserve',
    description: 'Keep more energy for backup and operational reliability.',
    temperament: 'Resilient',
    bias: { profit: 20, health: 20, reliability: 60 },
  },
  {
    id: 'custom',
    emoji: '🎛️',
    name: 'Custom Weights',
    description: 'Manually tune profit, health, and reserve priorities.',
    temperament: 'User-defined',
    bias: { profit: 33, health: 33, reliability: 34 },
  },
]

const selectedStrategy = ref<StrategyId>('balanced')
const customWeights = ref({ profit: 33, health: 33, reliability: 34 })
const batterySocMin = ref(0.1)
const batteryCRateDischarge = ref(1)
const forecastHorizonHours = ref(24)
const connectedPowerKw = ref(10)
const marketRegimeOverride = ref<Stage2MarketRegimeChoice>('auto')

const isLoading = ref(false)
const isSaving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const customWeightSum = computed(() => customWeights.value.profit + customWeights.value.health + customWeights.value.reliability)
const messageClass = computed(() => (messageType.value === 'success' ? 'text-green-300' : 'text-red-300'))
const effectiveMarketRegime = computed(() => {
  if (marketRegimeOverride.value !== 'auto') {
    return marketRegimeOverride.value
  }

  return connectedPowerKw.value > 50 ? 'market_premium' : 'net_billing'
})
const effectiveMarketRegimeLabel = computed(() => {
  return effectiveMarketRegime.value === 'market_premium' ? 'MARKET PREMIUM' : 'NET BILLING'
})
const effectiveMarketRegimeBadgeClass = computed(() => {
  if (effectiveMarketRegime.value === 'market_premium') {
    return 'border-fuchsia-500/70 bg-fuchsia-500/15 text-fuchsia-200'
  }
  return 'border-sky-500/70 bg-sky-500/15 text-sky-200'
})
const effectiveMarketRegimeSummary = computed(() => {
  if (marketRegimeOverride.value === 'market_premium') {
    return 'Forced Market Premium keeps policy and analytics in the >50 kW comparative scenario.'
  }
  if (marketRegimeOverride.value === 'net_billing') {
    return 'Forced Net Billing keeps policy and analytics in the <=50 kW comparative scenario.'
  }
  return connectedPowerKw.value > 50
    ? 'Auto mode currently resolves to Market Premium because connected site power is above 50 kW.'
    : 'Auto mode currently resolves to Net Billing because connected site power is at or below 50 kW.'
})

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

const normalizeMarketRegimeOverride = (value: unknown): Stage2MarketRegimeChoice => {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'net_billing' || normalized === 'net-billing') return 'net_billing'
  if (normalized === 'market_premium' || normalized === 'market-premium') return 'market_premium'
  return 'auto'
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
      connectedPowerKw.value = Number(response.data.connected_power_kw ?? response.data.load_peak_kw ?? 10)
      marketRegimeOverride.value = normalizeMarketRegimeOverride(response.data.market_regime_override)

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
        connected_power_kw: connectedPowerKw.value,
        market_regime_override: marketRegimeOverride.value,
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
