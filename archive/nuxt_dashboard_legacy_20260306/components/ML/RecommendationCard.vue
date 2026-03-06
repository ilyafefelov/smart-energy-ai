<template>
  <div class="bg-slate-900 border border-slate-700 rounded-lg p-6 space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold text-white flex items-center gap-2">
        <span class="text-2xl">🤖</span>
        AI Recommendations
      </h3>
      <div class="flex items-center gap-2">
        <button
          @click="refreshRecommendation"
          :disabled="mlStore.loading"
          class="px-3 py-1 bg-energy-600 hover:bg-energy-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded-md transition-colors"
        >
          <span v-if="mlStore.loading" class="animate-spin">⟳</span>
          <span v-else>🔄</span>
        </button>
        <div class="flex items-center gap-1">
          <div 
            :class="[
              'w-2 h-2 rounded-full',
              mlStore.isDataFresh ? 'bg-green-500' : 'bg-yellow-500'
            ]"
          ></div>
          <span class="text-xs text-slate-400">
            {{ mlStore.lastUpdatedFormatted }}
          </span>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="mlStore.error" class="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-4">
      <p class="text-red-300 text-sm">⚠️ {{ mlStore.error }}</p>
      <button @click="mlStore.clearError" class="text-xs text-red-400 hover:text-red-300 mt-2">
        Dismiss
      </button>
    </div>

    <!-- Loading State -->
    <div v-else-if="mlStore.loading" class="flex items-center justify-center py-8">
      <div class="animate-spin text-2xl">⟳</div>
      <span class="ml-2 text-slate-400">Getting AI recommendation...</span>
    </div>

    <!-- Recommendation Content -->
    <div v-else-if="mlStore.currentRecommendation" class="space-y-4">
      <!-- Main Recommendation -->
      <div class="flex items-center gap-4">
        <div 
          :class="[
            'flex items-center justify-center w-16 h-16 rounded-full text-2xl',
            mlStore.recommendationColor === 'green' ? 'bg-green-500 bg-opacity-20 text-green-400' :
            mlStore.recommendationColor === 'blue' ? 'bg-blue-500 bg-opacity-20 text-blue-400' :
            'bg-gray-500 bg-opacity-20 text-gray-400'
          ]"
        >
          {{ mlStore.recommendationIcon }}
        </div>
        <div class="flex-1">
          <h4 class="text-xl font-bold" :class="{
            'text-green-400': mlStore.recommendationColor === 'green',
            'text-blue-400': mlStore.recommendationColor === 'blue',
            'text-gray-400': mlStore.recommendationColor === 'gray'
          }">
            {{ mlStore.currentRecommendation.action }}
          </h4>
          <p class="text-sm text-slate-400">
            Confidence: {{ Math.round(mlStore.currentRecommendation.confidence * 100) }}% 
            ({{ mlStore.confidenceLevel }})
          </p>
        </div>
      </div>

      <!-- Reasoning -->
      <div class="bg-slate-800 rounded-lg p-4">
        <h5 class="text-sm font-semibold text-slate-300 mb-2">💡 AI Reasoning</h5>
        <p class="text-sm text-slate-400">{{ mlStore.currentRecommendation.reasoning }}</p>
      </div>

      <!-- Savings Estimate -->
      <div v-if="mlStore.savingsEstimate" class="grid grid-cols-3 gap-2 text-center">
        <div class="bg-slate-800 rounded-lg p-3">
          <p class="text-xs text-slate-400">Today</p>
          <p class="text-lg font-semibold text-green-400">
            {{ mlStore.getFormattedSavings('daily') }}
          </p>
        </div>
        <div class="bg-slate-800 rounded-lg p-3">
          <p class="text-xs text-slate-400">This Month</p>
          <p class="text-lg font-semibold text-green-400">
            {{ mlStore.getFormattedSavings('monthly') }}
          </p>
        </div>
        <div class="bg-slate-800 rounded-lg p-3">
          <p class="text-xs text-slate-400">Annual</p>
          <p class="text-lg font-semibold text-green-400">
            {{ mlStore.getFormattedSavings('annual') }}
          </p>
        </div>
      </div>

      <!-- Battery Health Impact -->
      <div v-if="mlStore.batteryImpact" class="bg-slate-800 rounded-lg p-4">
        <h5 class="text-sm font-semibold text-slate-300 mb-3">🔋 Battery Impact</h5>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="text-xs text-slate-400">Current SOC</p>
            <div class="flex items-center gap-2 mt-1">
              <div class="flex-1 bg-slate-700 rounded-full h-2">
                <div 
                  class="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full transition-all"
                  :style="{ width: mlStore.batteryImpact.current_soc + '%' }"
                ></div>
              </div>
              <span class="text-sm font-semibold text-white">
                {{ Math.round(mlStore.batteryImpact.current_soc) }}%
              </span>
            </div>
          </div>
          <div>
            <p class="text-xs text-slate-400">Battery Health</p>
            <div class="flex items-center gap-2 mt-1">
              <div class="flex-1 bg-slate-700 rounded-full h-2">
                <div 
                  class="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full transition-all"
                  :style="{ width: mlStore.getBatteryHealthPercent() + '%' }"
                ></div>
              </div>
              <span class="text-sm font-semibold text-white">
                {{ Math.round(mlStore.getBatteryHealthPercent()) }}%
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-1">
              ~{{ mlStore.batteryImpact.cycles_remaining.toLocaleString() }} cycles left
            </p>
          </div>
        </div>
      </div>

      <!-- Auto Refresh Toggle -->
      <div class="flex items-center justify-between pt-2 border-t border-slate-700">
        <div class="flex items-center gap-2">
          <input
            id="autoRefresh"
            type="checkbox"
            v-model="autoRefreshEnabled"
            @change="toggleAutoRefresh"
            class="rounded bg-slate-700 border-slate-600 text-energy-500 focus:ring-energy-500"
          >
          <label for="autoRefresh" class="text-sm text-slate-400">
            Auto-refresh (5 min)
          </label>
        </div>
        <p class="text-xs text-slate-500">
          Model: {{ mlStore.modelInfo?.version || 'Phase4F-v1.0' }}
        </p>
      </div>
    </div>

    <!-- No Data State -->
    <div v-else class="text-center py-8">
      <p class="text-slate-400 mb-4">No recommendation data available</p>
      <button
        @click="refreshRecommendation"
        class="px-4 py-2 bg-energy-600 hover:bg-energy-700 text-white rounded-md transition-colors"
      >
        Get Recommendation
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMLStore } from '~/stores/mlStore'

const mlStore = useMLStore()
const autoRefreshEnabled = ref(false)

// Handle auto-refresh toggle
const toggleAutoRefresh = () => {
  if (autoRefreshEnabled.value) {
    mlStore.startAutoRefresh()
  } else {
    mlStore.stopAutoRefresh()
  }
}

// Manual refresh
const refreshRecommendation = async () => {
  await mlStore.fetchRecommendation()
}

// Initialize on mount
onMounted(() => {
  // Fetch initial recommendation if none exists
  if (!mlStore.currentRecommendation) {
    mlStore.fetchRecommendation()
  }
  
  // Sync auto-refresh state
  autoRefreshEnabled.value = mlStore.autoRefresh
})

// Cleanup on unmount
onUnmounted(() => {
  mlStore.stopAutoRefresh()
})
</script>