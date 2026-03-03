<template>
  <div class="bg-slate-800 border border-slate-700 rounded-lg p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-white">📊 24-Hour Forecast</h3>
      <span class="text-xs text-slate-400">Live next 24 hours</span>
    </div>

    <div v-if="forecastRows.length > 0" class="space-y-2">
      <div class="grid grid-cols-4 gap-2 text-xs text-slate-400 border-b border-slate-700 pb-2">
        <span>Time</span>
        <span>Action</span>
        <span>Price</span>
        <span>Status</span>
      </div>
      
      <div class="space-y-1 max-h-40 overflow-y-auto">
        <div v-for="hour in forecastRows" :key="hour.key" class="grid grid-cols-4 gap-2 text-sm py-1">
          <span class="text-slate-300">{{ hour.time }}:00</span>
          <span 
            class="text-xs px-2 py-1 rounded"
            :class="{
              'bg-green-900 text-green-300': hour.action === 'BUY',
              'bg-blue-900 text-blue-300': hour.action === 'SELL',
              'bg-gray-900 text-gray-300': hour.action === 'HOLD'
            }"
          >
            {{ hour.action }}
          </span>
          <span class="text-energy-400">₴{{ hour.price.toFixed(2) }}</span>
          <span class="text-slate-400">{{ hour.status }}</span>
        </div>
      </div>
    </div>

    <div v-else class="py-8 text-center text-sm text-slate-400">
      Waiting for live price forecast...
    </div>

    <!-- Summary -->
    <div class="mt-4 pt-4 border-t border-slate-700">
      <div class="grid grid-cols-3 gap-4 text-center">
        <div>
          <p class="text-xs text-slate-400">BUY Hours</p>
          <p class="font-semibold text-green-400">{{ buyHours }}</p>
        </div>
        <div>
          <p class="text-xs text-slate-400">SELL Hours</p>
          <p class="font-semibold text-blue-400">{{ sellHours }}</p>
        </div>
        <div>
          <p class="text-xs text-slate-400">HOLD Hours</p>
          <p class="font-semibold text-gray-400">{{ holdHours }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePricesStore } from '~/stores/pricesStore'

interface ForecastRow {
  key: string
  time: number
  action: 'BUY' | 'SELL' | 'HOLD'
  price: number
  status: 'Peak' | 'Off-Peak' | 'Normal'
}

const pricesStore = usePricesStore()

const forecastRows = computed<ForecastRow[]>(() => {
  const source = pricesStore.forecast.slice(0, 24)
  const avg = pricesStore.todayAvg
  const nowHour = new Date().getHours()

  if (source.length === 0) {
    return []
  }

  return source.map((point, idx) => {
    const price = Number(point.price || 0)
    let action: ForecastRow['action'] = 'HOLD'
    let status: ForecastRow['status'] = 'Normal'

    if (avg > 0 && price < avg * 0.85) {
      action = 'BUY'
      status = 'Off-Peak'
    } else if (avg > 0 && price > avg * 1.15) {
      action = 'SELL'
      status = 'Peak'
    }

    return {
      key: `${idx}-${point.timestamp instanceof Date ? point.timestamp.getTime() : nowHour + idx}`,
      time: (nowHour + idx) % 24,
      action,
      price,
      status,
    }
  })
})

const buyHours = computed(() => forecastRows.value.filter((h) => h.action === 'BUY').length)
const sellHours = computed(() => forecastRows.value.filter((h) => h.action === 'SELL').length)
const holdHours = computed(() => forecastRows.value.filter((h) => h.action === 'HOLD').length)
</script>
