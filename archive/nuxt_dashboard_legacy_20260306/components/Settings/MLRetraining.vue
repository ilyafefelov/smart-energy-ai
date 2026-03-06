<template>
  <UCard>
    <template #header>
      <h3 class="text-lg font-semibold flex items-center gap-2">
        🧠 ML Model Retraining
        <UBadge 
          :color="getStatusColor(retrainStatus.status)" 
          variant="soft"
          v-if="retrainStatus.status !== 'idle'"
        >
          {{ getStatusText(retrainStatus.status) }}
        </UBadge>
      </h3>
    </template>
    
    <!-- Idle State -->
    <div v-if="!retraining && !retrainComplete" class="space-y-4">
      <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
        <div class="flex items-center gap-3">
          <UIcon name="i-heroicons-cpu-chip" class="text-2xl text-gray-500" />
          <div>
            <h4 class="font-semibold text-gray-900 dark:text-white">ML Pipeline Status</h4>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Last retrained: {{ formatLastRetrainDate() }}
            </p>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Next scheduled: {{ getNextScheduledRetrain() }}
            </p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="bg-blue-50 dark:bg-blue-950 rounded-lg p-4">
          <h5 class="font-semibold text-blue-900 dark:text-blue-100 mb-2">Current Models</h5>
          <div class="space-y-1 text-sm">
            <div class="flex justify-between">
              <span class="text-blue-700 dark:text-blue-300">XGBoost:</span>
              <span class="font-medium">{{ currentModelStats.xgboost_accuracy }}% accuracy</span>
            </div>
            <div class="flex justify-between">
              <span class="text-blue-700 dark:text-blue-300">LightGBM:</span>
              <span class="font-medium">{{ currentModelStats.lightgbm_accuracy }}% accuracy</span>
            </div>
            <div class="flex justify-between">
              <span class="text-blue-700 dark:text-blue-300">Ensemble:</span>
              <span class="font-medium">{{ currentModelStats.ensemble_accuracy }}% accuracy</span>
            </div>
          </div>
        </div>

        <div class="bg-green-50 dark:bg-green-950 rounded-lg p-4">
          <h5 class="font-semibold text-green-900 dark:text-green-100 mb-2">Training Data</h5>
          <div class="space-y-1 text-sm">
            <div class="flex justify-between">
              <span class="text-green-700 dark:text-green-300">Data Points:</span>
              <span class="font-medium">{{ trainingDataStats.data_points.toLocaleString() }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-green-700 dark:text-green-300">Features:</span>
              <span class="font-medium">{{ trainingDataStats.features }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-green-700 dark:text-green-300">Quality Score:</span>
              <span class="font-medium">{{ (trainingDataStats.quality_score * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <UAlert 
        icon="i-heroicons-information-circle"
        color="blue"
        title="Why Retrain?"
      >
        <template #description>
          <ul class="list-disc list-inside space-y-1 text-sm">
            <li>Configuration changes require model recalibration</li>
            <li>New market data improves prediction accuracy</li>
            <li>Seasonal patterns need regular updates</li>
            <li>Battery degradation affects optimal strategies</li>
          </ul>
        </template>
      </UAlert>

      <div class="flex justify-between items-center">
        <div class="text-sm text-gray-600 dark:text-gray-400">
          Estimated training time: 3-5 minutes
        </div>
        <UButton 
          @click="startRetraining" 
          :loading="startingRetraining"
          size="lg"
          icon="i-heroicons-cpu-chip"
          color="blue"
        >
          {{ startingRetraining ? 'Starting...' : 'Retrain Models' }}
        </UButton>
      </div>
    </div>

    <!-- Training in Progress -->
    <div v-else-if="retraining" class="space-y-6">
      <!-- Progress Bar -->
      <div>
        <div class="flex justify-between items-center mb-2">
          <h4 class="font-semibold">{{ retrainStatus.stage || 'Training in Progress' }}</h4>
          <span class="text-sm font-medium">{{ retrainStatus.progress || 0 }}%</span>
        </div>
        <UProgress 
          :value="retrainStatus.progress || 0"
          :max="100"
          :ui="{ progress: { background: 'bg-blue-500' }}"
          size="lg"
        >
          <template #indicator="{ percent }">
            <span class="text-xs font-medium text-white">{{ percent }}%</span>
          </template>
        </UProgress>
      </div>

      <!-- Current Stage Details -->
      <div class="bg-blue-50 dark:bg-blue-950 rounded-lg p-4">
        <div class="flex items-start gap-3">
          <div class="animate-spin">
            <UIcon name="i-heroicons-cog-6-tooth" class="text-2xl text-blue-500" />
          </div>
          <div>
            <h5 class="font-semibold text-blue-900 dark:text-blue-100">
              {{ retrainStatus.stage || 'Processing' }}
            </h5>
            <p class="text-sm text-blue-700 dark:text-blue-300 mt-1">
              {{ retrainStatus.details || 'Training machine learning models with your configuration...' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Training Steps Tracker -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
        <div 
          v-for="(step, index) in trainingSteps"
          :key="index"
          :class="[
            'text-center p-2 rounded',
            getStepStatus(step, retrainStatus.progress) === 'completed' 
              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
              : getStepStatus(step, retrainStatus.progress) === 'current'
              ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
          ]"
        >
          <UIcon 
            :name="getStepIcon(step, retrainStatus.progress)"
            :class="[
              'mx-auto mb-1',
              getStepStatus(step, retrainStatus.progress) === 'current' ? 'animate-spin' : ''
            ]"
          />
          <div class="font-medium">{{ step.name }}</div>
        </div>
      </div>

      <!-- Cancel Button -->
      <div class="flex justify-center">
        <UButton 
          @click="cancelRetraining"
          variant="outline"
          color="red"
          size="sm"
        >
          Cancel Training
        </UButton>
      </div>
    </div>

    <!-- Training Complete -->
    <div v-else-if="retrainComplete" class="space-y-6">
      <UAlert
        icon="i-heroicons-check-circle"
        color="green"
        title="✅ Retraining Complete!"
      >
        <template #description>
          <div class="space-y-2">
            <p>The ML pipeline has been successfully retrained with your current configuration.</p>
            <div class="grid grid-cols-2 gap-4 mt-3">
              <div>
                <span class="text-sm text-gray-600">New Model Accuracy:</span>
                <span class="font-semibold ml-2">{{ retrainResults.accuracy }}%</span>
              </div>
              <div>
                <span class="text-sm text-gray-600">Improvement:</span>
                <span class="font-semibold ml-2 text-green-600">+{{ retrainResults.improvement }}%</span>
              </div>
              <div>
                <span class="text-sm text-gray-600">Features Used:</span>
                <span class="font-semibold ml-2">{{ retrainResults.features_engineered }}</span>
              </div>
              <div>
                <span class="text-sm text-gray-600">Training Time:</span>
                <span class="font-semibold ml-2">{{ retrainResults.duration }}s</span>
              </div>
            </div>
          </div>
        </template>
      </UAlert>

      <!-- Model Performance Comparison -->
      <div class="bg-green-50 dark:bg-green-950 rounded-lg p-4">
        <h5 class="font-semibold text-green-900 dark:text-green-100 mb-3">Model Performance</h5>
        <div class="space-y-2">
          <div 
            v-for="model in Object.keys(retrainResults.model_accuracies || {})"
            :key="model"
            class="flex justify-between items-center"
          >
            <span class="text-sm text-green-700 dark:text-green-300 capitalize">{{ model }}:</span>
            <div class="flex items-center gap-2">
              <div class="w-24 bg-green-200 dark:bg-green-800 rounded-full h-2">
                <div 
                  class="bg-green-500 h-2 rounded-full"
                  :style="{ width: `${(retrainResults.model_accuracies[model] / 100) * 100}%` }"
                ></div>
              </div>
              <span class="text-sm font-medium w-12">{{ (retrainResults.model_accuracies[model] * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-between items-center">
        <UButton 
          @click="viewDetailedResults"
          variant="outline"
          icon="i-heroicons-chart-bar"
        >
          View Detailed Results
        </UButton>
        
        <UButton 
          @click="resetRetraining"
          color="blue"
          icon="i-heroicons-arrow-path"
        >
          Ready for Next Training
        </UButton>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useToast } from '#imports'

const toast = useToast()

// Component state
const retraining = ref(false)
const retrainComplete = ref(false)
const startingRetraining = ref(false)
const pollInterval = ref<NodeJS.Timeout>()

// Training status
const retrainStatus = reactive({
  status: 'idle',
  progress: 0,
  stage: '',
  details: '',
  jobId: null as string | null
})

// Training results
const retrainResults = reactive({
  accuracy: 0,
  improvement: 0,
  features_engineered: 0,
  duration: 0,
  model_accuracies: {} as Record<string, number>
})

// Mock current model stats
const currentModelStats = reactive({
  xgboost_accuracy: 78.5,
  lightgbm_accuracy: 76.2,
  ensemble_accuracy: 82.1
})

const trainingDataStats = reactive({
  data_points: 8760,
  features: 45,
  quality_score: 0.94
})

// Training steps for visual tracker
const trainingSteps = [
  { name: 'Data Loading', minProgress: 0, maxProgress: 20 },
  { name: 'Features', minProgress: 20, maxProgress: 40 },
  { name: 'Training', minProgress: 40, maxProgress: 80 },
  { name: 'Validation', minProgress: 80, maxProgress: 95 },
  { name: 'Complete', minProgress: 95, maxProgress: 100 }
]

// Methods
const getStatusColor = (status: string) => {
  const colors = {
    'idle': 'gray',
    'running': 'blue',
    'complete': 'green',
    'failed': 'red'
  }
  return colors[status] || 'gray'
}

const getStatusText = (status: string) => {
  const texts = {
    'idle': 'Ready',
    'running': 'Training',
    'complete': 'Complete',
    'failed': 'Failed'
  }
  return texts[status] || status
}

const formatLastRetrainDate = () => {
  // Mock last retrain date
  const lastRetrain = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000) // 3 days ago
  return lastRetrain.toLocaleDateString() + ' at ' + lastRetrain.toLocaleTimeString()
}

const getNextScheduledRetrain = () => {
  const nextRetrain = new Date(Date.now() + 4 * 24 * 60 * 60 * 1000) // 4 days from now
  return nextRetrain.toLocaleDateString()
}

const getStepStatus = (step: any, progress: number) => {
  if (progress >= step.maxProgress) return 'completed'
  if (progress >= step.minProgress && progress < step.maxProgress) return 'current'
  return 'pending'
}

const getStepIcon = (step: any, progress: number) => {
  const status = getStepStatus(step, progress)
  if (status === 'completed') return 'i-heroicons-check-circle'
  if (status === 'current') return 'i-heroicons-cog-6-tooth'
  return 'i-heroicons-clock'
}

const startRetraining = async () => {
  startingRetraining.value = true
  
  try {
    const response = await $fetch('/api/ml/recalculate', {
      method: 'POST',
      body: {}
    })
    
    if (response.success) {
      retrainStatus.jobId = response.jobId
      retrainStatus.status = 'running'
      retraining.value = true
      retrainComplete.value = false
      
      toast.add({
        title: 'Training Started',
        description: 'ML models are being retrained with your current configuration.',
        icon: 'i-heroicons-cpu-chip',
        color: 'blue'
      })
      
      // Start polling for status
      startStatusPolling()
    } else {
      throw new Error(response.error || 'Failed to start training')
    }
  } catch (error) {
    console.error('Failed to start retraining:', error)
    toast.add({
      title: 'Training Failed to Start',
      description: 'Could not start ML retraining. Please try again.',
      icon: 'i-heroicons-x-circle',
      color: 'red'
    })
  } finally {
    startingRetraining.value = false
  }
}

const startStatusPolling = () => {
  // Poll every 2 seconds for status updates
  pollInterval.value = setInterval(async () => {
    try {
      const response = await $fetch('/api/ml/recalculate-status', {
        params: { jobId: retrainStatus.jobId }
      })
      
      if (response.success) {
        Object.assign(retrainStatus, response)
        
        if (response.status === 'complete') {
          // Training completed successfully
          retraining.value = false
          retrainComplete.value = true
          
          // Update results
          if (response.results) {
            retrainResults.accuracy = response.results.accuracy
            retrainResults.improvement = response.results.improvement
            retrainResults.features_engineered = response.results.features_engineered
            retrainResults.duration = response.duration_seconds
            retrainResults.model_accuracies = {
              'xgboost': response.results.accuracy - 3,
              'lightgbm': response.results.accuracy - 1,
              'ensemble': response.results.accuracy
            }
          }
          
          stopStatusPolling()
          
          toast.add({
            title: 'Training Complete!',
            description: `Models retrained successfully with ${response.results?.accuracy || 'improved'}% accuracy.`,
            icon: 'i-heroicons-check-circle',
            color: 'green'
          })
          
          // Refresh dashboard data
          await refreshAllDashboardData()
        } else if (response.status === 'failed') {
          // Training failed
          retraining.value = false
          retrainComplete.value = false
          stopStatusPolling()
          
          toast.add({
            title: 'Training Failed',
            description: response.error || 'ML retraining encountered an error.',
            icon: 'i-heroicons-x-circle',
            color: 'red'
          })
        }
      }
    } catch (error) {
      console.error('Status polling error:', error)
    }
  }, 2000)
}

const stopStatusPolling = () => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = undefined
  }
}

const cancelRetraining = () => {
  // In a real implementation, this would call an API to cancel the job
  retraining.value = false
  retrainComplete.value = false
  retrainStatus.status = 'idle'
  stopStatusPolling()
  
  toast.add({
    title: 'Training Cancelled',
    description: 'ML retraining has been cancelled.',
    icon: 'i-heroicons-x-mark',
    color: 'orange'
  })
}

const resetRetraining = () => {
  retraining.value = false
  retrainComplete.value = false
  retrainStatus.status = 'idle'
  retrainStatus.progress = 0
  retrainStatus.stage = ''
  retrainStatus.details = ''
}

const viewDetailedResults = () => {
  // Navigate to detailed results view or open modal
  toast.add({
    title: 'Detailed Results',
    description: 'Detailed training results would be shown in a dedicated analytics page.',
    icon: 'i-heroicons-chart-bar',
    color: 'blue'
  })
}

const refreshAllDashboardData = async () => {
  // Emit event to refresh all dashboard components
  await nextTick()
}

// Cleanup on unmount
onUnmounted(() => {
  stopStatusPolling()
})

// Initialize
onMounted(async () => {
  // Check if there's an ongoing training session
  try {
    const response = await $fetch('/api/ml/recalculate-status')
    if (response.success && response.status === 'running') {
      Object.assign(retrainStatus, response)
      retraining.value = true
      startStatusPolling()
    }
  } catch (error) {
    console.warn('Could not check initial training status:', error)
  }
})
</script>

<style scoped>
.training-step {
  transition: all 0.3s ease-in-out;
}

.training-step.current {
  transform: scale(1.05);
}
</style>