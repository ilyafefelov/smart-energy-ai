<template>
  <div class="min-h-screen bg-slate-950 text-white p-8">
    <div class="max-w-7xl mx-auto space-y-8">
      <!-- Header -->
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <NuxtLink to="/" class="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block">
            ← Back to Dashboard
          </NuxtLink>
          <h1 class="text-4xl font-bold text-energy-400 mt-2">📈 Analytics</h1>
          <p class="text-slate-400 mt-2">Detailed energy market analysis and performance metrics</p>
        </div>

        <select
          v-model="selectedTenantId"
          class="px-3 py-2 rounded-md border border-slate-700 bg-slate-900 text-sm"
        >
          <option v-for="tenant in tenantOptions" :key="tenant.id" :value="tenant.id">
            {{ tenant.name || tenant.id }}
          </option>
        </select>
      </div>

      <!-- Error Handling -->
      <div v-if="pricesStore.error" class="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-4">
        <p class="text-red-300 font-semibold">⚠️ {{ pricesStore.error }}</p>
        <button @click="pricesStore.clearError" class="text-xs text-red-400 hover:text-red-300 mt-2">Dismiss</button>
      </div>

      <!-- Loading State -->
      <div v-if="pricesStore.isLoading" class="bg-blue-900 bg-opacity-30 border border-blue-700 rounded-lg p-4">
        <p class="text-blue-300 font-semibold">Loading analytics data...</p>
      </div>

      <!-- Price Analysis Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Today's Min Price"
          :value="pricesStore.todayMin.toFixed(2) + ' ₴/kWh'"
          icon="📉"
          color="green"
          :tooltipInfo="metricsStore.getTooltip('offPeakPrice')"
        />

        <MetricCard
          label="Today's Max Price"
          :value="pricesStore.todayMax.toFixed(2) + ' ₴/kWh'"
          icon="📈"
          color="red"
          :tooltipInfo="metricsStore.getTooltip('peakPrice')"
        />

        <MetricCard
          label="Today's Avg Price"
          :value="pricesStore.todayAvg.toFixed(2) + ' ₴/kWh'"
          icon="📊"
          color="blue"
          :tooltipInfo="metricsStore.getTooltip('averagePrice')"
        />

        <MetricCard
          label="Weighted Price"
          :value="pricesStore.todayWeighted.toFixed(2) + ' ₴/kWh'"
          icon="⚖️"
          color="purple"
          description="Confidence-weighted forecast"
        />
      </div>

      <!-- Volatility & Market Conditions -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Price Volatility Card -->
        <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
          <h2 class="text-lg font-bold text-white mb-4">💹 Price Volatility</h2>
          
          <div class="space-y-4">
            <div>
              <p class="text-sm text-slate-400 mb-2">Daily Range (₴)</p>
              <p class="text-2xl font-bold text-energy-400">{{ (pricesStore.todayMax - pricesStore.todayMin).toFixed(2) }}</p>
              <p class="text-xs text-slate-400 mt-1">Difference between peak and off-peak</p>
            </div>

            <div class="pt-4 border-t border-slate-700">
              <p class="text-sm text-slate-400 mb-2">Volatility Index</p>
              <div class="flex items-center gap-2">
                <div class="flex-1 bg-slate-700 rounded-full h-2">
                  <div class="h-full bg-gradient-to-r from-green-500 to-red-500 rounded-full" style="width: 65%"></div>
                </div>
                <span class="text-sm font-semibold text-slate-300">Moderate</span>
              </div>
              <p class="text-xs text-slate-400 mt-1">Based on hourly price variations</p>
            </div>
          </div>
        </div>

        <!-- Peak/Off-Peak Analysis -->
        <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
          <h2 class="text-lg font-bold text-white mb-4">⏰ Peak/Off-Peak Analysis</h2>

          <div class="space-y-4">
            <div>
              <p class="text-sm text-slate-400 mb-2">Peak Hours (8-20)</p>
              <p class="text-2xl font-bold text-red-400">{{ pricesStore.peakPrice.toFixed(2) }} ₴/kWh</p>
              <p class="text-xs text-slate-400 mt-1">Average price during trading hours</p>
            </div>

            <div class="pt-4 border-t border-slate-700">
              <p class="text-sm text-slate-400 mb-2">Off-Peak Hours (20-8)</p>
              <p class="text-2xl font-bold text-green-400">{{ pricesStore.offPeakPrice.toFixed(2) }} ₴/kWh</p>
              <p class="text-xs text-slate-400 mt-1">Average price outside trading hours</p>
            </div>

            <div class="pt-4 border-t border-slate-700">
              <p class="text-sm text-slate-400 mb-2">Price Ratio</p>
              <p class="text-lg font-bold text-energy-400">
                {{ (pricesStore.peakPrice / pricesStore.offPeakPrice).toFixed(2) }}x
              </p>
              <p class="text-xs text-slate-400 mt-1">Peak vs Off-Peak multiplier</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Arbitrage Opportunities Details -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-lg font-bold text-white mb-4">💡 Arbitrage Opportunities</h2>

        <div v-if="pricesStore.arbitrageOpportunity" class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Price Spread Card -->
          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-3">Daily Price Spread</p>
            <div class="flex items-end gap-2">
              <p class="text-3xl font-bold text-energy-400">{{ pricesStore.arbitrageOpportunity.spread.toFixed(2) }}</p>
              <p class="text-sm text-slate-400 mb-1">₴/kWh</p>
            </div>
            <p class="text-xs text-slate-400 mt-2">{{ pricesStore.arbitrageOpportunity.spreadPercent }}% variance</p>
          </div>

          <!-- Opportunity Score Card -->
          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-3">Opportunity Status</p>
            <div v-if="pricesStore.arbitrageOpportunity.opportunity" class="space-y-2">
              <p class="text-2xl font-bold text-green-400">✓ PROFITABLE</p>
              <p class="text-xs text-green-300">Minimum spread threshold met</p>
            </div>
            <div v-else class="space-y-2">
              <p class="text-2xl font-bold text-yellow-400">⚠ LIMITED</p>
              <p class="text-xs text-yellow-300">Spread below 2₴ threshold</p>
            </div>
          </div>

          <!-- Estimated Gain Card -->
          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-3">Est. Daily Gain (150kWh)</p>
            <p class="text-3xl font-bold text-cyan-400">
              {{ (pricesStore.arbitrageOpportunity.spread * 150).toFixed(0) }} ₴
            </p>
            <p class="text-xs text-slate-400 mt-2">Potential gain with full battery capacity</p>
          </div>
        </div>

        <!-- Forecast confidence -->
        <div class="mt-6 pt-6 border-t border-slate-700">
          <p class="text-sm text-slate-400 mb-3">Forecast Confidence</p>
          <div class="space-y-2">
            <div v-for="(forecast, idx) in pricesStore.forecast.slice(0, 6)" :key="idx" class="flex items-center justify-between">
              <span class="text-xs text-slate-400">Hour {{ forecast.hour }}:00</span>
              <div class="flex items-center gap-2 flex-1 ml-4">
                <div class="flex-1 bg-slate-700 rounded-full h-1">
                  <div class="h-full bg-energy-400 rounded-full" :style="{ width: (forecast.confidence * 100) + '%' }"></div>
                </div>
                <span class="text-xs text-slate-300 w-12">{{ (forecast.confidence * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Historical Performance Trends -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-lg font-bold text-white mb-4">📊 Historical Performance</h2>
        <p class="text-xs text-slate-400 mb-4">Source: {{ canonicalHistorySourceLabel }}</p>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-2">Daily Savings (Last 7 days)</p>
            <p class="text-2xl font-bold text-green-400">{{ Math.round(historyTotalSavings).toLocaleString() }} ₴</p>
            <p class="text-xs mt-2" :class="historyGrowthPercent >= 0 ? 'text-green-300' : 'text-red-300'">
              {{ historyGrowthPercent >= 0 ? '↑' : '↓' }} {{ Math.abs(historyGrowthPercent).toFixed(1) }}% vs first day in window
            </p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-2">Avg Daily Saving</p>
            <p class="text-2xl font-bold text-green-400">{{ Math.round(historyAverageSavings).toLocaleString() }} ₴</p>
            <p class="text-xs text-slate-400 mt-2">Consistent performance</p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-2">Success Rate</p>
            <p class="text-2xl font-bold text-energy-400">{{ historySuccessRate.toFixed(1) }}%</p>
            <p class="text-xs text-slate-400 mt-2">Days with positive realized net / total days</p>
          </div>
        </div>
      </div>

      <!-- Price Trend Chart -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-lg font-bold text-white mb-4">📉 Price Trend (24h Forecast)</h2>

        <svg v-if="pricesStore.forecast.length > 0" viewBox="0 0 1200 300" class="w-full h-64 mb-4">
          <!-- Grid -->
          <line x1="0" y1="50" x2="1200" y2="50" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
          <line x1="0" y1="150" x2="1200" y2="150" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
          <line x1="0" y1="250" x2="1200" y2="250" stroke="#475569" stroke-width="1" stroke-dasharray="4" />

          <!-- Line chart -->
          <polyline
            :points="chartPoints"
            fill="none"
            stroke="#22d3ee"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          />

          <!-- Fill -->
          <polygon
            :points="`0,300 ${chartPoints} 1200,300`"
            fill="url(#trendGradient)"
            opacity="0.2"
          />

          <defs>
            <linearGradient id="trendGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color: #22d3ee; stop-opacity: 0.5" />
              <stop offset="100%" style="stop-color: #22d3ee; stop-opacity: 0" />
            </linearGradient>
          </defs>

          <!-- Axis labels -->
          <text x="10" y="25" font-size="12" fill="#94a3b8">{{ pricesStore.peakPrice.toFixed(1) }}₴</text>
          <text x="10" y="290" font-size="12" fill="#94a3b8">{{ pricesStore.offPeakPrice.toFixed(1) }}₴</text>
        </svg>

        <p class="text-xs text-slate-400 mt-4">Data updated: {{ lastUpdateTime }}</p>
      </div>

      <!-- System Status -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-lg font-bold text-white mb-4">🎯 System Status</h2>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-300">Data Quality</span>
            <span class="px-3 py-1 bg-green-900 text-green-300 rounded-full text-xs font-semibold">Excellent</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-300">Forecast Update</span>
            <span class="px-3 py-1 bg-blue-900 text-blue-300 rounded-full text-xs font-semibold">Live</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-300">Market Status</span>
            <span class="px-3 py-1 bg-energy-400 bg-opacity-30 text-energy-400 rounded-full text-xs font-semibold">Active</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-300">Control Mode</span>
            <span class="px-3 py-1 rounded-full text-xs font-semibold"
              :class="controlStatusBadgeClass"
            >
              {{ controlModeLabel }}
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-300">Active Command</span>
            <span class="px-3 py-1 bg-blue-900 text-blue-300 rounded-full text-xs font-semibold">{{ activeCommandLabel }}</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-300">Economics Source</span>
            <span class="px-3 py-1 bg-purple-900 text-purple-300 rounded-full text-xs font-semibold">{{ canonicalHistorySourceLabel }}</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-300">Auto Transitions (Today)</span>
            <span class="px-3 py-1 bg-emerald-900 text-emerald-300 rounded-full text-xs font-semibold">{{ latestAutoTransitions }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { usePricesStore } from '~/stores/pricesStore'
import { useMetricsStore } from '~/stores/metricsStore'
import { useTenantContext } from '~/composables/useTenantContext'

const pricesStore = usePricesStore()
const metricsStore = useMetricsStore()
const tenantContext = useTenantContext()
const analyticsHistoryRows = ref<any[]>([])
const controlStatus = ref<any>(null)
const canonicalHistorySource = ref<string>('unknown')

const tenantOptions = computed(() => tenantContext.tenants.value)
const selectedTenantId = computed({
  get: () => tenantContext.currentTenantId.value,
  set: (tenantId: string) => tenantContext.setTenant(tenantId),
})

const buildTenantRequest = () => {
  const tenantId = tenantContext.currentTenantId.value
  return {
    query: {
      tenantId,
    },
    headers: {
      'x-tenant-id': tenantId,
    },
  }
}

const fetchCanonicalAnalyticsData = async () => {
  const tenantRequest = buildTenantRequest()
  const [historyResponse, controlResponse] = await Promise.all([
    $fetch<any>('/api/history', {
      ...tenantRequest,
      query: {
        ...tenantRequest.query,
        days: 7,
        limit: 7,
      },
    }).catch(() => null),
    $fetch<any>('/api/control/status', tenantRequest).catch(() => null),
  ])

  analyticsHistoryRows.value = Array.isArray(historyResponse?.data) ? historyResponse.data : []
  canonicalHistorySource.value = String(historyResponse?.source?.economics_source || 'unknown')
  controlStatus.value = controlResponse || null
}

const historyNetValues = computed(() => {
  return analyticsHistoryRows.value.map((row) => {
    const realizedNet = Number(row?.realized_net_uah || 0)
    const fallbackSavings = Number(row?.savings || 0)
    return Math.abs(realizedNet) > 0 ? realizedNet : fallbackSavings
  })
})

const historyTotalSavings = computed(() => {
  return historyNetValues.value.reduce((sum, value) => sum + value, 0)
})

const historyAverageSavings = computed(() => {
  if (historyNetValues.value.length === 0) {
    return 0
  }
  return historyTotalSavings.value / historyNetValues.value.length
})

const historySuccessRate = computed(() => {
  if (historyNetValues.value.length === 0) {
    return 0
  }
  const positiveDays = historyNetValues.value.filter((value) => value > 0).length
  return (positiveDays / historyNetValues.value.length) * 100
})

const historyGrowthPercent = computed(() => {
  if (historyNetValues.value.length < 2) {
    return 0
  }

  const first = Number(historyNetValues.value[0] || 0)
  const last = Number(historyNetValues.value[historyNetValues.value.length - 1] || 0)
  if (Math.abs(first) < 0.001) {
    return last > 0 ? 100 : 0
  }
  return ((last - first) / Math.abs(first)) * 100
})

const latestHistoryRow = computed(() => {
  return analyticsHistoryRows.value.length > 0
    ? analyticsHistoryRows.value[analyticsHistoryRows.value.length - 1]
    : null
})

const latestAutoTransitions = computed(() => Number(latestHistoryRow.value?.auto_transitions || 0))

const canonicalHistorySourceLabel = computed(() => {
  if (!canonicalHistorySource.value || canonicalHistorySource.value === 'unknown') {
    return 'fallback'
  }
  return canonicalHistorySource.value
})

const controlModeLabel = computed(() => String(controlStatus.value?.mode || 'unknown').toUpperCase())
const activeCommandLabel = computed(() => String(controlStatus.value?.active_command || 'idle').toUpperCase())
const controlStatusBadgeClass = computed(() => {
  const mode = String(controlStatus.value?.mode || '').toLowerCase()
  if (mode === 'automatic') return 'bg-green-900 text-green-300'
  if (mode === 'manual') return 'bg-red-900 text-red-300'
  return 'bg-slate-700 text-slate-300'
})

const lastUpdateTime = computed(() => {
  if (!pricesStore.lastFetchTime) return 'Never'
  return pricesStore.lastFetchTime.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  })
})

// Chart points calculation
const chartPoints = computed(() => {
  if (pricesStore.forecast.length === 0) return ''

  const minPrice = Math.min(...pricesStore.forecast.map(f => f.price))
  const maxPrice = Math.max(...pricesStore.forecast.map(f => f.price))
  const range = maxPrice - minPrice || 1

  return pricesStore.forecast.map((f, i) => {
    const x = (i / pricesStore.forecast.length) * 1200
    const y = 300 - ((f.price - minPrice) / range) * 250
    return `${x},${y}`
  }).join(' ')
})

onMounted(async () => {
  await tenantContext.loadTenants()

  await Promise.all([
    pricesStore.fetchPrices(),
    metricsStore.fetchMetrics(),
    fetchCanonicalAnalyticsData(),
  ])

  // Start real-time updates
  pricesStore.startRealTimeUpdates(60000)
  metricsStore.startRealTimeUpdates(30000)
})

onUnmounted(() => {
  pricesStore.stopRealTimeUpdates()
  metricsStore.stopRealTimeUpdates()
})

watch(
  () => tenantContext.currentTenantId.value,
  async () => {
    await Promise.all([
      pricesStore.fetchPrices(),
      metricsStore.fetchMetrics(),
      fetchCanonicalAnalyticsData(),
    ])
  },
)
</script>
