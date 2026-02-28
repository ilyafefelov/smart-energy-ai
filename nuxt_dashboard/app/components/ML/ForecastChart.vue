<template>
  <div class="bg-slate-800 border border-slate-700 rounded-lg p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-white">📊 24-Hour Forecast</h3>
      <span class="text-xs text-slate-400">Next 24 hours</span>
    </div>

    <!-- Simple forecast display -->
    <div class="space-y-2">
      <div class="grid grid-cols-4 gap-2 text-xs text-slate-400 border-b border-slate-700 pb-2">
        <span>Time</span>
        <span>Action</span>
        <span>Price</span>
        <span>Status</span>
      </div>
      
      <div class="space-y-1 max-h-40 overflow-y-auto">
        <div v-for="hour in sampleForecast" :key="hour.time" class="grid grid-cols-4 gap-2 text-sm py-1">
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
import { ref, computed } from 'vue'
import { usePricesStore } from '~/stores/pricesStore'

const pricesStore = usePricesStore()

const sampleForecast = computed(() => {
  if (!pricesStore.forecast || pricesStore.forecast.length === 0) {
    return [
      { time: 0, action: 'HOLD', price: 0.82, status: 'Off-peak' },
      { time: 1, action: 'HOLD', price: 0.82, status: 'Off-peak' },
      { time: 2, action: 'HOLD', price: 0.82, status: 'Off-peak' },
      { time: 6, action: 'HOLD', price: 0.85, status: 'Peak' },
      { time: 7, action: 'HOLD', price: 0.85, status: 'Peak' },
      { time: 8, action: 'HOLD', price: 0.85, status: 'Peak' },
      { time: 12, action: 'HOLD', price: 0.85, status: 'Peak' },
      { time: 18, action: 'HOLD', price: 0.85, status: 'Peak' },
      { time: 23, action: 'HOLD', price: 0.82, status: 'Off-peak' },
    ]
  }
  // Transform pricesStore.forecast to the expected format
  return pricesStore.forecast.map((f, idx) => ({
    time: (new Date().getHours() + idx) % 24,
    action: f.price < pricesStore.todayAvg * 0.85 ? 'BUY' : f.price > pricesStore.todayAvg * 1.15 ? 'SELL' : 'HOLD',
    price: f.price,
    status: f.price < pricesStore.todayAvg * 0.85 ? 'Good buy' : f.price > pricesStore.todayAvg * 1.15 ? 'Good sell' : 'Normal'
  }))
})

const buyHours = computed(() => sampleForecast.value.filter(h => h.action === 'BUY').length)
const sellHours = computed(() => sampleForecast.value.filter(h => h.action === 'SELL').length)
const holdHours = computed(() => sampleForecast.value.filter(h => h.action === 'HOLD').length)
</script>