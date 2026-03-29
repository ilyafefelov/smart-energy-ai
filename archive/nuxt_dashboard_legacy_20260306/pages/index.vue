<template>
  <div class="dashboard-page min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-7xl">
      <!-- Dashboard Header -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Smart Energy Dashboard
          </h1>
          <p class="text-gray-600 dark:text-gray-400">
            Real-time energy arbitrage monitoring and control
          </p>
        </div>
        
        <div class="flex items-center gap-4">
          <UBadge 
            :color="systemStatus.color" 
            variant="soft" 
            class="px-3 py-2"
          >
            {{ systemStatus.icon }} {{ systemStatus.text }}
          </UBadge>
          
          <UButton 
            @click="refreshDashboard" 
            :loading="refreshing"
            variant="outline"
            icon="i-heroicons-arrow-path"
            size="sm"
          >
            {{ refreshing ? 'Refreshing...' : 'Refresh' }}
          </UButton>
        </div>
      </div>

      <!-- System Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <!-- Current Profit -->
        <UCard class="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-green-600 dark:text-green-400">Today's Profit</p>
              <p class="text-2xl font-bold text-green-700 dark:text-green-300">
                ₴{{ todayProfit.toFixed(2) }}
              </p>
              <p class="text-xs text-green-600 dark:text-green-400 mt-1">
                {{ profitTrend > 0 ? '↗' : profitTrend < 0 ? '↘' : '→' }} vs yesterday
              </p>
            </div>
            <div class="p-3 bg-green-200 dark:bg-green-800 rounded-full">
              <UIcon name="i-heroicons-currency-dollar" class="text-2xl text-green-700 dark:text-green-300" />
            </div>
          </div>
        </UCard>

        <!-- Battery Status -->
        <UCard class="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-blue-600 dark:text-blue-400">Battery SOC</p>
              <p class="text-2xl font-bold text-blue-700 dark:text-blue-300">
                {{ currentSOC }}%
              </p>
              <p class="text-xs text-blue-600 dark:text-blue-400 mt-1">
                {{ batteryAction }} • {{ batteryHealth }}% health
              </p>
            </div>
            <div class="p-3 bg-blue-200 dark:bg-blue-800 rounded-full">
              <UIcon name="i-heroicons-battery-100" class="text-2xl text-blue-700 dark:text-blue-300" />
            </div>
          </div>
        </UCard>

        <!-- Current Power -->
        <UCard class="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-purple-600 dark:text-purple-400">Current Power</p>
              <p class="text-2xl font-bold text-purple-700 dark:text-purple-300">
                {{ Math.abs(currentPower) }} kW
              </p>
              <p class="text-xs text-purple-600 dark:text-purple-400 mt-1">
                {{ currentPower > 0 ? '⚡ Charging' : currentPower < 0 ? '🔌 Discharging' : '⏸ Idle' }}
              </p>
            </div>
            <div class="p-3 bg-purple-200 dark:bg-purple-800 rounded-full">
              <UIcon name="i-heroicons-bolt" class="text-2xl text-purple-700 dark:text-purple-300" />
            </div>
          </div>
        </UCard>

        <!-- Energy Price -->
        <UCard class="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-950 dark:to-orange-900">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-orange-600 dark:text-orange-400">Current Price</p>
              <p class="text-2xl font-bold text-orange-700 dark:text-orange-300">
                ₴{{ currentPrice.toFixed(1) }}
              </p>
              <p class="text-xs text-orange-600 dark:text-orange-400 mt-1">
                {{ isPeakHour ? '🔴 Peak' : '🟢 Off-peak' }} • {{ priceSpread.toFixed(1)} spread
              </p>
            </div>
            <div class="p-3 bg-orange-200 dark:bg-orange-800 rounded-full">
              <UIcon name="i-heroicons-chart-line" class="text-2xl text-orange-700 dark:text-orange-300" />
            </div>
          </div>
        </UCard>
      </div>

      <!-- Main Dashboard Content -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <!-- Live Charts Section -->
        <div class="xl:col-span-2 space-y-6">
          <!-- 24-Hour Energy Flow Chart -->
          <UCard>
            <template #header>
              <div class="flex justify-between items-center">
                <h3 class="text-lg font-semibold flex items-center gap-2">
                  📈 24-Hour Energy Flow
                </h3>
                <UButtonGroup size="sm" orientation="horizontal">
                  <UButton 
                    variant="ghost" 
                    :color="chartTimeframe === '24h' ? 'primary' : 'gray'"
                    @click="chartTimeframe = '24h'"
                  >
                    24H
                  </UButton>
                  <UButton 
                    variant="ghost" 
                    :color="chartTimeframe === '7d' ? 'primary' : 'gray'"
                    @click="chartTimeframe = '7d'"
                  >
                    7D
                  </UButton>
                  <UButton 
                    variant="ghost" 
                    :color="chartTimeframe === '30d' ? 'primary' : 'gray'"
                    @click="chartTimeframe = '30d'"
                  >
                    30D
                  </UButton>
                </UButtonGroup>
              </div>
            </template>
            
            <div class="h-80">
              <canvas ref="energyFlowChart" class="w-full h-full"></canvas>
            </div>
            
            <div class="mt-4 flex justify-between text-sm text-gray-600 dark:text-gray-400">
              <div class="flex items-center gap-4">
                <div class="flex items-center gap-2">
                  <div class="w-3 h-3 bg-blue-500 rounded"></div>
                  <span>Battery SOC</span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="w-3 h-3 bg-green-500 rounded"></div>
                  <span>Energy Price</span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="w-3 h-3 bg-purple-500 rounded"></div>
                  <span>Power Flow</span>
                </div>
              </div>
              <span>
                Next action: {{ nextAction }} in {{ timeToNextAction }}
              </span>
            </div>
          </UCard>

          <!-- Arbitrage Opportunities -->
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold flex items-center gap-2">
                💰 Today's Arbitrage Opportunities
              </h3>
            </template>
            
            <div class="space-y-3">
              <div 
                v-for="opportunity in nextOpportunities" 
                :key="opportunity.hour"
                class="flex items-center justify-between p-3 rounded-lg"
                :class="getOpportunityBgClass(opportunity.action)"
              >
                <div class="flex items-center gap-3">
                  <div class="text-2xl">{{ getActionIcon(opportunity.action) }}</div>
                  <div>
                    <p class="font-semibold capitalize">{{ opportunity.action }}</p>
                    <p class="text-sm opacity-75">{{ formatHour(opportunity.hour) }}</p>
                  </div>
                </div>
                
                <div class="text-right">
                  <p class="font-semibold">₴{{ opportunity.profit.toFixed(2) }}</p>
                  <p class="text-sm opacity-75">{{ (opportunity.confidence * 100).toFixed(0) }}% conf.</p>
                </div>
              </div>
            </div>
          </UCard>
        </div>

        <!-- Side Panel -->
        <div class="space-y-6">
          <!-- System Configuration Summary -->
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold flex items-center gap-2">
                ⚙️ System Configuration
              </h3>
            </template>
            
            <div class="space-y-4">
              <!-- Battery Info -->
              <div class="flex justify-between items-center p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                <div>
                  <p class="font-semibold text-blue-900 dark:text-blue-100">Battery</p>
                  <p class="text-sm text-blue-700 dark:text-blue-300">
                    {{ userConfig?.battery_type }} {{ userConfig?.battery_capacity_kwh }}kWh
                  </p>
                </div>
                <UButton 
                  to="/settings" 
                  size="sm" 
                  variant="ghost"
                  icon="i-heroicons-cog-6-tooth"
                />
              </div>

              <!-- Load Profile -->
              <div class="flex justify-between items-center p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                <div>
                  <p class="font-semibold text-green-900 dark:text-green-100">Load Profile</p>
                  <p class="text-sm text-green-700 dark:text-green-300">
                    {{ formatLoadProfile(userConfig?.load_profile_type) }} • {{ userConfig?.load_peak_kw }}kW peak
                  </p>
                </div>
                <UButton 
                  to="/settings" 
                  size="sm" 
                  variant="ghost"
                  icon="i-heroicons-cog-6-tooth"
                />
              </div>

              <!-- ML Model Status -->
              <div class="flex justify-between items-center p-3 bg-purple-50 dark:bg-purple-950 rounded-lg">
                <div>
                  <p class="font-semibold text-purple-900 dark:text-purple-100">ML Model</p>
                  <p class="text-sm text-purple-700 dark:text-purple-300">
                    {{ mlAccuracy }}% accuracy • {{ daysSinceTraining }}d old
                  </p>
                </div>
                <UButton 
                  to="/settings" 
                  size="sm" 
                  variant="ghost"
                  icon="i-heroicons-cpu-chip"
                />
              </div>
            </div>
          </UCard>

          <!-- Quick Actions -->
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold flex items-center gap-2">
                🎮 Quick Actions
              </h3>
            </template>
            
            <div class="space-y-3">
              <UButton 
                @click="forceCharge"
                :loading="actionLoading.charge"
                block
                variant="outline"
                color="green"
                icon="i-heroicons-arrow-up"
              >
                Force Charge
              </UButton>
              
              <UButton 
                @click="forceDischarge"
                :loading="actionLoading.discharge"
                block
                variant="outline"
                color="red"
                icon="i-heroicons-arrow-down"
              >
                Force Discharge
              </UButton>
              
              <UButton 
                @click="toggleAutoMode"
                :loading="actionLoading.auto"
                block
                :variant="autoModeEnabled ? 'solid' : 'outline'"
                :color="autoModeEnabled ? 'blue' : 'gray'"
                :icon="autoModeEnabled ? 'i-heroicons-play' : 'i-heroicons-pause'"
              >
                {{ autoModeEnabled ? 'Auto Mode ON' : 'Auto Mode OFF' }}
              </UButton>
              
              <UButton 
                @click="triggerMLRetrain"
                :loading="actionLoading.retrain"
                block
                variant="outline"
                color="purple"
                icon="i-heroicons-cpu-chip"
              >
                Retrain ML Model
              </UButton>
            </div>
          </UCard>

          <!-- Recent Alerts -->
          <UCard>
            <template #header>
              <h3 class="text-lg font-semibold flex items-center gap-2">
                🚨 Recent Alerts
              </h3>
            </template>
            
            <div class="space-y-2 max-h-60 overflow-y-auto">
              <div 
                v-for="alert in recentAlerts" 
                :key="alert.id"
                class="flex items-start gap-3 p-3 rounded-lg"
                :class="getAlertBgClass(alert.type)"
              >
                <div class="text-lg flex-shrink-0 mt-0.5">{{ getAlertIcon(alert.type) }}</div>
                <div>
                  <p class="font-medium text-sm">{{ alert.title }}</p>
                  <p class="text-xs opacity-75">{{ alert.message }}</p>
                  <p class="text-xs opacity-50 mt-1">{{ formatTime(alert.timestamp) }}</p>
                </div>
              </div>
              
              <div v-if="recentAlerts.length === 0" class="text-center text-gray-500 py-4">
                <UIcon name="i-heroicons-check-circle" class="text-2xl mb-2" />
                <p class="text-sm">All systems running smoothly</p>
              </div>
            </div>
          </UCard>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useSettingsStore } from '~/stores/settingsStore'
import { useAnalyticsStore } from '~/stores/analyticsStore'
import { useToast } from '#imports'

const settingsStore = useSettingsStore()
const analyticsStore = useAnalyticsStore()
const toast = useToast()

// Component state
const refreshing = ref(false)
const chartTimeframe = ref('24h')
const energyFlowChart = ref<HTMLCanvasElement>()
const updateInterval = ref<NodeJS.Timeout>()

// Real-time data
const todayProfit = ref(41.85)
const profitTrend = ref(2.3)
const currentSOC = ref(67)
const batteryHealth = ref(98.5)
const batteryAction = ref('Charging')
const currentPower = ref(5.2)
const currentPrice = ref(8.5)
const isPeakHour = ref(false)
const priceSpread = ref(4.5)
const autoModeEnabled = ref(true)

// Action loading states
const actionLoading = reactive({
  charge: false,
  discharge: false,
  auto: false,
  retrain: false
})

// Computed properties
const userConfig = computed(() => settingsStore.userConfig)

const systemStatus = computed(() => {
  if (autoModeEnabled.value && batteryHealth.value > 95) {
    return { color: 'green', icon: '✅', text: 'Optimal' }
  } else if (batteryHealth.value > 85) {
    return { color: 'amber', icon: '⚠️', text: 'Good' }
  } else {
    return { color: 'red', icon: '🚨', text: 'Attention' }
  }
})

const mlAccuracy = computed(() => (analyticsStore.mlMetrics.accuracy * 100).toFixed(1))
const daysSinceTraining = computed(() => analyticsStore.daysSinceTraining)

const nextOpportunities = computed(() => {
  return analyticsStore.arbitrageOpportunities.slice(0, 4)
})

const nextAction = computed(() => {
  const next = nextOpportunities.value[0]
  return next ? next.action : 'hold'
})

const timeToNextAction = computed(() => {
  const next = nextOpportunities.value[0]
  if (!next) return 'N/A'
  
  const now = new Date()
  const nextHour = next.hour
  const currentHour = now.getHours()
  
  let hoursUntil = nextHour - currentHour
  if (hoursUntil < 0) hoursUntil += 24
  
  return hoursUntil === 0 ? 'now' : `${hoursUntil}h`
})

// Mock alerts
const recentAlerts = ref([
  {
    id: 1,
    type: 'info',
    title: 'Optimal charge window starting',
    message: 'Low price period detected, charging recommended',
    timestamp: new Date(Date.now() - 10 * 60 * 1000) // 10 min ago
  },
  {
    id: 2,
    type: 'success',
    title: 'Daily target achieved',
    message: 'Exceeded daily profit target by 15%',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000) // 2 hours ago
  }
])

// Methods
const formatLoadProfile = (type?: string) => {
  const profiles = {
    'standard': 'Business Hours',
    'multi_shift': 'Multi-Shift',
    '24_7': 'Continuous',
    'custom': 'Custom'
  }
  return profiles[type as keyof typeof profiles] || 'Standard'
}

const getOpportunityBgClass = (action: string) => {
  const classes = {
    'charge': 'bg-green-50 dark:bg-green-950 text-green-800 dark:text-green-200',
    'discharge': 'bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-200',
    'hold': 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300'
  }
  return classes[action as keyof typeof classes] || classes.hold
}

const getActionIcon = (action: string) => {
  const icons = { 'charge': '⚡', 'discharge': '🔌', 'hold': '⏸' }
  return icons[action as keyof typeof icons] || '⏸'
}

const getAlertBgClass = (type: string) => {
  const classes = {
    'info': 'bg-blue-50 dark:bg-blue-950',
    'success': 'bg-green-50 dark:bg-green-950',
    'warning': 'bg-amber-50 dark:bg-amber-950',
    'error': 'bg-red-50 dark:bg-red-950'
  }
  return classes[type as keyof typeof classes] || classes.info
}

const getAlertIcon = (type: string) => {
  const icons = { 'info': 'ℹ️', 'success': '✅', 'warning': '⚠️', 'error': '🚨' }
  return icons[type as keyof typeof icons] || 'ℹ️'
}

const formatHour = (hour: number) => {
  return `${String(hour).padStart(2, '0')}:00`
}

const formatTime = (timestamp: Date) => {
  return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const refreshDashboard = async () => {
  refreshing.value = true
  
  try {
    await analyticsStore.refreshAllData()
    
    // Update real-time values
    todayProfit.value = analyticsStore.costAnalytics.netSavings
    currentSOC.value = analyticsStore.batteryMetrics.socCurrent
    batteryHealth.value = analyticsStore.batteryMetrics.healthPercentage
    
    drawEnergyFlowChart()
    
    toast.add({
      title: 'Dashboard Updated',
      description: 'All data refreshed successfully',
      icon: 'i-heroicons-check-circle',
      color: 'green'
    })
  } catch (error) {
    toast.add({
      title: 'Refresh Failed',
      description: 'Could not update dashboard data',
      icon: 'i-heroicons-x-circle',
      color: 'red'
    })
  } finally {
    refreshing.value = false
  }
}

const forceCharge = async () => {
  actionLoading.charge = true
  
  try {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    batteryAction.value = 'Force Charging'
    currentPower.value = 8.5
    
    toast.add({
      title: 'Force Charge Started',
      description: 'Battery is now charging at maximum rate',
      icon: 'i-heroicons-arrow-up',
      color: 'green'
    })
  } finally {
    actionLoading.charge = false
  }
}

const forceDischarge = async () => {
  actionLoading.discharge = true
  
  try {
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    batteryAction.value = 'Force Discharging'
    currentPower.value = -12.0
    
    toast.add({
      title: 'Force Discharge Started',
      description: 'Battery is now discharging at maximum rate',
      icon: 'i-heroicons-arrow-down',
      color: 'red'
    })
  } finally {
    actionLoading.discharge = false
  }
}

const toggleAutoMode = async () => {
  actionLoading.auto = true
  
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    
    autoModeEnabled.value = !autoModeEnabled.value
    
    toast.add({
      title: `Auto Mode ${autoModeEnabled.value ? 'Enabled' : 'Disabled'}`,
      description: autoModeEnabled.value 
        ? 'System will automatically optimize battery operations'
        : 'Manual control mode activated',
      icon: autoModeEnabled.value ? 'i-heroicons-play' : 'i-heroicons-pause',
      color: 'blue'
    })
  } finally {
    actionLoading.auto = false
  }
}

const triggerMLRetrain = async () => {
  actionLoading.retrain = true
  
  try {
    const response = await $fetch('/api/ml/recalculate', {
      method: 'POST',
      body: {}
    })
    
    if (response.success) {
      toast.add({
        title: 'ML Retraining Started',
        description: 'Models are being retrained with latest data',
        icon: 'i-heroicons-cpu-chip',
        color: 'purple'
      })
    } else {
      throw new Error('Failed to start retraining')
    }
  } catch (error) {
    toast.add({
      title: 'Retraining Failed',
      description: 'Could not start ML model retraining',
      icon: 'i-heroicons-x-circle',
      color: 'red'
    })
  } finally {
    actionLoading.retrain = false
  }
}

const drawEnergyFlowChart = () => {
  if (!energyFlowChart.value) return
  
  const canvas = energyFlowChart.value
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
  
  // Generate mock data for 24-hour period
  const simulation = analyticsStore.generateBatterySimulation()
  
  if (simulation.length === 0) {
    // Draw placeholder if no simulation data
    ctx.fillStyle = 'rgb(107, 114, 128)'
    ctx.font = '16px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('Loading chart data...', width / 2, height / 2)
    return
  }
  
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
  
  // Draw SOC line
  ctx.strokeStyle = 'rgb(59, 130, 246)' // Blue
  ctx.lineWidth = 3
  ctx.beginPath()
  
  simulation.forEach((point, index) => {
    const x = (point.hour / 23) * width
    const y = height - (point.soc / 100) * height
    
    if (index === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // Add current time indicator
  const currentHour = new Date().getHours()
  const currentX = (currentHour / 24) * width
  
  ctx.strokeStyle = 'rgb(239, 68, 68)' // Red
  ctx.lineWidth = 2
  ctx.setLineDash([5, 5])
  ctx.beginPath()
  ctx.moveTo(currentX, 0)
  ctx.lineTo(currentX, height)
  ctx.stroke()
  ctx.setLineDash([])
  
  // Labels
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

const startRealTimeUpdates = () => {
  updateInterval.value = setInterval(() => {
    // Mock real-time updates
    if (Math.random() > 0.7) { // 30% chance to update
      currentSOC.value += (Math.random() - 0.5) * 2
      currentSOC.value = Math.max(10, Math.min(90, currentSOC.value))
      
      currentPower.value += (Math.random() - 0.5) * 1
      currentPower.value = Math.max(-15, Math.min(10, currentPower.value))
      
      todayProfit.value += Math.random() * 0.5
    }
  }, 30000) // Update every 30 seconds
}

const stopRealTimeUpdates = () => {
  if (updateInterval.value) {
    clearInterval(updateInterval.value)
    updateInterval.value = undefined
  }
}

// Initialize
onMounted(async () => {
  await settingsStore.loadSettings()
  await analyticsStore.recalculateAllMetrics()
  
  drawEnergyFlowChart()
  startRealTimeUpdates()
})

onUnmounted(() => {
  stopRealTimeUpdates()
})
</script>

<style scoped>
.dashboard-page {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  min-height: 100vh;
}

:deep(.dark) .dashboard-page {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
}

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