<template>
  <div class="min-h-screen bg-slate-950 text-white p-8">
    <div class="max-w-7xl mx-auto space-y-8">
      <!-- Header -->
      <div class="flex justify-between items-start">
        <div>
          <h1 class="text-4xl font-bold text-energy-400 mb-2">⚡ Energy Dashboard</h1>
          <p class="text-slate-400">Real-time AI-powered battery optimization</p>
        </div>
        <div class="text-right">
          <p class="text-sm text-slate-400">{{ currentDate }}</p>
          <p class="text-energy-400 font-semibold">{{ liveStatus }}</p>
        </div>
      </div>

      <!-- Error handling -->
      <div v-if="metricsStore.error" class="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-4">
        <p class="text-red-300 font-semibold">⚠️ {{ metricsStore.error }}</p>
        <button @click="metricsStore.clearError" class="text-xs text-red-400 hover:text-red-300 mt-2">Dismiss</button>
      </div>

      <!-- Key Metrics Grid (4 cols) -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Daily Savings Card -->
        <MetricCard
          label="Daily Savings"
          :value="metricsStore.savingsToday.value"
          icon="💰"
          :color="metricsStore.savingsToday.color as any"
          :trend="metricsStore.savingsToday.trend as any"
          :trendValue="metricsStore.savingsToday.trendValue"
          :tooltipInfo="metricsStore.getTooltip('savingsToday')"
        />

        <!-- Current Price Card -->
        <MetricCard
          label="Current Price"
          :value="pricesStore.currentPriceFormatted"
          icon="📊"
          :color="pricesStore.priceStatus.color as any"
          :tooltipInfo="metricsStore.getTooltip('averagePrice')"
        />

        <!-- Battery SOC Card -->
        <MetricCard
          label="Battery SOC"
          :value="batteryStore.socPercentage"
          icon="🔋"
          color="yellow"
          :description="`${batteryStore.power.toFixed(2)} kW • ${batteryStore.temperature.toFixed(1)}°C`"
          :tooltipInfo="metricsStore.getTooltip('batteryHealth')"
        >
          <div class="mt-4">
            <div class="w-full bg-slate-700 rounded-full h-2">
              <div 
                class="h-full bg-gradient-to-r from-green-500 to-yellow-500 rounded-full transition-all"
                :style="{ width: batteryStore.soc + '%' }"
              ></div>
            </div>
            <p class="text-xs text-slate-400 mt-2">{{ batteryStore.capacity }} kWh capacity</p>
          </div>
        </MetricCard>

        <!-- Forecast Accuracy Card -->
        <MetricCard
          label="Forecast Accuracy"
          :value="metricsStore.accuracy.value"
          icon="🎯"
          color="blue"
          :tooltipInfo="metricsStore.getTooltip('forecastAccuracy')"
        />
      </div>

      <!-- Secondary Metrics Grid (3 cols) -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="Peak Price Today"
          :value="pricesStore.peakPrice.toFixed(2) + ' ₴/kWh'"
          icon="📈"
          color="red"
          :tooltipInfo="metricsStore.getTooltip('peakPrice')"
        />

        <MetricCard
          label="Off-Peak Price"
          :value="pricesStore.offPeakPrice.toFixed(2) + ' ₴/kWh'"
          icon="📉"
          color="green"
          :tooltipInfo="metricsStore.getTooltip('offPeakPrice')"
        />

        <MetricCard
          label="Next Cycle In"
          :value="metricsStore.metrics.nextCycleIn.value"
          icon="⏱️"
          color="purple"
          :tooltipInfo="metricsStore.getTooltip('nextCycleIn')"
        />
      </div>

      <!-- Price Forecast Chart (Interactive) -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h2 class="text-xl font-bold text-white mb-1">24h Price Forecast</h2>
            <p class="text-sm text-slate-400">Hover for details • Click to lock price</p>
          </div>
          <div class="flex gap-2">
            <button class="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded transition">🔍+ Zoom</button>
            <button class="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded transition">◀ Pan</button>
          </div>
        </div>

        <!-- Simple SVG Chart -->
        <div v-if="pricesStore.forecast.length > 0" class="relative">
          <svg viewBox="0 0 1200 400" class="w-full h-64 mb-4">
            <!-- Grid lines -->
            <line x1="0" y1="50" x2="1200" y2="50" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
            <line x1="0" y1="150" x2="1200" y2="150" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
            <line x1="0" y1="250" x2="1200" y2="250" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
            <line x1="0" y1="350" x2="1200" y2="350" stroke="#475569" stroke-width="1" stroke-dasharray="4" />

            <!-- Price line chart -->
            <polyline
              :points="chartPoints"
              fill="none"
              stroke="#22d3ee"
              stroke-width="3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />

            <!-- Fill under line -->
            <polygon
              :points="`0,350 ${chartPoints} 1200,350`"
              fill="url(#priceGradient)"
              opacity="0.3"
            />

            <!-- Gradient definition -->
            <defs>
              <linearGradient id="priceGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color: #22d3ee; stop-opacity: 0.5" />
                <stop offset="100%" style="stop-color: #22d3ee; stop-opacity: 0" />
              </linearGradient>
            </defs>

            <!-- Axis labels -->
            <text x="10" y="25" font-size="12" fill="#94a3b8">{{ pricesStore.peakPrice.toFixed(1) }}₴</text>
            <text x="10" y="375" font-size="12" fill="#94a3b8">{{ pricesStore.offPeakPrice.toFixed(1) }}₴</text>
          </svg>

          <!-- Legend -->
          <div class="flex justify-center gap-6 text-sm">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-cyan-400 rounded-full"></div>
              <span class="text-slate-300">Price forecast</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-green-500 rounded-full"></div>
              <span class="text-slate-300">Good buying time</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-red-500 rounded-full"></div>
              <span class="text-slate-300">Good selling time</span>
            </div>
          </div>
        </div>

        <!-- Loading state -->
        <div v-else class="flex items-center justify-center h-64">
          <p class="text-slate-400">Loading forecast...</p>
        </div>
      </div>

      <!-- Arbitrage Opportunities -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">💡 Arbitrage Opportunities</h2>
        
        <div v-if="pricesStore.arbitrageOpportunity" class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-1">Price Spread</p>
            <p class="text-2xl font-bold text-energy-400">{{ pricesStore.arbitrageOpportunity.spread.toFixed(2) }} ₴</p>
            <p class="text-xs text-slate-400 mt-1">{{ pricesStore.arbitrageOpportunity.spreadPercent }}% variance</p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-1">Opportunity Status</p>
            <p v-if="pricesStore.arbitrageOpportunity.opportunity" class="text-xl font-bold text-green-400">✓ Profitable</p>
            <p v-else class="text-xl font-bold text-yellow-400">⚠ Limited</p>
            <p class="text-xs text-slate-400 mt-1">Minimum 2₴ spread required</p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-1">Recommended Action</p>
            <p v-if="pricesStore.arbitrageOpportunity.opportunity" class="text-lg font-bold text-energy-400">Buy Low → Sell High</p>
            <p v-else class="text-lg font-bold text-slate-400">Hold</p>
            <p class="text-xs text-slate-400 mt-1">Based on forecast</p>
          </div>
        </div>
      </div>

      <!-- Battery Trajectory Simulation -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">🔋 Battery Trajectory (Next 24h)</h2>
        <p class="text-sm text-slate-400 mb-4">Simulated battery SOC based on optimal trading strategy</p>

        <svg viewBox="0 0 1200 300" class="w-full h-48 mb-4">
          <!-- Grid -->
          <line x1="0" y1="50" x2="1200" y2="50" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
          <line x1="0" y1="150" x2="1200" y2="150" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
          <line x1="0" y1="250" x2="1200" y2="250" stroke="#475569" stroke-width="1" stroke-dasharray="4" />

          <!-- Simulated trajectory -->
          <polyline
            points="0,150 100,120 200,140 300,100 400,130 500,110 600,140 700,120 800,150 900,130 1000,110 1100,140 1200,100"
            fill="none"
            stroke="#fbbf24"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          />

          <!-- Min/Max bounds -->
          <line x1="0" y1="30" x2="1200" y2="30" stroke="#ef4444" stroke-width="2" stroke-dasharray="8" opacity="0.5" />
          <line x1="0" y1="270" x2="1200" y2="270" stroke="#22c55e" stroke-width="2" stroke-dasharray="8" opacity="0.5" />

          <!-- Labels -->
          <text x="10" y="25" font-size="12" fill="#ef4444">Max (100%)</text>
          <text x="10" y="290" font-size="12" fill="#22c55e">Min (15%)</text>
        </svg>

        <p class="text-xs text-slate-400">Hover to see predicted SOC at specific hour • Drag to adjust forecast</p>
      </div>

      <!-- Active Retraining Section -->
      <div v-if="retrainingStore.isRunning" class="bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded-lg p-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="animate-spin text-2xl">⚙️</div>
          <div>
            <h2 class="text-xl font-bold text-yellow-300">Model Retraining in Progress</h2>
            <p class="text-sm text-yellow-200">{{ retrainingStore.job.message }}</p>
          </div>
        </div>

        <div class="w-full bg-slate-800 rounded-full h-3 mb-2">
          <div 
            class="h-full bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full transition-all"
            :style="{ width: retrainingStore.progressPercent + '%' }"
          ></div>
        </div>

        <div class="flex justify-between text-sm text-yellow-300">
          <span>{{ retrainingStore.progressPercentFormatted }}</span>
          <span>{{ retrainingStore.timeRemaining }}</span>
        </div>

        <button 
          @click="cancelRetraining"
          class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm font-semibold transition"
        >
          ✕ Cancel Retraining
        </button>
      </div>

      <!-- Retraining Complete Alert -->
      <div v-if="retrainingStore.isCompleted" class="bg-green-900 bg-opacity-30 border border-green-700 rounded-lg p-6">
        <h2 class="text-xl font-bold text-green-300 mb-2">✅ Model Retraining Complete!</h2>
        <p class="text-green-200 mb-4">Your personal PPO model has been optimized and is now active.</p>

        <div v-if="retrainingStore.job.metricsImprovement" class="grid grid-cols-3 gap-4 mb-4">
          <div class="bg-slate-800 rounded-lg p-3">
            <p class="text-xs text-slate-400">Previous Accuracy</p>
            <p class="text-lg font-bold text-green-400">{{ retrainingStore.job.metricsImprovement.previousAccuracy }}%</p>
          </div>
          <div class="bg-slate-800 rounded-lg p-3">
            <p class="text-xs text-slate-400">New Accuracy</p>
            <p class="text-lg font-bold text-green-300">{{ retrainingStore.job.metricsImprovement.newAccuracy }}%</p>
          </div>
          <div class="bg-slate-800 rounded-lg p-3">
            <p class="text-xs text-slate-400">Improvement</p>
            <p class="text-lg font-bold text-cyan-400">+{{ retrainingStore.job.metricsImprovement.improvementPercent }}%</p>
          </div>
        </div>

        <button 
          @click="dismissRetrainingComplete"
          class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-semibold transition"
        >
          Dismiss
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMetricsStore } from '~/stores/metricsStore'
import { useBatteryStore } from '~/stores/batteryStore'
import { usePricesStore } from '~/stores/pricesStore'
import { useRetrainingStore } from '~/stores/retrainingStore'
import { useSettingsStore } from '~/stores/settingsStore'

const metricsStore = useMetricsStore()
const batteryStore = useBatteryStore()
const pricesStore = usePricesStore()
const retrainingStore = useRetrainingStore()
const settingsStore = useSettingsStore()

const showRetrainingComplete = ref(false)

const currentDate = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
})

const liveStatus = computed(() => {
  return new Date().getHours() >= 8 && new Date().getHours() < 20 ? 'TRADING HOURS' : 'OFF-PEAK'
})

// Chart points for price forecast
const chartPoints = computed(() => {
  if (pricesStore.forecast.length === 0) return ''

  const minPrice = Math.min(...pricesStore.forecast.map(f => f.price))
  const maxPrice = Math.max(...pricesStore.forecast.map(f => f.price))
  const range = maxPrice - minPrice || 1

  return pricesStore.forecast.map((f, i) => {
    const x = (i / pricesStore.forecast.length) * 1200
    const y = 350 - ((f.price - minPrice) / range) * 300
    return `${x},${y}`
  }).join(' ')
})

const cancelRetraining = async () => {
  await retrainingStore.cancelRetraining()
}

const dismissRetrainingComplete = () => {
  showRetrainingComplete.value = false
}

// Initialize data on mount
onMounted(async () => {
  // Load settings FIRST so battery capacity is available
  await settingsStore.loadSettings()
  
  // Then fetch all data in parallel
  await Promise.all([
    metricsStore.fetchMetrics(),
    batteryStore.fetchBatteryStatus(),
    pricesStore.fetchPrices()
  ])

  // Start real-time updates
  batteryStore.startRealTimeUpdates(5000)
  pricesStore.startRealTimeUpdates(60000)
  metricsStore.startRealTimeUpdates(30000)
})

// Cleanup on unmount
onUnmounted(() => {
  batteryStore.stopRealTimeUpdates()
  pricesStore.stopRealTimeUpdates()
  metricsStore.stopRealTimeUpdates()
})
</script>

<style scoped>
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
