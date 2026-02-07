<template>
  <div class="bg-slate-900 rounded-lg border border-slate-700 p-6 space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-bold text-energy-400">🤖 ML Pipeline Monitor</h2>
      <button 
        @click="refresh"
        :disabled="loading"
        class="px-4 py-2 bg-energy-500 hover:bg-energy-600 rounded-lg text-sm font-medium disabled:opacity-50"
      >
        {{ loading ? '⏳ Refreshing...' : '🔄 Refresh' }}
      </button>
    </div>

    <!-- Current Recommendation Section -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Recommendation Card -->
      <div class="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <h3 class="text-lg font-semibold text-slate-200 mb-4">📊 Current Recommendation</h3>
        
        <div class="space-y-4">
          <!-- Action Badge -->
          <div class="flex items-center justify-between">
            <span class="text-slate-400">Action:</span>
            <span :class="['px-4 py-2 rounded-lg font-bold text-white', getActionColor(recommendation.action)]">
              {{ recommendation.action }}
            </span>
          </div>
          
          <!-- Confidence -->
          <div class="flex items-center justify-between">
            <span class="text-slate-400">Confidence:</span>
            <div class="flex items-center gap-2">
              <span class="font-semibold">{{ (recommendation.confidence * 100).toFixed(0) }}%</span>
              <div class="w-32 bg-slate-700 rounded-full h-2">
                <div 
                  class="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full"
                  :style="{ width: (recommendation.confidence * 100) + '%' }"
                ></div>
              </div>
            </div>
          </div>
          
          <!-- Current State -->
          <div class="grid grid-cols-2 gap-4 pt-4 border-t border-slate-700">
            <div>
              <p class="text-xs text-slate-500 mb-1">Current Price</p>
              <p class="text-lg font-semibold text-energy-400">{{ recommendation.price.toFixed(2) }} ₴/kWh</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">Battery SOC</p>
              <p class="text-lg font-semibold text-yellow-400">{{ recommendation.battery_soc.toFixed(1) }}%</p>
            </div>
          </div>
          
          <!-- Rationale -->
          <div class="pt-4 border-t border-slate-700">
            <p class="text-xs text-slate-500 mb-2">Rationale</p>
            <p class="text-sm text-slate-300">{{ recommendation.rationale }}</p>
          </div>
        </div>
      </div>

      <!-- Model Info Card -->
      <div class="bg-slate-800 border border-slate-700 rounded-lg p-4">
        <h3 class="text-lg font-semibold text-slate-200 mb-4">📋 Model Info</h3>
        
        <div class="space-y-3">
          <!-- Model Version -->
          <div class="flex justify-between items-center">
            <span class="text-slate-400">Model:</span>
            <span class="font-mono text-energy-400">{{ modelInfo.name }}</span>
          </div>
          
          <!-- Version -->
          <div class="flex justify-between items-center">
            <span class="text-slate-400">Version:</span>
            <span class="font-mono">{{ modelInfo.version }}</span>
          </div>
          
          <!-- Accuracy -->
          <div class="flex justify-between items-center">
            <span class="text-slate-400">Test Accuracy:</span>
            <span class="font-semibold text-green-400">{{ (modelInfo.accuracy * 100).toFixed(1) }}%</span>
          </div>
          
          <!-- Backtesting Profit -->
          <div class="flex justify-between items-center">
            <span class="text-slate-400">Backtest Profit (2y):</span>
            <span class="font-semibold text-cyan-400">₴{{ modelInfo.profit.toFixed(2) }}</span>
          </div>
          
          <!-- Status -->
          <div class="pt-4 border-t border-slate-700">
            <div :class="['px-3 py-2 rounded-lg text-center font-semibold', driftDetected ? 'bg-red-900 text-red-300' : 'bg-green-900 text-green-300']">
              {{ driftDetected ? '⚠️ Drift Detected' : '✅ No Drift' }}
            </div>
          </div>
          
          <!-- Training Data -->
          <div class="pt-2 text-xs text-slate-400 space-y-1">
            <p>• Trained on 17,520 samples</p>
            <p>• 73 features engineered</p>
            <p>• 4-class classification</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Feature Importance / Top Factors -->
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4">
      <h3 class="text-lg font-semibold text-slate-200 mb-4">⭐ Top Factors Influencing Decision</h3>
      
      <div class="space-y-3">
        <div v-for="(factor, idx) in topFactors" :key="idx" class="flex items-center gap-3">
          <span class="text-xs font-semibold text-slate-400 w-20">{{ (idx + 1) }}.</span>
          <span class="flex-1 text-sm text-slate-300">{{ factor.name }}</span>
          <div class="w-32 bg-slate-700 rounded-full h-2">
            <div 
              class="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
              :style="{ width: (factor.importance * 100) + '%' }"
            ></div>
          </div>
          <span class="text-xs text-slate-400 w-12 text-right">{{ (factor.importance * 100).toFixed(1) }}%</span>
        </div>
      </div>
    </div>

    <!-- Accuracy Trend -->
    <div class="bg-slate-800 border border-slate-700 rounded-lg p-4">
      <h3 class="text-lg font-semibold text-slate-200 mb-4">📈 Model Accuracy Trend</h3>
      
      <div class="flex items-end gap-2 h-20">
        <div 
          v-for="(acc, idx) in accuracyTrend" 
          :key="idx"
          class="flex-1 bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t hover:opacity-80 transition-opacity"
          :style="{ height: (acc * 100) + '%' }"
          :title="`${(acc * 100).toFixed(1)}%`"
        ></div>
      </div>
      
      <div class="flex justify-between text-xs text-slate-400 mt-2">
        <span>Week -3</span>
        <span>Week -2</span>
        <span>Week -1</span>
        <span>Current</span>
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="error" class="bg-red-900 bg-opacity-20 border border-red-700 rounded-lg p-4">
      <p class="text-red-300 text-sm">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMLPipelineStore } from '~/app/stores/mlPipelineStore'

const mlStore = useMLPipelineStore()

const loading = ref(false)
const error = ref('')

onMounted(() => {
  mlStore.initialize()
  mlStore.startAutoRefresh(5 * 60 * 1000) // Refresh every 5 minutes
})

const refresh = async () => {
  loading.value = true
  try {
    await mlStore.fetchRecommendation()
    await mlStore.fetchMLflowStatus()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const recommendation = computed(() => mlStore.recommendation)
const modelInfo = computed(() => ({
  name: mlStore.mlflowStatus.active_model?.name || 'Unknown',
  version: mlStore.mlflowStatus.active_model?.version || '1.0.0',
  accuracy: mlStore.mlflowStatus.active_model?.metrics?.test_accuracy || 0,
  profit: mlStore.mlflowStatus.active_model?.metrics?.backtesting_profit || 0,
}))

const driftDetected = computed(() => mlStore.driftDetected)
const accuracyTrend = computed(() => mlStore.accuracyTrend)

const topFactors = computed(() => {
  const factors = mlStore.mlflowStatus.active_model?.feature_importance || []
  return factors.slice(0, 5)
})

const getActionColor = (action: string) => {
  const colors = {
    'BUY': 'bg-green-600',
    'SELL': 'bg-yellow-600',
    'DISCHARGE': 'bg-orange-600',
    'HOLD': 'bg-slate-600',
  }
  return colors[action] || 'bg-slate-600'
}
</script>
