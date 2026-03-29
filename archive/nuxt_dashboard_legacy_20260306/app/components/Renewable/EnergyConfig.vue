<!-- Renewable Energy Configuration and Forecasting Component -->
<template>
  <div class="space-y-6">
    <!-- System Configuration -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-sun" class="w-8 h-8 text-yellow-500" />
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
              🌞 Renewable Energy System
            </h1>
          </div>
          <div class="flex items-center space-x-3">
            <UBadge 
              :color="getTotalCapacityColor()" 
              :label="`${totalCapacity}kW Total`"
              size="lg"
            />
            <UButton 
              @click="refreshForecast" 
              :loading="loading"
              icon="i-heroicons-arrow-path"
              size="sm"
              variant="ghost"
            >
              Refresh
            </UButton>
          </div>
        </div>
      </template>
      
      <!-- System Configuration -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Solar Panel Configuration -->
        <div class="space-y-4">
          <div class="flex items-center space-x-3 mb-4">
            <UIcon name="i-heroicons-sun" class="w-6 h-6 text-yellow-500" />
            <h3 class="text-lg font-semibold">☀️ Solar PV System</h3>
          </div>
          
          <UFormGroup label="Solar Capacity (kW)">
            <div class="flex items-center space-x-4">
              <URange 
                v-model="solarCapacity" 
                :min="0" 
                :max="50" 
                :step="0.5"
                class="flex-1"
              />
              <UInput 
                v-model="solarCapacity" 
                type="number" 
                :min="0" 
                :max="50" 
                :step="0.5"
                class="w-20"
              />
              <span class="text-sm text-gray-500">kW</span>
            </div>
          </UFormGroup>
          
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div class="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded">
              <div class="font-medium text-yellow-800 dark:text-yellow-200">Panel Efficiency</div>
              <div class="text-xl font-bold text-yellow-600">22%</div>
            </div>
            <div class="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded">
              <div class="font-medium text-yellow-800 dark:text-yellow-200">System Losses</div>
              <div class="text-xl font-bold text-yellow-600">15%</div>
            </div>
          </div>
          
          <div class="text-xs text-gray-500 space-y-1">
            <p>• South-facing, 35° tilt (optimal for Kiev)</p>
            <p>• High-efficiency monocrystalline panels</p>
            <p>• Includes inverter and wiring losses</p>
          </div>
        </div>
        
        <!-- Wind Turbine Configuration -->
        <div class="space-y-4">
          <div class="flex items-center space-x-3 mb-4">
            <UIcon name="i-heroicons-bolt" class="w-6 h-6 text-blue-500" />
            <h3 class="text-lg font-semibold">💨 Wind Turbine System</h3>
          </div>
          
          <UFormGroup label="Wind Capacity (kW)">
            <div class="flex items-center space-x-4">
              <URange 
                v-model="windCapacity" 
                :min="0" 
                :max="25" 
                :step="0.5"
                class="flex-1"
              />
              <UInput 
                v-model="windCapacity" 
                type="number" 
                :min="0" 
                :max="25" 
                :step="0.5"
                class="w-20"
              />
              <span class="text-sm text-gray-500">kW</span>
            </div>
          </UFormGroup>
          
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
              <div class="font-medium text-blue-800 dark:text-blue-200">Hub Height</div>
              <div class="text-xl font-bold text-blue-600">30m</div>
            </div>
            <div class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded">
              <div class="font-medium text-blue-800 dark:text-blue-200">Cut-in Speed</div>
              <div class="text-xl font-bold text-blue-600">3 m/s</div>
            </div>
          </div>
          
          <div class="text-xs text-gray-500 space-y-1">
            <p>• Rated power at 12 m/s wind speed</p>
            <p>• Cut-out at 25 m/s for safety</p>
            <p>• Optimized for Ukrainian wind patterns</p>
          </div>
        </div>
      </div>
      
      <!-- Quick Configuration Presets -->
      <div class="mt-6">
        <h4 class="font-medium mb-3">Quick Setup Presets:</h4>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <UButton 
            @click="applyPreset('residential')" 
            variant="outline" 
            size="sm"
            block
          >
            🏠 Residential<br><span class="text-xs">5kW Solar + 2kW Wind</span>
          </UButton>
          <UButton 
            @click="applyPreset('commercial')" 
            variant="outline" 
            size="sm"
            block
          >
            🏢 Commercial<br><span class="text-xs">20kW Solar + 10kW Wind</span>
          </UButton>
          <UButton 
            @click="applyPreset('solar_only')" 
            variant="outline" 
            size="sm"
            block
          >
            ☀️ Solar Focus<br><span class="text-xs">15kW Solar Only</span>
          </UButton>
          <UButton 
            @click="applyPreset('hybrid')" 
            variant="outline" 
            size="sm"
            block
          >
            🔄 Balanced<br><span class="text-xs">10kW Solar + 5kW Wind</span>
          </UButton>
        </div>
      </div>
    </UCard>

    <!-- Current Generation Status -->
    <UCard>
      <template #header>
        <div class="flex items-center space-x-3">
          <UIcon name="i-heroicons-bolt" class="w-6 h-6 text-emerald-500" />
          <h2 class="text-xl font-semibold">⚡ Real-time Generation</h2>
        </div>
      </template>
      
      <div v-if="currentGeneration" class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="text-center p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
          <div class="text-4xl font-bold text-emerald-600 mb-2">
            {{ currentGeneration.current_generation?.total_kw?.toFixed(1) || '0.0' }}kW
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Total Generation</p>
          <p class="text-xs text-gray-500 mt-1">
            Right Now
          </p>
        </div>
        
        <div class="text-center p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <div class="text-4xl font-bold text-yellow-600 mb-2">
            {{ currentGeneration.current_generation?.solar_kw?.toFixed(1) || '0.0' }}kW
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Solar Power</p>
          <p class="text-xs text-gray-500 mt-1">
            {{ currentGeneration.weather_conditions?.solar_irradiance_wm2 || 0 }} W/m²
          </p>
        </div>
        
        <div class="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div class="text-4xl font-bold text-blue-600 mb-2">
            {{ currentGeneration.current_generation?.wind_kw?.toFixed(1) || '0.0' }}kW
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Wind Power</p>
          <p class="text-xs text-gray-500 mt-1">
            {{ currentGeneration.weather_conditions?.wind_speed_ms?.toFixed(1) || 0 }} m/s
          </p>
        </div>
        
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div class="text-4xl font-bold text-gray-600 mb-2">
            {{ getCapacityFactor() }}%
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400">Capacity Factor</p>
          <p class="text-xs text-gray-500 mt-1">
            Current Output
          </p>
        </div>
      </div>
      
      <!-- Weather Conditions -->
      <div v-if="currentGeneration" class="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-center text-sm">
        <div>
          <div class="text-lg font-bold">{{ currentGeneration.weather_conditions?.temperature_celsius?.toFixed(1) || '--' }}°C</div>
          <p class="text-gray-500">Temperature</p>
        </div>
        <div>
          <div class="text-lg font-bold">{{ currentGeneration.weather_conditions?.cloud_cover_percent || 0 }}%</div>
          <p class="text-gray-500">Cloud Cover</p>
        </div>
        <div>
          <div class="text-lg font-bold">{{ currentGeneration.weather_conditions?.wind_speed_ms?.toFixed(1) || 0 }} m/s</div>
          <p class="text-gray-500">Wind Speed</p>
        </div>
        <div>
          <div class="text-lg font-bold">{{ currentGeneration.weather_conditions?.solar_irradiance_wm2 || 0 }} W/m²</div>
          <p class="text-gray-500">Solar Irradiance</p>
        </div>
      </div>
    </UCard>

    <!-- 24-Hour Forecast -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-chart-line" class="w-6 h-6 text-purple-500" />
            <h2 class="text-xl font-semibold">📈 24-Hour Generation Forecast</h2>
          </div>
          <div class="flex items-center space-x-2">
            <USelectMenu 
              v-model="forecastHours" 
              :options="forecastOptions"
              size="sm"
            />
            <UButton 
              @click="refreshForecast" 
              :loading="loading"
              icon="i-heroicons-arrow-path"
              size="sm"
              variant="ghost"
            />
          </div>
        </div>
      </template>
      
      <!-- Forecast Summary -->
      <div v-if="forecast" class="mb-6">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div class="text-center p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded">
            <div class="text-2xl font-bold text-emerald-600">
              {{ forecast.summary?.total_renewable_kwh?.toFixed(1) || 0 }}
            </div>
            <p class="text-sm text-gray-600">Total kWh</p>
          </div>
          <div class="text-center p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded">
            <div class="text-2xl font-bold text-yellow-600">
              {{ forecast.summary?.solar_capacity_factor?.toFixed(1) || 0 }}%
            </div>
            <p class="text-sm text-gray-600">Solar CF</p>
          </div>
          <div class="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded">
            <div class="text-2xl font-bold text-blue-600">
              {{ forecast.summary?.wind_capacity_factor?.toFixed(1) || 0 }}%
            </div>
            <p class="text-sm text-gray-600">Wind CF</p>
          </div>
          <div class="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded">
            <div class="text-2xl font-bold text-purple-600">
              {{ forecast.summary?.peak_total_kw?.toFixed(1) || 0 }}
            </div>
            <p class="text-sm text-gray-600">Peak kW</p>
          </div>
        </div>
        
        <!-- Peak Generation Times -->
        <div v-if="forecast.summary?.peak_solar_hour || forecast.summary?.peak_wind_hour" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div v-if="forecast.summary?.peak_solar_hour" class="p-3 border border-yellow-200 dark:border-yellow-800 rounded bg-yellow-50 dark:bg-yellow-900/10">
            <div class="flex items-center space-x-2 mb-1">
              <UIcon name="i-heroicons-sun" class="w-4 h-4 text-yellow-500" />
              <span class="font-medium text-yellow-800 dark:text-yellow-200">Peak Solar Generation</span>
            </div>
            <p class="text-sm">
              {{ formatTime(forecast.summary.peak_solar_hour) }} - {{ forecast.summary?.peak_solar_kw?.toFixed(1) }}kW
            </p>
          </div>
          
          <div v-if="forecast.summary?.peak_wind_hour" class="p-3 border border-blue-200 dark:border-blue-800 rounded bg-blue-50 dark:bg-blue-900/10">
            <div class="flex items-center space-x-2 mb-1">
              <UIcon name="i-heroicons-bolt" class="w-4 h-4 text-blue-500" />
              <span class="font-medium text-blue-800 dark:text-blue-200">Peak Wind Generation</span>
            </div>
            <p class="text-sm">
              {{ formatTime(forecast.summary.peak_wind_hour) }} - {{ forecast.summary?.peak_wind_kw?.toFixed(1) }}kW
            </p>
          </div>
        </div>
      </div>
      
      <!-- Hourly Forecast Chart -->
      <div v-if="forecast?.hourly_forecast" class="space-y-4">
        <div class="h-64 bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <div class="flex items-center justify-center h-full">
            <div class="text-center">
              <UIcon name="i-heroicons-chart-bar" class="w-12 h-12 mx-auto mb-2 text-gray-400" />
              <p class="text-gray-500">Generation Forecast Chart</p>
              <p class="text-xs text-gray-400 mt-1">Interactive chart would be rendered here</p>
            </div>
          </div>
        </div>
        
        <!-- Hourly Data Table -->
        <div class="max-h-64 overflow-y-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 dark:bg-gray-800 sticky top-0">
              <tr>
                <th class="text-left p-2">Hour</th>
                <th class="text-right p-2">Solar (kW)</th>
                <th class="text-right p-2">Wind (kW)</th>
                <th class="text-right p-2">Total (kW)</th>
                <th class="text-right p-2">Weather</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="(hour, index) in forecast.hourly_forecast.slice(0, 24)" 
                :key="index"
                class="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <td class="p-2 font-medium">{{ formatHour(hour.timestamp) }}</td>
                <td class="p-2 text-right">
                  <span class="text-yellow-600 font-medium">{{ hour.solar_generation_kw?.toFixed(1) || '0.0' }}</span>
                </td>
                <td class="p-2 text-right">
                  <span class="text-blue-600 font-medium">{{ hour.wind_generation_kw?.toFixed(1) || '0.0' }}</span>
                </td>
                <td class="p-2 text-right">
                  <span class="font-bold">{{ hour.total_generation_kw?.toFixed(1) || '0.0' }}</span>
                </td>
                <td class="p-2 text-right text-xs">
                  <div>{{ hour.temperature_celsius?.toFixed(0) }}°C</div>
                  <div>{{ hour.wind_speed_ms?.toFixed(1) }}m/s</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </UCard>

    <!-- System Optimization -->
    <UCard>
      <template #header>
        <div class="flex items-center space-x-3">
          <UIcon name="i-heroicons-cog-6-tooth" class="w-6 h-6 text-indigo-500" />
          <h2 class="text-xl font-semibold">🔧 System Optimization</h2>
        </div>
      </template>
      
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Optimization Parameters -->
        <div class="space-y-4">
          <UFormGroup label="Target Daily Generation (kWh)">
            <UInput 
              v-model="optimizationParams.targetDailyKwh" 
              type="number" 
              :min="1" 
              :max="500"
              placeholder="e.g., 50"
            />
          </UFormGroup>
          
          <UFormGroup label="Budget (USD)">
            <UInput 
              v-model="optimizationParams.budgetUsd" 
              type="number" 
              :min="1000" 
              :max="100000"
              placeholder="e.g., 20000"
            />
          </UFormGroup>
          
          <UButton 
            @click="optimizeSystem" 
            :loading="optimizing"
            color="indigo"
            icon="i-heroicons-cpu-chip"
            block
          >
            Optimize System Configuration
          </UButton>
        </div>
        
        <!-- Optimization Results -->
        <div v-if="optimizationResult">
          <h4 class="font-semibold mb-4">🎯 Optimization Results</h4>
          
          <div class="space-y-4">
            <div class="p-4 border border-emerald-200 dark:border-emerald-800 rounded-lg bg-emerald-50 dark:bg-emerald-900/10">
              <h5 class="font-medium text-emerald-800 dark:text-emerald-200 mb-2">Recommended Configuration</h5>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span class="text-gray-600">Solar Capacity:</span>
                  <div class="font-bold text-yellow-600">{{ optimizationResult.optimization_result?.solar_capacity_kw }}kW</div>
                </div>
                <div>
                  <span class="text-gray-600">Wind Capacity:</span>
                  <div class="font-bold text-blue-600">{{ optimizationResult.optimization_result?.wind_capacity_kw }}kW</div>
                </div>
                <div>
                  <span class="text-gray-600">Daily Output:</span>
                  <div class="font-bold">{{ optimizationResult.optimization_result?.estimated_daily_kwh }}kWh</div>
                </div>
                <div>
                  <span class="text-gray-600">Target Achievement:</span>
                  <div class="font-bold text-emerald-600">{{ optimizationResult.optimization_result?.target_achievement_percent }}%</div>
                </div>
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div class="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
                <div class="font-bold text-lg">{{ optimizationResult.optimization_result?.payback_years }}</div>
                <p class="text-gray-500">Years Payback</p>
              </div>
              <div class="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded">
                <div class="font-bold text-lg">${{ optimizationResult.optimization_result?.cost_per_daily_kwh }}</div>
                <p class="text-gray-500">Cost per Daily kWh</p>
              </div>
            </div>
            
            <UButton 
              @click="applyOptimization" 
              color="emerald"
              icon="i-heroicons-check"
              block
            >
              Apply Recommended Configuration
            </UButton>
          </div>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup>
// Page metadata
definePageMeta({
  title: 'Renewable Energy',
  description: 'Solar and wind generation configuration and forecasting'
})

// Imports
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

// Toast notifications
const toast = useToast()

// Reactive state
const solarCapacity = ref(10.0)
const windCapacity = ref(5.0)
const forecastHours = ref(24)
const loading = ref(false)
const optimizing = ref(false)

const currentGeneration = ref(null)
const forecast = ref(null)
const optimizationResult = ref(null)

const optimizationParams = ref({
  targetDailyKwh: 50,
  budgetUsd: 20000
})

// Forecast options
const forecastOptions = [
  { label: '24 Hours', value: 24 },
  { label: '48 Hours', value: 48 },
  { label: '72 Hours', value: 72 },
  { label: '1 Week', value: 168 }
]

// Computed properties
const totalCapacity = computed(() => solarCapacity.value + windCapacity.value)

// Auto-refresh setup
let refreshInterval = null

// Methods
const refreshForecast = async () => {
  loading.value = true
  try {
    // Get current generation
    const currentData = await $fetch('/api/renewable/forecast', {
      params: {
        type: 'current',
        solar_capacity: solarCapacity.value,
        wind_capacity: windCapacity.value
      }
    })
    currentGeneration.value = currentData
    
    // Get forecast
    const forecastData = await $fetch('/api/renewable/forecast', {
      params: {
        type: 'forecast',
        forecast_hours: forecastHours.value,
        solar_capacity: solarCapacity.value,
        wind_capacity: windCapacity.value
      }
    })
    forecast.value = forecastData
    
    console.log('Renewable forecast refreshed')
    
  } catch (error) {
    console.error('Failed to refresh renewable forecast:', error)
    toast.add({
      title: 'Forecast Refresh Failed',
      description: error.message || 'Could not fetch renewable energy data',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}

const optimizeSystem = async () => {
  optimizing.value = true
  try {
    const result = await $fetch('/api/renewable/forecast', {
      params: {
        type: 'optimize',
        target_daily_kwh: optimizationParams.value.targetDailyKwh,
        budget_usd: optimizationParams.value.budgetUsd
      }
    })
    
    optimizationResult.value = result
    
    toast.add({
      title: 'Optimization Complete',
      description: 'System configuration optimized for your requirements',
      color: 'green'
    })
    
  } catch (error) {
    console.error('System optimization failed:', error)
    toast.add({
      title: 'Optimization Failed',
      description: error.message || 'Could not optimize system configuration',
      color: 'red'
    })
  } finally {
    optimizing.value = false
  }
}

const applyOptimization = () => {
  if (optimizationResult.value?.optimization_result) {
    solarCapacity.value = optimizationResult.value.optimization_result.solar_capacity_kw
    windCapacity.value = optimizationResult.value.optimization_result.wind_capacity_kw
    
    toast.add({
      title: 'Configuration Applied',
      description: 'System updated with optimized configuration',
      color: 'blue'
    })
    
    // Refresh forecast with new configuration
    refreshForecast()
  }
}

const applyPreset = (preset) => {
  const presets = {
    residential: { solar: 5, wind: 2 },
    commercial: { solar: 20, wind: 10 },
    solar_only: { solar: 15, wind: 0 },
    hybrid: { solar: 10, wind: 5 }
  }
  
  if (presets[preset]) {
    solarCapacity.value = presets[preset].solar
    windCapacity.value = presets[preset].wind
    
    toast.add({
      title: 'Preset Applied',
      description: `${preset.charAt(0).toUpperCase() + preset.slice(1)} configuration loaded`,
      color: 'blue'
    })
  }
}

// Utility functions
const getTotalCapacityColor = () => {
  if (totalCapacity.value >= 20) return 'green'
  if (totalCapacity.value >= 10) return 'blue'
  if (totalCapacity.value >= 5) return 'amber'
  return 'gray'
}

const getCapacityFactor = () => {
  if (!currentGeneration.value || totalCapacity.value === 0) return 0
  
  const currentOutput = currentGeneration.value.current_generation?.total_kw || 0
  return Math.round((currentOutput / totalCapacity.value) * 100)
}

const formatTime = (timestamp) => {
  if (!timestamp) return '--'
  try {
    return new Date(timestamp).toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit'
    })
  } catch {
    return '--'
  }
}

const formatHour = (timestamp) => {
  if (!timestamp) return '--'
  try {
    return new Date(timestamp).toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return '--'
  }
}

// Watch for capacity changes and refresh forecast
watch([solarCapacity, windCapacity, forecastHours], () => {
  // Debounce forecast refresh
  if (refreshInterval) {
    clearTimeout(refreshInterval)
  }
  refreshInterval = setTimeout(() => {
    refreshForecast()
  }, 1000)
}, { deep: true })

// Lifecycle
onMounted(async () => {
  // Initial data load
  await refreshForecast()
  
  // Set up auto-refresh every 5 minutes
  refreshInterval = setInterval(async () => {
    await refreshForecast()
  }, 300000)
  
  console.log('Renewable energy page mounted, auto-refresh enabled')
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  console.log('Renewable energy page unmounted, auto-refresh disabled')
})
</script>

<style scoped>
/* Component-specific styles */
.renewable-chart {
  /* Chart styling would go here */
}
</style>