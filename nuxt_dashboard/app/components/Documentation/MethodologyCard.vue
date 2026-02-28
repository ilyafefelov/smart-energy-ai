<template>
  <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
    <div class="flex items-start justify-between">
      <div>
        <h3 class="text-lg font-bold text-white">📚 Forecasting & Buy/Sell Zones</h3>
        <p class="text-sm text-slate-400 mt-1">Quick overview of how prices are forecasted, thresholds used for buy/sell decisions, and data freshness.</p>
      </div>
      <div class="text-right">
        <p class="text-xs text-slate-400">Last update</p>
        <p class="text-sm font-semibold text-energy-400">{{ lastUpdateText }}</p>
      </div>
    </div>

    <div class="mt-4 space-y-3">
      <button @click="showDetails = !showDetails" class="px-3 py-1 text-xs bg-slate-700 hover:bg-energy-400 hover:text-slate-900 rounded transition font-semibold">
        {{ showDetails ? 'Hide details' : 'View methodology' }}
      </button>

      <div v-if="showDetails" class="mt-4 text-sm text-slate-300 space-y-3">
        <div>
          <p class="font-semibold text-energy-400">Price Forecasting Methodology</p>
          <p class="mt-1">We use a lightweight ensemble model combining recent historical hourly prices, market signals (grid load & renewables when available), and short-term smoothing. The model produces a 24-hour hourly forecast and a confidence score per hour.</p>
          <p class="mt-1 text-xs text-slate-400">Confidence: A typical hour has 70–95% confidence. The UI shows per-hour confidence where available.</p>
        </div>

        <div>
          <p class="font-semibold text-energy-400">Buy / Sell Zone Explanation</p>
          <p class="mt-1">The dashboard highlights zones based on today&apos;s average price:</p>
          <ul class="list-disc ml-4 text-slate-300 mt-2 text-xs">
            <li><span class="font-semibold">Buy (Green):</span> Price &lt; 85% of today&apos;s average. Formula: price &lt; 0.85 × avg</li>
            <li><span class="font-semibold">Sell (Red):</span> Price &gt; 115% of today&apos;s average. Formula: price &gt; 1.15 × avg</li>
          </ul>
          <p class="mt-1 text-xs text-slate-400">Thresholds chosen from common arbitrage heuristics and tuned for a 2 UAH minimum spread requirement.</p>
        </div>

        <div>
          <p class="font-semibold text-energy-400">Data Freshness</p>
          <p class="mt-1">Data sources include the OREE price API and local battery telemetry. Forecasts are refreshed periodically; manual Refresh will request the server. The UI shows the last successful fetch timestamp.</p>
          <p class="mt-1 text-xs text-slate-400">Update frequency: default background refresh every 60s for prices, 5s for battery status, 30s for metrics.</p>
        </div>

        <div>
          <p class="font-semibold text-energy-400">Notes</p>
          <p class="mt-1 text-xs text-slate-400">If data appears unstable after refreshing multiple times, the server caches results for short windows to provide consistent user experience. For production, replace simulator endpoints with the official OREE data feed and add persistent caching at the API gateway.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { usePricesStore } from '~/stores/pricesStore'

const showDetails = ref(false)
const pricesStore = usePricesStore()

const lastUpdateText = computed(() => {
  const t = pricesStore.lastFetchTime
  if (!t) return 'Never'
  try {
    return (t as Date).toLocaleString()
  } catch {
    return String(t)
  }
})
</script>

<style scoped>
</style>
