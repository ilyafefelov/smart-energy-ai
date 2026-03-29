<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <h2 class="text-xl font-bold text-white mb-6">Optimization Profile</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
      <div
        v-for="profile in profiles"
        :key="profile.id"
        @click="selectProfile(profile.id)"
        class="cursor-pointer border-2 rounded-lg p-4 transition"
        :class="selected === profile.id ? 'border-cyan-400 bg-slate-700' : 'border-slate-700 bg-slate-900 hover:border-slate-500'"
      >
        <div class="text-2xl mb-2">{{ profile.icon }}</div>
        <div class="font-semibold text-white">{{ profile.name }}</div>
        <div class="text-xs text-slate-400 mt-1">{{ profile.description }}</div>
      </div>
    </div>

    <h3 class="text-lg font-semibold text-white mb-4 mt-8">Current Electricity Price</h3>
    <p class="text-sm text-slate-400 mb-4">Live electricity price from OREE market data.</p>
    <div class="bg-slate-900 rounded-lg p-4">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-3xl font-bold text-energy-400">{{ currentPrice }} ₴/kWh</p>
          <p class="text-xs text-slate-400 mt-1">
            Avg today: {{ avgPrice }} ₴/kWh | 
            <span :class="priceTrend === 'up' ? 'text-red-400' : priceTrend === 'down' ? 'text-green-400' : 'text-slate-400'">
              {{ priceTrend === 'up' ? '↑ Rising' : priceTrend === 'down' ? '↓ Falling' : '→ Stable' }}
            </span>
          </p>
        </div>
        <div class="text-right">
          <p class="text-xs text-slate-400">Last updated</p>
          <p class="text-sm text-white">{{ lastUpdate }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'
import { usePricesStore } from '~/stores/pricesStore'

const settingsStore = useSettingsStore()
const pricesStore = usePricesStore()
const selected = ref('balanced')

const profiles = [
  { id: 'savings', icon: '💰', name: 'Max Savings', description: 'Prioritize arbitrage profit' },
  { id: 'balanced', icon: '⚖️', name: 'Balanced', description: 'Balance savings and health' },
  { id: 'longevity', icon: '🛡️', name: 'Longevity', description: 'Protect battery life' }
]

onMounted(() => {
  selected.value = settingsStore.optimizationSettings.strategy
  pricesStore.fetchPrices()
})

const selectProfile = (id: string) => {
  selected.value = id
  settingsStore.updateOptimization({ strategy: id as 'savings' | 'balanced' | 'longevity' })
}

const currentPrice = computed(() => {
  return pricesStore.currentPrice?.toFixed(2) ?? '—'
})

const avgPrice = computed(() => {
  return pricesStore.todayAvg?.toFixed(2) ?? '—'
})

const priceTrend = computed(() => {
  return pricesStore.priceStatus?.trend ?? 'stable'
})

const lastUpdate = computed(() => {
  if (!pricesStore.currentPriceTimestamp) return '—'
  return new Date(pricesStore.currentPriceTimestamp).toLocaleTimeString()
})
</script>
