<template>
  <div class="bg-slate-800 border border-slate-700 rounded-lg p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-white">📊 24-Hour Forecast</h3>
      <div class="text-right">
        <p class="text-xs text-slate-400">{{ forecastSourceLabel }}</p>
        <p class="text-[11px] text-slate-500" v-if="executionStatusLine">{{ executionStatusLine }}</p>
      </div>
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

      <div class="mt-4 rounded border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs text-slate-300">
        <span class="text-slate-400">Execution linkage:</span>
        {{ executionLinkSourceLabel }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useMLStore } from '~/stores/mlStore'
import { useMLPipelineStore } from '~/stores/mlPipelineStore'
import { usePricesStore } from '~/stores/pricesStore'
import { useTenantContext } from '~/composables/useTenantContext'

interface ForecastRow {
  key: string
  time: number
  action: 'BUY' | 'SELL' | 'HOLD'
  price: number
  status: 'Peak' | 'Off-Peak' | 'Normal'
}

const pricesStore = usePricesStore()
const mlStore = useMLStore()
const mlPipelineStore = useMLPipelineStore()
const tenantContext = useTenantContext()

const mlForecastRows = computed<ForecastRow[]>(() => {
  const source = mlStore.dailyForecast.slice(0, 24)
  if (source.length === 0) {
    return []
  }

  return source.map((point, idx) => {
    const action = (point.action || 'HOLD') as ForecastRow['action']
    const status: ForecastRow['status'] = action === 'BUY'
      ? 'Off-Peak'
      : action === 'SELL'
        ? 'Peak'
        : 'Normal'

    return {
      key: `ml-${idx}-${point.hour}`,
      time: Number(point.hour) % 24,
      action,
      // ML API emits price in UAH/MWh, chart uses UAH/kWh.
      price: Number(point.price_uah_mwh || 0) / 1000,
      status,
    }
  })
})

const priceHeuristicRows = computed<ForecastRow[]>(() => {
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

const forecastRows = computed<ForecastRow[]>(() => {
  return mlForecastRows.value.length > 0 ? mlForecastRows.value : priceHeuristicRows.value
})

const forecastSourceLabel = computed(() => (mlForecastRows.value.length > 0 ? 'ML hourly forecast' : 'Live price heuristic'))

const executionStatusLine = computed(() => {
  const link = mlPipelineStore.recommendationExecutionLink
  if (!link?.synced_at) {
    return ''
  }

  const mode = String(link.mode || 'unknown').toUpperCase()
  const action = String(link.active_command || 'idle').toUpperCase()
  const source = String(link.decision_source || 'unknown').toUpperCase()
  return `${mode} / ${action} via ${source}`
})

const executionLinkSourceLabel = computed(() => {
  const link = mlPipelineStore.recommendationExecutionLink
  const net = Number(link?.realized_net_today_uah || 0).toFixed(0)
  const transitions = Number(link?.auto_transitions_today || 0)
  const economicsSource = String(link?.economics_source || 'unknown')
  return `Realized net today ${net} UAH | auto transitions ${transitions} | source ${economicsSource}`
})

const buyHours = computed(() => forecastRows.value.filter((h) => h.action === 'BUY').length)
const sellHours = computed(() => forecastRows.value.filter((h) => h.action === 'SELL').length)
const holdHours = computed(() => forecastRows.value.filter((h) => h.action === 'HOLD').length)

onMounted(async () => {
  await tenantContext.loadTenants()
  await Promise.all([
    mlStore.fetchRecommendation(tenantContext.currentTenantId.value),
    mlPipelineStore.fetchRecommendationExecutionLink(tenantContext.currentTenantId.value),
  ])
})

watch(
  () => tenantContext.currentTenantId.value,
  async (tenantId) => {
    await Promise.all([
      mlStore.fetchRecommendation(tenantId),
      mlPipelineStore.fetchRecommendationExecutionLink(tenantId),
    ])
  },
)
</script>
