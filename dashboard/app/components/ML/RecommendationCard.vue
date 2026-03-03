<template>
  <div class="bg-slate-800 border border-slate-700 rounded-lg p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-white">🤖 AI Recommendation</h3>
      <button 
        @click="refreshRecommendation" 
        :disabled="mlStore.isLoading"
        class="px-3 py-1 bg-energy-600 hover:bg-energy-700 disabled:opacity-50 rounded text-sm"
      >
        {{ mlStore.isLoading ? 'Loading...' : 'Refresh' }}
      </button>
    </div>

    <!-- Error State -->
    <div v-if="mlStore.error" class="bg-red-900 bg-opacity-30 border border-red-700 rounded p-3 mb-4">
      <p class="text-red-300 text-sm">⚠️ {{ mlStore.error }}</p>
    </div>

    <!-- Recommendation Display -->
    <div v-else-if="mlStore.currentRecommendation" class="space-y-4">
      <!-- Action Badge -->
      <div class="flex items-center space-x-3">
        <span class="text-3xl">{{ mlStore.getRecommendationIcon() }}</span>
        <div>
          <span 
            class="inline-block px-3 py-1 rounded-full text-sm font-semibold"
            :class="{
              'bg-green-900 text-green-300': mlStore.currentRecommendation.action === 'BUY',
              'bg-blue-900 text-blue-300': mlStore.currentRecommendation.action === 'SELL', 
              'bg-gray-900 text-gray-300': mlStore.currentRecommendation.action === 'HOLD'
            }"
          >
            {{ mlStore.currentRecommendation.action }}
          </span>
          <p class="text-sm text-slate-400 mt-1">
            Confidence: {{ Math.round(mlStore.currentRecommendation.confidence * 100) }}%
          </p>
        </div>
      </div>

      <!-- Reasoning -->
      <div class="bg-slate-900 rounded p-3">
        <p class="text-sm text-slate-300">{{ mlStore.currentRecommendation.reasoning }}</p>
      </div>

      <!-- Savings Estimate -->
      <div class="grid grid-cols-3 gap-3 text-center">
        <div>
          <p class="text-xs text-slate-400">Daily</p>
          <p class="font-semibold text-energy-400">{{ mlStore.getFormattedSavings('daily') }}</p>
        </div>
        <div>
          <p class="text-xs text-slate-400">Monthly</p>
          <p class="font-semibold text-energy-400">{{ mlStore.getFormattedSavings('monthly') }}</p>
        </div>
        <div>
          <p class="text-xs text-slate-400">Annual</p>
          <p class="font-semibold text-energy-400">{{ mlStore.getFormattedSavings('annual') }}</p>
        </div>
      </div>

      <!-- Last Updated -->
      <p class="text-xs text-slate-500 text-center">
        Last updated: {{ new Date(mlStore.currentRecommendation.timestamp).toLocaleTimeString() }}
      </p>
    </div>

    <!-- Loading State -->
    <div v-else-if="mlStore.isLoading" class="text-center py-8">
      <div class="animate-spin w-8 h-8 border-2 border-energy-400 border-t-transparent rounded-full mx-auto mb-2"></div>
      <p class="text-slate-400">Loading recommendation...</p>
    </div>

    <!-- Initial State -->
    <div v-else class="text-center py-8">
      <p class="text-slate-400 mb-3">No recommendation available</p>
      <button 
        @click="refreshRecommendation"
        class="px-4 py-2 bg-energy-600 hover:bg-energy-700 rounded"
      >
        Get Recommendation
      </button>
    </div>
  </div>
</template>

<script setup>
import { useMLStore } from '~/stores/mlStore'
import { useTenantContext } from '~/composables/useTenantContext'

const mlStore = useMLStore()
const tenantContext = useTenantContext()

const refreshRecommendation = async () => {
  await mlStore.fetchRecommendation(tenantContext.currentTenantId.value)
}

// Load recommendation on mount
onMounted(async () => {
  await tenantContext.loadTenants()
  await refreshRecommendation()
})

watch(
  () => tenantContext.currentTenantId.value,
  async () => {
    await refreshRecommendation()
  },
)
</script>