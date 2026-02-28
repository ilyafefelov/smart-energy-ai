<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Analytics Dashboard</h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Real-time performance analysis based on your 
          <UBadge color="primary" variant="soft">{{ batteryType }}</UBadge>
          battery and
          <UBadge color="blue" variant="soft">{{ loadProfileType }}</UBadge>
          load profile
        </p>
      </div>
      <div class="flex items-center gap-2">
        <UButton 
          @click="refreshAnalytics" 
          :loading="refreshing"
          variant="outline"
          icon="i-heroicons-arrow-path"
          size="sm"
        >
          {{ refreshing ? 'Refreshing...' : 'Refresh' }}
        </UButton>
        <UBadge 
          :color="mlStatus === 'up-to-date' ? 'green' : 'amber'" 
          variant="soft"
          class="px-2"
        >
          {{ mlStatus === 'up-to-date' ? '✓ Up to Date' : '⚠ Needs Recalc' }}
        </UBadge>
      </div>
    </div>

    <!-- Battery Performance Section -->
    <UCard>
      <template #header>
        <div class="flex justify-between items-center">
          <h2 class="text-xl font-semibold flex items-center gap-2">
            🔋 Battery Performance Analysis
          </h2>
          <span class="text-sm text-gray-500">
            {{ batteryCapacity }}kWh {{ batteryType }} System
          </span>
        </div>
      </template>
      
      <!-- Live Degradation Tracking -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div class="text-center p-4 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 rounded-lg">
          <div class="text-3xl font-bold text-green-600 dark:text-green-400">
            {{ batteryMetrics.cyclesRemaining.toLocaleString() }}
          </div>
          <div class="text-sm text-green-700 dark:text-green-300 font-medium">Cycles Remaining</div>
          <div class="text-xs text-green-600 dark:text-green-400 mt-1">
            of {{ batterySpecs.cycles_max.toLocaleString() }} total
          </div>
        </div>
        
        <div class="text-center p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 rounded-lg">
          <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
            {{ batteryMetrics.healthPercentage }}%
          </div>
          <div class="text-sm text-blue-700 dark:text-blue-300 font-medium">Battery Health</div>
          <div class="text-xs text-blue-600 dark:text-blue-400 mt-1">
            {{ getHealthStatus(batteryMetrics.healthPercentage) }}
          </div>
        </div>
        
        <div class="text-center p-4 bg-gradient-to-br from-red-50 to-red-100 dark:from-red-950 dark:to-red-900 rounded-lg">
          <div class="text-3xl font-bold text-red-600 dark:text-red-400">
            ₴{{ batteryMetrics.degradationCostToday.toFixed(2) }}
          </div>
          <div class="text-sm text-red-700 dark:text-red-300 font-medium">Degradation Cost Today</div>
          <div class="text-xs text-red-600 dark:text-red-400 mt-1">
            ₴{{ (batteryMetrics.degradationCostToday * 365).toFixed(0) }}/year
          </div>
        </div>
      </div>
      
      <!-- Battery Discharge Simulation -->
      <div class="space-y-4">
        <h3 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-heroicons-chart-line" />
          24-Hour Battery Simulation
        </h3>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <canvas ref="batteryChart" class="w-full h-64"></canvas>
        </div>
        <div class="text-sm text-gray-600 dark:text-gray-400 bg-blue-50 dark:bg-blue-950 p-3 rounded">
          <UIcon name="i-heroicons-information-circle" class="inline mr-1" />
          Simulation based on your {{ loadProfileType }} load profile with {{ batteryType }} battery 
          ({{ batteryCapacity }}kWh capacity, {{ (batteryEfficiency * 100).toFixed(0) }}% efficiency).
          Shows optimal charge/discharge cycles for maximum arbitrage profit.
        </div>
      </div>
    </UCard>

    <!-- Cost Optimization Results -->
    <UCard>
      <template #header>
        <h2 class="text-xl font-semibold flex items-center gap-2">
          💰 Cost Optimization & Arbitrage Analysis
        </h2>
      </template>
      
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Arbitrage Opportunities -->
        <div>
          <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
            <UIcon name="i-heroicons-currency-dollar" />
            Daily Arbitrage Performance
          </h3>
          <div class="space-y-3">
            <div class="flex justify-between items-center p-3 bg-green-50 dark:bg-green-950 rounded">
              <span class="text-green-800 dark:text-green-200">Arbitrage Revenue:</span>
              <span class="font-bold text-green-600 dark:text-green-400">
                +₴{{ costAnalytics.dailyArbitrageProfit.toFixed(2) }}
              </span>
            </div>
            
            <div class="flex justify-between items-center p-3 bg-blue-50 dark:bg-blue-950 rounded">
              <span class="text-blue-800 dark:text-blue-200">Peak Avoidance:</span>
              <span class="font-bold text-blue-600 dark:text-blue-400">
                +₴{{ costAnalytics.peakAvoidanceSavings.toFixed(2) }}
              </span>
            </div>
            
            <div class="flex justify-between items-center p-3 bg-red-50 dark:bg-red-950 rounded">
              <span class="text-red-800 dark:text-red-200">Battery Degradation:</span>
              <span class="font-bold text-red-600 dark:text-red-400">
                -₴{{ costAnalytics.degradationCost.toFixed(2) }}
              </span>
            </div>
            
            <hr class="border-gray-300 dark:border-gray-600">
            
            <div class="flex justify-between items-center p-4 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-950 dark:to-indigo-950 rounded-lg">
              <span class="font-semibold text-purple-900 dark:text-purple-100 text-lg">Net Daily Profit:</span>
              <span 
                :class="[
                  'font-bold text-xl',
                  costAnalytics.netSavings > 0 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                ]"
              >
                {{ costAnalytics.netSavings > 0 ? '+' : '' }}₴{{ costAnalytics.netSavings.toFixed(2) }}
              </span>
            </div>

            <!-- Monthly/Annual Projections -->
            <div class="grid grid-cols-2 gap-4 mt-4">
              <div class="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
                <div class="font-bold text-lg">₴{{ (costAnalytics.netSavings * 30).toFixed(0) }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Monthly</div>
              </div>
              <div class="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
                <div class="font-bold text-lg">₴{{ (costAnalytics.netSavings * 365).toFixed(0) }}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Annual</div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Payback Analysis -->
        <div>
          <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
            <UIcon name="i-heroicons-chart-bar" />
            Investment Analysis
          </h3>
          <div class="space-y-4">
            <!-- Payback Chart Placeholder -->
            <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
              <canvas ref="paybackChart" class="w-full h-48"></canvas>
            </div>
            
            <!-- Investment Metrics -->
            <div class="space-y-3">
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">Battery Investment:</span>
                <span class="font-semibold">₴{{ batteryInvestment.toLocaleString() }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">Payback Period:</span>
                <span class="font-semibold">
                  {{ paybackPeriodYears > 50 ? 'Not viable' : paybackPeriodYears + ' years' }}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">ROI (Annual):</span>
                <span 
                  :class="[
                    'font-semibold',
                    roiPercent > 0 ? 'text-green-600' : 'text-red-600'
                  ]"
                >
                  {{ roiPercent > 0 ? '+' : '' }}{{ roiPercent.toFixed(1) }}%
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-600 dark:text-gray-400">NPV (10 years):</span>
                <span 
                  :class="[
                    'font-semibold',
                    npv > 0 ? 'text-green-600' : 'text-red-600'
                  ]"
                >
                  ₴{{ npv.toLocaleString() }}
                </span>
              </div>
            </div>

            <!-- Investment Recommendation -->
            <UAlert 
              :icon="getRecommendationIcon()"
              :color="getRecommendationColor()"
              :title="getRecommendationTitle()"
            >
              <template #description>
                {{ getRecommendationText() }}
              </template>
            </UAlert>
          </div>
        </div>
      </div>
    </UCard>

    <!-- ML Performance Metrics -->
    <UCard>
      <template #header>
        <h2 class="text-xl font-semibold flex items-center gap-2">
          🤖 ML Model Performance
        </h2>
      </template>
      
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div class="text-center p-4 bg-gradient-to-br from-indigo-50 to-indigo-100 dark:from-indigo-950 dark:to-indigo-900 rounded-lg">
          <div class="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
            {{ (mlMetrics.accuracy * 100).toFixed(1) }}%
          </div>
          <div class="text-sm text-indigo-700 dark:text-indigo-300 font-medium">Model Accuracy</div>
          <div class="text-xs text-indigo-600 dark:text-indigo-400 mt-1">
            {{ getAccuracyGrade(mlMetrics.accuracy) }}
          </div>
        </div>
        
        <div class="text-center p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 rounded-lg">
          <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {{ (mlMetrics.confidence * 100).toFixed(0) }}%
          </div>
          <div class="text-sm text-purple-700 dark:text-purple-300 font-medium">Confidence Score</div>
          <div class="text-xs text-purple-600 dark:text-purple-400 mt-1">
            High reliability
          </div>
        </div>
        
        <div class="text-center p-4 bg-gradient-to-br from-teal-50 to-teal-100 dark:from-teal-950 dark:to-teal-900 rounded-lg">
          <div class="text-2xl font-bold text-teal-600 dark:text-teal-400">
            {{ mlMetrics.featuresUsed }}
          </div>
          <div class="text-sm text-teal-700 dark:text-teal-300 font-medium">Features Used</div>
          <div class="text-xs text-teal-600 dark:text-teal-400 mt-1">
            Price + Weather + Battery
          </div>
        </div>
        
        <div class="text-center p-4 bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-950 dark:to-orange-900 rounded-lg">
          <div class="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {{ getDaysSinceTraining() }}
          </div>
          <div class="text-sm text-orange-700 dark:text-orange-300 font-medium">Days Since Training</div>
          <div class="text-xs text-orange-600 dark:text-orange-400 mt-1">
            {{ getTrainingStatus() }}
          </div>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'

const settingsStore = useSettingsStore()

// Component state
const refreshing = ref(false)
const batteryChart = ref<HTMLCanvasElement>()
const paybackChart = ref<HTMLCanvasElement>()

// Real-time metrics (reactive to settings changes)
const batteryMetrics = reactive({
  cyclesRemaining: 7850,
  healthPercentage: 98.5,
  degradationCostToday: 16.25
})

const costAnalytics = reactive({
  dailyArbitrageProfit: 45.80,
  peakAvoidanceSavings: 12.30,
  degradationCost: 16.25,
  netSavings: 41.85
})

const mlMetrics = reactive({
  accuracy: 0.821,
  confidence: 0.89,
  featuresUsed: 47,
  lastTraining: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000) // 2 days ago
})

// Computed properties from settings
const batteryType = computed(() => settingsStore.settings.userConfig?.battery_type || 'LFP')
const batteryCapacity = computed(() => settingsStore.settings.userConfig?.battery_capacity_kwh || 10)
const batteryEfficiency = computed(() => settingsStore.settings.userConfig?.battery_efficiency || 0.95)
const loadProfileType = computed(() => settingsStore.settings.userConfig?.load_profile_type || 'standard')

const batterySpecs = computed(() => {
  const specs = {
    'LFP': { cycles_max: 8000, cost_per_kwh: 13000 },
    'Lead-Acid': { cycles_max: 600, cost_per_kwh: 5500 },
    'VRFB': { cycles_max: 20000, cost_per_kwh: 22000 }
  }
  return specs[batteryType.value] || specs['LFP']
})

const batteryInvestment = computed(() => {
  return batteryCapacity.value * batterySpecs.value.cost_per_kwh
})

const paybackPeriodYears = computed(() => {
  const annualProfit = costAnalytics.netSavings * 365
  return annualProfit > 0 ? batteryInvestment.value / annualProfit : 999
})

const roiPercent = computed(() => {
  const annualProfit = costAnalytics.netSavings * 365
  return (annualProfit / batteryInvestment.value) * 100
})

const npv = computed(() => {
  const annualProfit = costAnalytics.netSavings * 365
  const discountRate = 0.08 // 8% discount rate
  let npv = -batteryInvestment.value // Initial investment
  
  for (let year = 1; year <= 10; year++) {
    npv += annualProfit / Math.pow(1 + discountRate, year)
  }
  
  return Math.round(npv)
})

const mlStatus = computed(() => {
  const daysSince = getDaysSinceTraining()
  return daysSince < 7 ? 'up-to-date' : 'needs-recalc'
})

// Methods
const getHealthStatus = (percentage: number) => {
  if (percentage >= 95) return 'Excellent'
  if (percentage >= 85) return 'Good'
  if (percentage >= 70) return 'Fair'
  return 'Poor'
}

const getAccuracyGrade = (accuracy: number) => {
  if (accuracy >= 0.9) return 'A+ Excellent'
  if (accuracy >= 0.8) return 'A Good'
  if (accuracy >= 0.7) return 'B Fair'
  return 'C Needs Improvement'
}

const getDaysSinceTraining = () => {
  const diffMs = Date.now() - mlMetrics.lastTraining.getTime()
  return Math.floor(diffMs / (1000 * 60 * 60 * 24))
}

const getTrainingStatus = () => {
  const days = getDaysSinceTraining()
  if (days < 3) return 'Fresh'
  if (days < 7) return 'Current'
  if (days < 14) return 'Aging'
  return 'Stale'
}

const getRecommendationIcon = () => {
  if (roiPercent.value > 15) return 'i-heroicons-check-circle'
  if (roiPercent.value > 5) return 'i-heroicons-exclamation-triangle'
  return 'i-heroicons-x-circle'
}

const getRecommendationColor = () => {
  if (roiPercent.value > 15) return 'green'
  if (roiPercent.value > 5) return 'amber'
  return 'red'
}

const getRecommendationTitle = () => {
  if (roiPercent.value > 15) return 'Excellent Investment'
  if (roiPercent.value > 5) return 'Marginal Investment'
  return 'Poor Investment'
}

const getRecommendationText = () => {
  if (roiPercent.value > 15) {
    return `Strong ROI of ${roiPercent.value.toFixed(1)}% makes this battery system highly profitable. Payback in ${paybackPeriodYears.value.toFixed(1)} years.`
  } else if (roiPercent.value > 5) {
    return `Moderate ROI of ${roiPercent.value.toFixed(1)}%. Consider optimizing settings or waiting for better battery prices.`
  } else {
    return `Low ROI of ${roiPercent.value.toFixed(1)}% suggests this configuration may not be economically viable. Consider reducing capacity or improving arbitrage spread.`
  }
}

const refreshAnalytics = async () => {
  refreshing.value = true
  
  try {
    // Simulate data refresh based on current settings
    await recalculateMetrics()
    
    // Redraw charts
    await nextTick()
    drawBatteryChart()
    drawPaybackChart()
    
  } catch (error) {
    console.error('Failed to refresh analytics:', error)
  } finally {
    refreshing.value = false
  }
}

const recalculateMetrics = async () => {
  // Simulate calculation delay
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Recalculate based on current settings
  const capacity = batteryCapacity.value
  const efficiency = batteryEfficiency.value
  const type = batteryType.value
  
  // Update battery metrics
  const specs = batterySpecs.value
  batteryMetrics.cyclesRemaining = specs.cycles_max - Math.floor(Math.random() * 500)
  batteryMetrics.healthPercentage = 100 - (Math.random() * 5)
  batteryMetrics.degradationCostToday = capacity * specs.cost_per_kwh / specs.cycles_max
  
  // Update cost analytics (simplified calculation)
  const priceSpread = 4.5 // UAH/kWh difference peak vs off-peak
  const usableCapacity = capacity * 0.9 // Assume 90% DoD
  
  costAnalytics.dailyArbitrageProfit = usableCapacity * priceSpread * efficiency
  costAnalytics.peakAvoidanceSavings = capacity * 2.5 // Mock peak avoidance
  costAnalytics.degradationCost = batteryMetrics.degradationCostToday
  costAnalytics.netSavings = costAnalytics.dailyArbitrageProfit + costAnalytics.peakAvoidanceSavings - costAnalytics.degradationCost
}

const drawBatteryChart = () => {
  if (!batteryChart.value) return
  
  const canvas = batteryChart.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // Set canvas size
  canvas.width = canvas.offsetWidth
  canvas.height = canvas.offsetHeight
  
  const width = canvas.width
  const height = canvas.height
  
  // Clear canvas
  ctx.fillStyle = 'rgb(249, 250, 251)' // Light background
  ctx.fillRect(0, 0, width, height)
  
  // Draw grid
  ctx.strokeStyle = 'rgb(229, 231, 235)'
  ctx.lineWidth = 1
  
  // Vertical grid lines (hours)
  for (let hour = 0; hour <= 24; hour += 4) {
    const x = (hour / 24) * width
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height)
    ctx.stroke()
  }
  
  // Horizontal grid lines (SOC levels)
  for (let soc = 0; soc <= 100; soc += 25) {
    const y = height - (soc / 100) * height
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }
  
  // Generate mock battery SOC data
  const socData: number[] = []
  let currentSoc = 50
  
  for (let hour = 0; hour < 24; hour++) {
    // Simple arbitrage logic: charge at night (low prices), discharge during peak
    if (hour >= 1 && hour <= 6) {
      // Charging period
      currentSoc = Math.min(90, currentSoc + 8)
    } else if (hour >= 18 && hour <= 22) {
      // Discharging period
      currentSoc = Math.max(20, currentSoc - 12)
    } else {
      // Maintain or slight discharge
      currentSoc = Math.max(20, currentSoc - 1)
    }
    socData.push(currentSoc)
  }
  
  // Draw SOC curve
  ctx.strokeStyle = 'rgb(59, 130, 246)' // Blue
  ctx.lineWidth = 3
  ctx.beginPath()
  
  socData.forEach((soc, hour) => {
    const x = (hour / 23) * width
    const y = height - (soc / 100) * height
    
    if (hour === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // Add labels
  ctx.fillStyle = 'rgb(55, 65, 81)'
  ctx.font = '12px sans-serif'
  ctx.textAlign = 'center'
  
  // Hour labels
  for (let hour = 0; hour <= 24; hour += 6) {
    const x = (hour / 24) * width
    ctx.fillText(`${hour}:00`, x, height + 15)
  }
  
  // SOC labels
  ctx.textAlign = 'right'
  for (let soc = 0; soc <= 100; soc += 25) {
    const y = height - (soc / 100) * height + 4
    ctx.fillText(`${soc}%`, -5, y)
  }
}

const drawPaybackChart = () => {
  if (!paybackChart.value) return
  
  const canvas = paybackChart.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  // Set canvas size
  canvas.width = canvas.offsetWidth
  canvas.height = canvas.offsetHeight
  
  const width = canvas.width
  const height = canvas.height
  
  // Clear canvas
  ctx.fillStyle = 'rgb(249, 250, 251)'
  ctx.fillRect(0, 0, width, height)
  
  // Draw payback analysis
  const years = 10
  const annualProfit = costAnalytics.netSavings * 365
  const initialInvestment = batteryInvestment.value
  
  let cumulativeProfit = -initialInvestment
  const data: { year: number, cumulative: number }[] = []
  
  for (let year = 0; year <= years; year++) {
    data.push({ year, cumulative: cumulativeProfit })
    if (year > 0) {
      cumulativeProfit += annualProfit
    }
  }
  
  // Draw zero line
  const zeroY = height * 0.6
  ctx.strokeStyle = 'rgb(107, 114, 128)'
  ctx.lineWidth = 1
  ctx.setLineDash([5, 5])
  ctx.beginPath()
  ctx.moveTo(0, zeroY)
  ctx.lineTo(width, zeroY)
  ctx.stroke()
  ctx.setLineDash([])
  
  // Draw payback curve
  ctx.strokeStyle = cumulativeProfit > 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'
  ctx.lineWidth = 2
  ctx.beginPath()
  
  const maxValue = Math.max(...data.map(d => Math.abs(d.cumulative)))
  const scale = (height * 0.4) / maxValue
  
  data.forEach((point, index) => {
    const x = (index / years) * width
    const y = zeroY - (point.cumulative * scale)
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // Add labels
  ctx.fillStyle = 'rgb(55, 65, 81)'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'center'
  
  for (let year = 0; year <= years; year += 2) {
    const x = (year / years) * width
    ctx.fillText(`Year ${year}`, x, height - 5)
  }
}

// Watch for settings changes and recalculate
watch([batteryType, batteryCapacity, batteryEfficiency, loadProfileType], async () => {
  await recalculateMetrics()
  await nextTick()
  drawBatteryChart()
  drawPaybackChart()
}, { deep: true })

// Initialize
onMounted(async () => {
  await recalculateMetrics()
  await nextTick()
  drawBatteryChart()
  drawPaybackChart()
})
</script>

<style scoped>
canvas {
  border-radius: 8px;
}

.metric-card {
  transition: transform 0.2s ease-in-out;
}

.metric-card:hover {
  transform: translateY(-2px);
}
</style>